import re
from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    Case,
    CaseEvent,
    CaseMessage,
    ConsultationRequest,
    DocumentItem,
    EmailVerification,
    PasswordResetVerification,
)


class CommonGroundTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="alex",
            email="alex@example.com",
            password="Strong-pass-841!",
            first_name="Alex",
        )
        self.other_user = user_model.objects.create_user(
            username="sam",
            email="sam@example.com",
            password="Strong-pass-842!",
            first_name="Sam",
        )
        self.staff = user_model.objects.create_user(
            username="casey",
            email="casey@example.com",
            password="Strong-pass-843!",
            first_name="Casey",
            is_staff=True,
        )
        self.own_case = Case.objects.create(
            title="Skilled migration planning",
            summary="Review occupation, points and state options.",
            visa_type=Case.VisaType.SKILLED,
            client=self.user,
            advisor=self.staff,
            next_action="Confirm English test date",
        )
        self.other_case = Case.objects.create(
            title="Partner visa preparation",
            summary="Organise relationship evidence.",
            visa_type=Case.VisaType.PARTNER,
            client=self.other_user,
        )

    def signup_taylor(self):
        response = self.client.post(
            reverse("signup"),
            {
                "first_name": "Taylor",
                "email": "taylor@example.com",
                "username": "taylor",
                "password1": "Useful-pass-925!",
                "password2": "Useful-pass-925!",
            },
        )
        return response, get_user_model().objects.get(username="taylor")

    def verification_code_from_email(self):
        match = re.search(r"\b(\d{6})\b", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_public_pages_load(self):
        for route in ("home", "services", "about", "guides", "consultation"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 200)

        self.assertContains(
            self.client.get(reverse("home")),
            "Portfolio demonstration",
        )

    def test_consultation_date_input_has_dmy_mask_attributes(self):
        response = self.client.get(reverse("consultation"))
        self.assertContains(response, 'placeholder="DD/MM/YYYY"')
        self.assertContains(response, 'maxlength="10"')
        self.assertContains(response, 'data-date-input="dmy"')

    def test_consultation_thanks_requires_a_successful_submission(self):
        response = self.client.get(reverse("consultation_thanks"))
        self.assertRedirects(response, reverse("consultation"))

    def test_health_check_is_public(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_portfolio_cleanup_preserves_staff_and_removes_client_data(self):
        ConsultationRequest.objects.create(
            name="Portfolio Cleanup",
            email="cleanup@example.com",
            visa_interest=Case.VisaType.OTHER,
            preferred_contact=ConsultationRequest.ContactMethod.EMAIL,
            message="Temporary test record.",
            privacy_consent=True,
        )
        dry_run_output = StringIO()
        call_command("sanitize_portfolio_data", stdout=dry_run_output)
        self.assertIn("Dry run only", dry_run_output.getvalue())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

        call_command("sanitize_portfolio_data", "--apply", stdout=StringIO())

        self.assertTrue(get_user_model().objects.filter(pk=self.staff.pk).exists())
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertFalse(get_user_model().objects.filter(pk=self.other_user.pk).exists())
        self.assertFalse(Case.objects.exists())
        self.assertFalse(ConsultationRequest.objects.exists())

    @override_settings(CONSULTATION_NOTIFICATION_EMAILS=["team@example.com"])
    def test_consultation_form_creates_enquiry_and_sends_notifications(self):
        response = self.client.post(
            reverse("consultation"),
            {
                "name": "Jordan Lee",
                "email": "jordan@example.com",
                "phone": "0400 000 000",
                "location": "Sydney",
                "visa_interest": Case.VisaType.SKILLED,
                "current_visa": "Graduate visa",
                "visa_expiry": "01/06/2027",
                "preferred_contact": ConsultationRequest.ContactMethod.EMAIL,
                "message": "I would like to understand my skilled options.",
                "privacy_consent": "on",
            },
        )
        self.assertRedirects(response, reverse("consultation_thanks"))
        enquiry = ConsultationRequest.objects.get(email="jordan@example.com")
        self.assertEqual(enquiry.status, ConsultationRequest.Status.NEW)
        self.assertEqual(enquiry.visa_expiry, date(2027, 6, 1))
        self.assertEqual(len(mail.outbox), 2)
        confirmation = next(
            message for message in mail.outbox if message.to == ["jordan@example.com"]
        )
        notification = next(
            message for message in mail.outbox if message.to == ["team@example.com"]
        )
        self.assertEqual(confirmation.subject, "We received your consultation request")
        self.assertIn("CGM-ENQ-000001", confirmation.body)
        self.assertEqual(notification.subject, "New consultation request received")
        self.assertIn("Sydney", notification.body)
        self.assertIn(
            f"/admin/tickets/consultationrequest/{enquiry.pk}/change/",
            notification.body,
        )
        thanks = self.client.get(reverse("consultation_thanks"))
        self.assertContains(thanks, "Our team has been notified")
        self.assertContains(thanks, "a confirmation email has been sent")

    def test_consultation_honeypot_discards_automated_submission(self):
        response = self.client.post(
            reverse("consultation"),
            {
                "website": "https://spam.example",
                "name": "Automated Visitor",
                "email": "bot@example.com",
                "visa_interest": Case.VisaType.OTHER,
                "preferred_contact": ConsultationRequest.ContactMethod.EMAIL,
                "message": "Automated content",
                "privacy_consent": "on",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(ConsultationRequest.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(CONSULTATION_NOTIFICATION_EMAILS=["team@example.com"])
    @patch(
        "tickets.views.send_consultation_confirmation_email",
        side_effect=RuntimeError("SMTP unavailable"),
    )
    def test_consultation_thanks_reports_confirmation_email_failure(self, _send):
        response = self.client.post(
            reverse("consultation"),
            {
                "name": "Email Failure Test",
                "email": "email-failure@example.com",
                "phone": "",
                "location": "Sydney",
                "visa_interest": Case.VisaType.OTHER,
                "current_visa": "",
                "visa_expiry": "",
                "preferred_contact": ConsultationRequest.ContactMethod.EMAIL,
                "message": "Testing accurate delivery status.",
                "privacy_consent": "on",
            },
        )

        self.assertRedirects(response, reverse("consultation_thanks"))
        thanks = self.client.get(reverse("consultation_thanks"))
        self.assertContains(thanks, "Your confirmation email is delayed")
        self.assertNotContains(thanks, "a confirmation email has been sent")

    @override_settings(
        CONSULTATION_RATE_LIMIT_COUNT=1,
        CONSULTATION_RATE_LIMIT_WINDOW_SECONDS=600,
    )
    def test_consultation_rate_limit_blocks_repeated_submission(self):
        payload = {
            "name": "First Visitor",
            "email": "first@example.com",
            "phone": "",
            "location": "Sydney",
            "visa_interest": Case.VisaType.OTHER,
            "current_visa": "",
            "visa_expiry": "",
            "preferred_contact": ConsultationRequest.ContactMethod.EMAIL,
            "message": "First portfolio enquiry.",
            "privacy_consent": "on",
        }
        first = self.client.post(reverse("consultation"), payload)
        self.assertRedirects(first, reverse("consultation_thanks"))

        payload.update(
            {
                "name": "Second Visitor",
                "email": "second@example.com",
                "message": "Second portfolio enquiry.",
            }
        )
        second = self.client.post(reverse("consultation"), payload)

        self.assertEqual(second.status_code, 200)
        self.assertContains(second, "Too many consultation requests were submitted.")
        self.assertEqual(ConsultationRequest.objects.count(), 1)

    def test_consultation_rejects_impossible_calendar_date(self):
        response = self.client.post(
            reverse("consultation"),
            {
                "name": "Invalid Date",
                "email": "invalid-date@example.com",
                "phone": "0400 000 001",
                "location": "Sydney",
                "visa_interest": Case.VisaType.OTHER,
                "current_visa": "Student visa",
                "visa_expiry": "31/02/2027",
                "preferred_contact": ConsultationRequest.ContactMethod.EMAIL,
                "message": "Testing an impossible date.",
                "privacy_consent": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Enter a real date in DD/MM/YYYY format "
            "(day 01–31, month 01–12, year 1900–2100).",
        )
        self.assertFalse(
            ConsultationRequest.objects.filter(email="invalid-date@example.com").exists()
        )

    def test_consultation_rejects_date_outside_supported_year_range(self):
        response = self.client.post(
            reverse("consultation"),
            {
                "name": "Year Range Test",
                "email": "year-range@example.com",
                "phone": "0400000000",
                "location": "Sydney",
                "visa_interest": "other",
                "current_visa": "",
                "visa_expiry": "01/01/2200",
                "preferred_contact": "email",
                "message": "Testing an unreasonable year.",
                "privacy_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a year between 1900 and 2100.")
        self.assertFalse(
            ConsultationRequest.objects.filter(email="year-range@example.com").exists()
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_signup_creates_inactive_user_and_sends_hashed_code(self):
        response, user = self.signup_taylor()
        self.assertRedirects(response, reverse("verify_email"))
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])
        code = self.verification_code_from_email()
        verification = EmailVerification.objects.get(user=user)
        self.assertNotEqual(verification.code_hash, code)
        self.assertTrue(check_password(code, verification.code_hash))

    def test_correct_email_code_activates_and_logs_in_user(self):
        _, user = self.signup_taylor()
        code = self.verification_code_from_email()
        response = self.client.post(reverse("verify_email"), {"code": code})
        self.assertRedirects(response, reverse("dashboard"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_incorrect_email_code_counts_attempt(self):
        _, user = self.signup_taylor()
        correct_code = self.verification_code_from_email()
        wrong_code = "999999" if correct_code != "999999" else "888888"
        self.assertEqual(
            self.client.post(reverse("verify_email"), {"code": wrong_code}).status_code,
            200,
        )
        self.assertEqual(EmailVerification.objects.get(user=user).attempts, 1)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_expired_email_code_does_not_activate_user(self):
        _, user = self.signup_taylor()
        code = self.verification_code_from_email()
        verification = EmailVerification.objects.get(user=user)
        verification.expires_at = timezone.now() - timedelta(seconds=1)
        verification.save(update_fields=["expires_at"])
        self.assertEqual(
            self.client.post(reverse("verify_email"), {"code": code}).status_code, 200
        )
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_signup_page_loads_password_toggle_script(self):
        response = self.client.get(reverse("signup"))
        self.assertContains(response, "/static/js/app")

    def test_login_page_contains_collapsed_password_reset_panel(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Forgot password?")
        self.assertContains(response, "data-reset-panel")
        self.assertContains(response, "aria-hidden=\"true\"")
        self.assertContains(response, "hidden")

    def test_password_reset_code_is_sent_and_stored_as_a_hash(self):
        response = self.client.post(
            reverse("send_password_reset_code"), {"email": self.user.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(len(mail.outbox), 1)
        code = self.verification_code_from_email()
        verification = PasswordResetVerification.objects.get(user=self.user)
        self.assertNotEqual(verification.code_hash, code)
        self.assertTrue(check_password(code, verification.code_hash))

    def test_password_reset_request_does_not_reveal_unknown_email(self):
        response = self.client.post(
            reverse("send_password_reset_code"), {"email": "missing@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_resend_cooldown_prevents_duplicate_email(self):
        url = reverse("send_password_reset_code")
        self.client.post(url, {"email": self.user.email})
        self.client.post(url, {"email": self.user.email})
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        EMAIL_RATE_LIMIT_COUNT=1,
        EMAIL_RATE_LIMIT_WINDOW_SECONDS=3600,
    )
    def test_password_reset_email_rate_limit_applies_across_addresses(self):
        url = reverse("send_password_reset_code")
        self.client.post(url, {"email": self.user.email})
        second = self.client.post(url, {"email": self.other_user.email})

        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["ok"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(
            PasswordResetVerification.objects.filter(user=self.other_user).exists()
        )

    def test_correct_password_reset_code_changes_password_once(self):
        self.client.post(
            reverse("send_password_reset_code"), {"email": self.user.email}
        )
        code = self.verification_code_from_email()
        payload = {
            "email": self.user.email,
            "code": code,
            "new_password1": "New-strong-pass-941!",
            "new_password2": "New-strong-pass-941!",
        }
        response = self.client.post(reverse("confirm_password_reset"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-strong-pass-941!"))

        reused = self.client.post(reverse("confirm_password_reset"), payload)
        self.assertEqual(reused.status_code, 400)
        self.assertFalse(reused.json()["ok"])

    def test_incorrect_password_reset_code_counts_attempt(self):
        self.client.post(
            reverse("send_password_reset_code"), {"email": self.user.email}
        )
        correct_code = self.verification_code_from_email()
        wrong_code = "999999" if correct_code != "999999" else "888888"
        response = self.client.post(
            reverse("confirm_password_reset"),
            {
                "email": self.user.email,
                "code": wrong_code,
                "new_password1": "New-strong-pass-941!",
                "new_password2": "New-strong-pass-941!",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            PasswordResetVerification.objects.get(user=self.user).attempts, 1
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Strong-pass-841!"))

    def test_regular_user_only_sees_their_cases(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, self.own_case.title)
        self.assertNotContains(response, self.other_case.title)

    def test_staff_sees_all_cases(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, self.own_case.title)
        self.assertContains(response, self.other_case.title)

    def test_user_cannot_open_another_users_case(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("case_detail", kwargs={"pk": self.other_case.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_non_staff_cannot_create_or_edit_cases(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("case_create")).status_code, 404)
        self.assertEqual(
            self.client.get(reverse("case_edit", kwargs={"pk": self.own_case.pk})).status_code,
            404,
        )

    def test_staff_can_create_case_and_initial_event(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("case_create"),
            {
                "title": "Graduate pathway review",
                "client": self.user.pk,
                "visa_type": Case.VisaType.STUDENT,
                "stage": Case.Stage.ASSESSMENT,
                "advisor": self.staff.pk,
                "urgency": Case.Urgency.IMPORTANT,
                "summary": "Review the client's options after study.",
                "next_action": "Send qualification documents",
                "key_date": "2027-03-15",
            },
        )
        case = Case.objects.get(title="Graduate pathway review")
        self.assertRedirects(response, case.get_absolute_url())
        self.assertEqual(case.client, self.user)
        self.assertTrue(CaseEvent.objects.filter(case=case, title="Case opened").exists())

    def test_client_can_message_on_their_case(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.own_case.get_absolute_url(), {"body": "I have booked my test."}
        )
        self.assertRedirects(response, self.own_case.get_absolute_url())
        case_message = CaseMessage.objects.get(case=self.own_case)
        self.assertEqual(case_message.author, self.user)
        self.assertFalse(case_message.is_internal)

    def test_internal_staff_note_is_hidden_from_client(self):
        CaseMessage.objects.create(
            case=self.own_case,
            author=self.staff,
            body="Internal risk review only",
            is_internal=True,
        )
        self.client.force_login(self.user)
        response = self.client.get(self.own_case.get_absolute_url())
        self.assertNotContains(response, "Internal risk review only")

    def test_staff_can_update_stage_and_create_timeline_event(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("case_edit", kwargs={"pk": self.own_case.pk}),
            {
                "title": self.own_case.title,
                "client": self.user.pk,
                "visa_type": self.own_case.visa_type,
                "stage": Case.Stage.LODGED,
                "advisor": self.staff.pk,
                "urgency": Case.Urgency.TIME_SENSITIVE,
                "summary": self.own_case.summary,
                "next_action": "Await acknowledgement",
                "key_date": "2027-04-01",
            },
        )
        self.assertRedirects(response, self.own_case.get_absolute_url())
        self.own_case.refresh_from_db()
        self.assertEqual(self.own_case.stage, Case.Stage.LODGED)
        self.assertTrue(
            CaseEvent.objects.filter(
                case=self.own_case, title=self.own_case.get_stage_display()
            ).exists()
        )

    def test_staff_can_add_and_update_document_item(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("document_add", kwargs={"pk": self.own_case.pk}),
            {
                "name": "Passport bio page",
                "status": DocumentItem.Status.REQUESTED,
                "notes": "Colour scan",
            },
        )
        self.assertRedirects(response, self.own_case.get_absolute_url())
        document = DocumentItem.objects.get(case=self.own_case)
        response = self.client.post(
            reverse(
                "document_update",
                kwargs={"pk": self.own_case.pk, "document_pk": document.pk},
            ),
            {"status": DocumentItem.Status.ACCEPTED},
        )
        self.assertRedirects(response, self.own_case.get_absolute_url())
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentItem.Status.ACCEPTED)

    def test_dashboard_filters_by_stage_and_search_term(self):
        self.own_case.stage = Case.Stage.LODGED
        self.own_case.save()
        second = Case.objects.create(
            title="Employer nomination strategy",
            summary="Review employer sponsorship.",
            visa_type=Case.VisaType.EMPLOYER,
            client=self.user,
            stage=Case.Stage.FINALISED,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("dashboard"),
            {"stage": Case.Stage.FINALISED, "q": "nomination"},
        )
        self.assertContains(response, second.title)
        self.assertNotContains(response, self.own_case.title)
