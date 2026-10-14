from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction

from tickets.models import (
    Case,
    CaseEvent,
    CaseMessage,
    ConsultationRequest,
    DocumentItem,
    EmailVerification,
    PasswordResetVerification,
)


class Command(BaseCommand):
    help = (
        "Remove client/test accounts and business records while preserving staff "
        "and superuser accounts. Runs as a dry-run unless --apply is supplied."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the cleanup. Without this flag, only counts are displayed.",
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        removable_users = user_model.objects.filter(
            is_staff=False,
            is_superuser=False,
        )
        preserved_users = user_model.objects.filter(
            is_staff=True,
        ) | user_model.objects.filter(is_superuser=True)

        counts = {
            "non_staff_users": removable_users.distinct().count(),
            "staff_users_preserved": preserved_users.distinct().count(),
            "consultation_requests": ConsultationRequest.objects.count(),
            "cases": Case.objects.count(),
            "case_messages": CaseMessage.objects.count(),
            "case_events": CaseEvent.objects.count(),
            "document_items": DocumentItem.objects.count(),
            "email_verifications": EmailVerification.objects.count(),
            "password_reset_verifications": PasswordResetVerification.objects.count(),
            "sessions": Session.objects.count(),
            "admin_log_entries": LogEntry.objects.count(),
        }

        self.stdout.write("Portfolio data cleanup plan:")
        for name, count in counts.items():
            self.stdout.write(f"  {name}={count}")
        staff_names = ", ".join(
            preserved_users.distinct()
            .order_by("username")
            .values_list("username", flat=True)
        )
        self.stdout.write(f"  preserved_staff_usernames={staff_names or '(none)'}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry run only; no data was changed."))
            return

        with transaction.atomic():
            ConsultationRequest.objects.all().delete()
            Case.objects.all().delete()
            EmailVerification.objects.all().delete()
            PasswordResetVerification.objects.all().delete()
            removable_users.delete()
            Session.objects.all().delete()
            LogEntry.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Portfolio data cleanup complete; staff and superuser accounts were preserved."
            )
        )
