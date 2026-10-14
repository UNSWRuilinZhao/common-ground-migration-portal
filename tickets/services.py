import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ConsultationRequest, EmailVerification, PasswordResetVerification


VERIFICATION_LIFETIME = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_VERIFICATION_ATTEMPTS = 5


def consultation_reference(enquiry):
    return f"CGM-ENQ-{enquiry.pk:06d}"


def send_consultation_confirmation_email(enquiry):
    return send_mail(
        subject="We received your consultation request",
        message=render_to_string(
            "emails/consultation_confirmation.txt",
            {
                "enquiry": enquiry,
                "reference": consultation_reference(enquiry),
            },
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[enquiry.email],
        fail_silently=False,
    )


def send_consultation_staff_notification(enquiry, admin_url):
    recipients = settings.CONSULTATION_NOTIFICATION_EMAILS
    if not recipients:
        return 0
    return send_mail(
        subject="New consultation request received",
        message=render_to_string(
            "emails/consultation_staff_notification.txt",
            {
                "enquiry": enquiry,
                "reference": consultation_reference(enquiry),
                "admin_url": admin_url,
            },
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )


def issue_verification_code(user):
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification, _ = EmailVerification.objects.update_or_create(
        user=user,
        defaults={
            "code_hash": make_password(code),
            "expires_at": timezone.now() + VERIFICATION_LIFETIME,
            "attempts": 0,
            "verified_at": None,
        },
    )
    send_mail(
        subject="Your Common Ground verification code",
        message=(
            f"Hi {user.first_name or user.username},\n\n"
            f"Your Common Ground client portal verification code is: {code}\n\n"
            "This code expires in 10 minutes. If you did not create this account, "
            "you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    return verification


def issue_password_reset_code(user):
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification, _ = PasswordResetVerification.objects.update_or_create(
        user=user,
        defaults={
            "code_hash": make_password(code),
            "expires_at": timezone.now() + VERIFICATION_LIFETIME,
            "attempts": 0,
            "used_at": None,
        },
    )
    send_mail(
        subject="Reset your Common Ground password",
        message=(
            f"Hi {user.first_name or user.username},\n\n"
            f"Your Common Ground client portal password reset code is: {code}\n\n"
            "This code expires in 10 minutes. If you did not request a password "
            "reset, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    return verification
