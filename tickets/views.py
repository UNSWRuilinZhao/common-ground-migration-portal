import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CaseMessageForm,
    ConsultationForm,
    DocumentItemForm,
    SignUpForm,
    StaffCaseForm,
    VerificationCodeForm,
)
from .models import (
    Case,
    CaseEvent,
    ConsultationRequest,
    DocumentItem,
    EmailVerification,
    PasswordResetVerification,
)
from .services import (
    MAX_VERIFICATION_ATTEMPTS,
    RESEND_COOLDOWN,
    issue_password_reset_code,
    issue_verification_code,
    send_consultation_confirmation_email,
    send_consultation_staff_notification,
)
from .security import email_delivery_rate_limited, rate_limit_exceeded


logger = logging.getLogger(__name__)
PENDING_USER_SESSION_KEY = "pending_verification_user_id"
CONSULTATION_RECEIPT_SESSION_KEY = "consultation_submission_receipt"


def home(request):
    return render(request, "home.html")


def services(request):
    return render(request, "public/services.html")


def about(request):
    return render(request, "public/about.html")


def guides(request):
    return render(request, "public/guides.html")


def consultation(request):
    if request.method == "GET":
        request.session.pop(CONSULTATION_RECEIPT_SESSION_KEY, None)

    initial = {}
    if request.user.is_authenticated:
        initial = {
            "name": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
        }
    form = ConsultationForm(request.POST or None, initial=initial)
    if request.method == "POST" and request.POST.get("website", "").strip():
        logger.warning("Consultation honeypot rejected an automated submission.")
        return redirect("home")

    consultation_limited = False
    if request.method == "POST":
        submitted_email = request.POST.get("email", "").strip().lower()[:254]
        limit = settings.CONSULTATION_RATE_LIMIT_COUNT
        window = settings.CONSULTATION_RATE_LIMIT_WINDOW_SECONDS
        consultation_limited = rate_limit_exceeded(
            request,
            "consultation:source",
            limit=limit,
            window_seconds=window,
        ) or rate_limit_exceeded(
            request,
            "consultation:address",
            limit=limit,
            window_seconds=window,
            identity=submitted_email,
        )
        if consultation_limited:
            form.add_error(
                None,
                "Too many consultation requests were submitted. "
                "Please wait ten minutes and try again.",
            )

    if request.method == "POST" and not consultation_limited and form.is_valid():
        enquiry = form.save()
        email_failures = []
        confirmation_sent = False
        staff_notified = False
        try:
            confirmation_sent = bool(send_consultation_confirmation_email(enquiry))
            if not confirmation_sent:
                email_failures.append("confirmation")
        except Exception:
            email_failures.append("confirmation")
            logger.exception(
                "Unable to send consultation confirmation for enquiry %s",
                enquiry.pk,
            )
        try:
            admin_url = request.build_absolute_uri(
                reverse(
                    "admin:tickets_consultationrequest_change",
                    args=[enquiry.pk],
                )
            )
            staff_notified = bool(
                send_consultation_staff_notification(enquiry, admin_url)
            )
            if not staff_notified:
                email_failures.append("staff notification")
        except Exception:
            email_failures.append("staff notification")
            logger.exception(
                "Unable to send staff notification for enquiry %s",
                enquiry.pk,
            )

        if email_failures:
            messages.warning(
                request,
                "Your request was saved, but an email notification may be delayed.",
            )
        else:
            messages.success(
                request,
                "Your request was received and a confirmation email has been sent.",
            )
        request.session[CONSULTATION_RECEIPT_SESSION_KEY] = {
            "confirmation_sent": confirmation_sent,
            "staff_notified": staff_notified,
        }
        return redirect("consultation_thanks")
    return render(request, "public/consultation.html", {"form": form})


def consultation_thanks(request):
    receipt = request.session.get(CONSULTATION_RECEIPT_SESSION_KEY)
    if not receipt:
        return redirect("consultation")
    return render(request, "public/consultation_thanks.html", receipt)


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if email_delivery_rate_limited(
            request,
            "signup",
            form.cleaned_data["email"],
        ):
            form.add_error(
                None,
                "Too many verification emails were requested. Please try again later.",
            )
            return render(request, "registration/signup.html", {"form": form})
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        request.session[PENDING_USER_SESSION_KEY] = user.pk
        try:
            issue_verification_code(user)
            messages.success(request, "We sent a six-digit code to your email.")
        except Exception:
            logger.exception("Unable to send verification email for user %s", user.pk)
            messages.error(
                request,
                "Your account was created, but the email could not be sent. Try resending the code.",
            )
        return redirect("verify_email")
    return render(request, "registration/signup.html", {"form": form})


def pending_verification_user(request):
    user_id = request.session.get(PENDING_USER_SESSION_KEY)
    if not user_id:
        return None
    return get_user_model().objects.filter(pk=user_id, is_active=False).first()


def verify_email(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    user = pending_verification_user(request)
    if not user:
        messages.info(request, "Create an account before entering a verification code.")
        return redirect("signup")

    form = VerificationCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        verification = EmailVerification.objects.filter(user=user).first()
        if not verification:
            messages.error(request, "No active code was found. Request a new code.")
        elif verification.is_expired():
            messages.error(request, "This code has expired. Request a new code.")
        elif verification.attempts >= MAX_VERIFICATION_ATTEMPTS:
            messages.error(request, "Too many incorrect attempts. Request a new code.")
        elif check_password(form.cleaned_data["code"], verification.code_hash):
            verification.verified_at = timezone.now()
            verification.save(update_fields=["verified_at"])
            user.is_active = True
            user.save(update_fields=["is_active"])
            request.session.pop(PENDING_USER_SESSION_KEY, None)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Email verified — welcome to your client portal.")
            return redirect("dashboard")
        else:
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            remaining = MAX_VERIFICATION_ATTEMPTS - verification.attempts
            messages.error(
                request,
                f"That code is incorrect. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
            )

    return render(
        request,
        "registration/verify_email.html",
        {"form": form, "email": user.email},
    )


@require_POST
def resend_verification(request):
    user = pending_verification_user(request)
    if not user:
        messages.info(request, "Create an account before requesting a code.")
        return redirect("signup")

    verification = EmailVerification.objects.filter(user=user).first()
    if verification and timezone.now() - verification.sent_at < RESEND_COOLDOWN:
        messages.info(request, "Please wait one minute before requesting another code.")
        return redirect("verify_email")

    if email_delivery_rate_limited(request, "verification-resend", user.email):
        messages.info(
            request,
            "Too many verification emails were requested. Please try again later.",
        )
        return redirect("verify_email")

    try:
        issue_verification_code(user)
        messages.success(request, "A new verification code has been sent.")
    except Exception:
        logger.exception("Unable to resend verification email for user %s", user.pk)
        messages.error(request, "The code could not be sent. Please try again shortly.")
    return redirect("verify_email")


@require_POST
def send_password_reset_code(request):
    email = request.POST.get("email", "").strip().lower()[:254]
    response_message = (
        "If an active account matches that email, a six-digit code has been sent."
    )
    if email_delivery_rate_limited(request, "password-reset", email):
        return JsonResponse({"ok": True, "message": response_message})
    user = (
        get_user_model()
        .objects.filter(email__iexact=email, is_active=True)
        .order_by("pk")
        .first()
    )

    if user:
        verification = PasswordResetVerification.objects.filter(user=user).first()
        is_cooling_down = (
            verification
            and timezone.now() - verification.sent_at < RESEND_COOLDOWN
        )
        if not is_cooling_down:
            try:
                issue_password_reset_code(user)
            except Exception:
                logger.exception(
                    "Unable to send password reset email for user %s", user.pk
                )

    return JsonResponse({"ok": True, "message": response_message})


@require_POST
def confirm_password_reset(request):
    email = request.POST.get("email", "").strip().lower()[:254]
    code = request.POST.get("code", "").strip()
    new_password1 = request.POST.get("new_password1", "")
    new_password2 = request.POST.get("new_password2", "")

    errors = {}
    if not email:
        errors["email"] = ["Enter the email address linked to your account."]
    if len(code) != 6 or not code.isdigit():
        errors["code"] = ["Enter the six-digit code from your email."]
    if not new_password1:
        errors["new_password1"] = ["Enter a new password."]
    if new_password1 != new_password2:
        errors["new_password2"] = ["The two password entries do not match."]
    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    with transaction.atomic():
        user = (
            get_user_model()
            .objects.filter(email__iexact=email, is_active=True)
            .order_by("pk")
            .first()
        )
        verification = None
        if user:
            verification = (
                PasswordResetVerification.objects.select_for_update()
                .filter(user=user)
                .first()
            )

        invalid_code = (
            not verification
            or verification.used_at is not None
            or verification.is_expired()
            or verification.attempts >= MAX_VERIFICATION_ATTEMPTS
        )
        if invalid_code:
            return JsonResponse(
                {
                    "ok": False,
                    "errors": {"code": ["This code is invalid or has expired."]},
                },
                status=400,
            )

        if not check_password(code, verification.code_hash):
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            remaining = MAX_VERIFICATION_ATTEMPTS - verification.attempts
            message = "This code is incorrect."
            if remaining:
                message += f" {remaining} attempt{'s' if remaining != 1 else ''} remaining."
            else:
                message += " Request a new code."
            return JsonResponse(
                {"ok": False, "errors": {"code": [message]}}, status=400
            )

        try:
            validate_password(new_password1, user=user)
        except ValidationError as exc:
            return JsonResponse(
                {"ok": False, "errors": {"new_password1": list(exc.messages)}},
                status=400,
            )

        user.set_password(new_password1)
        user.save(update_fields=["password"])
        verification.used_at = timezone.now()
        verification.save(update_fields=["used_at"])

    return JsonResponse(
        {
            "ok": True,
            "message": "Your password has been reset. You can now log in securely.",
        }
    )


def health(request):
    return JsonResponse({"status": "ok"})


def visible_cases(user):
    cases = Case.objects.select_related("client", "advisor")
    if user.is_staff:
        return cases
    return cases.filter(client=user)


@login_required
def dashboard(request):
    cases = visible_cases(request.user)
    all_visible = cases

    query = request.GET.get("q", "").strip()
    stage = request.GET.get("stage", "").strip()
    visa_type = request.GET.get("visa_type", "").strip()

    if query:
        cases = cases.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(client__username__icontains=query)
            | Q(client__first_name__icontains=query)
            | Q(client__email__icontains=query)
        )
    if stage in Case.Stage.values:
        cases = cases.filter(stage=stage)
    if visa_type in Case.VisaType.values:
        cases = cases.filter(visa_type=visa_type)

    stats = {
        "total": all_visible.count(),
        "active": all_visible.exclude(stage=Case.Stage.FINALISED).count(),
        "preparing": all_visible.filter(
            stage__in=[Case.Stage.STRATEGY, Case.Stage.DOCUMENTS, Case.Stage.AWAITING_CLIENT]
        ).count(),
        "lodged": all_visible.filter(
            stage__in=[Case.Stage.LODGED, Case.Stage.AWAITING_DECISION]
        ).count(),
    }
    context = {
        "cases": cases,
        "query": query,
        "selected_stage": stage,
        "selected_visa_type": visa_type,
        "stage_choices": Case.Stage.choices,
        "visa_type_choices": Case.VisaType.choices,
        "stats": stats,
        "new_enquiries": (
            ConsultationRequest.objects.filter(status=ConsultationRequest.Status.NEW)[:4]
            if request.user.is_staff
            else []
        ),
    }
    return render(request, "cases/dashboard.html", context)


def staff_or_404(user):
    if not user.is_staff:
        raise Http404("This workspace is only available to staff.")


@login_required
def case_create(request):
    staff_or_404(request.user)
    form = StaffCaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        case = form.save()
        CaseEvent.objects.create(
            case=case,
            title="Case opened",
            detail=f"{case.get_visa_type_display()} case created.",
            created_by=request.user,
        )
        messages.success(request, f"{case.reference} was created.")
        return redirect(case)
    return render(
        request,
        "cases/case_form.html",
        {"form": form, "page_title": "Create a case", "submit_label": "Create case"},
    )


def get_visible_case_or_404(user, pk):
    return get_object_or_404(visible_cases(user), pk=pk)


@login_required
def case_detail(request, pk):
    case = get_visible_case_or_404(request.user, pk)
    message_form = CaseMessageForm(
        request.POST or None,
        is_staff=request.user.is_staff,
    )
    if request.method == "POST" and message_form.is_valid():
        case_message = message_form.save(commit=False)
        case_message.case = case
        case_message.author = request.user
        if not request.user.is_staff:
            case_message.is_internal = False
        case_message.save()
        messages.success(
            request,
            "Internal note added." if case_message.is_internal else "Message sent.",
        )
        return redirect(case)

    case_messages = case.messages.select_related("author")
    events = case.events.select_related("created_by")
    if not request.user.is_staff:
        case_messages = case_messages.filter(is_internal=False)
        events = events.filter(visible_to_client=True)

    return render(
        request,
        "cases/case_detail.html",
        {
            "case": case,
            "case_messages": case_messages,
            "events": events,
            "message_form": message_form,
            "document_form": DocumentItemForm() if request.user.is_staff else None,
            "document_status_choices": DocumentItem.Status.choices,
        },
    )


@login_required
def case_edit(request, pk):
    staff_or_404(request.user)
    case = get_object_or_404(Case, pk=pk)
    previous_stage = case.stage
    form = StaffCaseForm(request.POST or None, instance=case)
    if request.method == "POST" and form.is_valid():
        case = form.save()
        if previous_stage != case.stage:
            CaseEvent.objects.create(
                case=case,
                title=case.get_stage_display(),
                detail="Case stage updated by your advisory team.",
                created_by=request.user,
            )
        messages.success(request, "Case details updated.")
        return redirect(case)
    return render(
        request,
        "cases/case_form.html",
        {"form": form, "page_title": f"Edit {case.reference}", "submit_label": "Save changes"},
    )


@require_POST
@login_required
def document_add(request, pk):
    staff_or_404(request.user)
    case = get_object_or_404(Case, pk=pk)
    form = DocumentItemForm(request.POST)
    if form.is_valid():
        document = form.save(commit=False)
        document.case = case
        document.save()
        messages.success(request, f"{document.name} was added to the checklist.")
    else:
        messages.error(request, "The checklist item could not be added.")
    return redirect(case)


@require_POST
@login_required
def document_update(request, pk, document_pk):
    staff_or_404(request.user)
    case = get_object_or_404(Case, pk=pk)
    document = get_object_or_404(DocumentItem, pk=document_pk, case=case)
    status = request.POST.get("status", "")
    if status in DocumentItem.Status.values:
        document.status = status
        document.save(update_fields=["status", "updated_at"])
        CaseEvent.objects.create(
            case=case,
            title=f"Document: {document.name}",
            detail=f"Status changed to {document.get_status_display()}.",
            created_by=request.user,
        )
        messages.success(request, "Document status updated.")
    else:
        messages.error(request, "Choose a valid document status.")
    return redirect(case)
