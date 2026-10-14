# Generated for the FlowDesk to Common Ground Migration domain transition.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def migrate_legacy_values(apps, schema_editor):
    Case = apps.get_model("tickets", "Case")
    visa_types = {
        "it_support": "other",
        "automation": "other",
        "ai_tool": "other",
        "access": "other",
        "other": "other",
    }
    urgencies = {
        "low": "routine",
        "medium": "important",
        "high": "time_sensitive",
        "urgent": "critical",
    }
    stages = {
        "new": "enquiry",
        "in_progress": "documents",
        "waiting": "awaiting_client",
        "resolved": "finalised",
    }
    for case in Case.objects.all().iterator():
        case.visa_type = visa_types.get(case.visa_type, "other")
        case.urgency = urgencies.get(case.urgency, "routine")
        case.stage = stages.get(case.stage, "enquiry")
        case.save(update_fields=["visa_type", "urgency", "stage"])


def restore_legacy_values(apps, schema_editor):
    Case = apps.get_model("tickets", "Case")
    stages = {
        "enquiry": "new",
        "assessment": "in_progress",
        "strategy": "in_progress",
        "documents": "in_progress",
        "awaiting_client": "waiting",
        "lodged": "in_progress",
        "awaiting_decision": "waiting",
        "finalised": "resolved",
    }
    for case in Case.objects.all().iterator():
        case.visa_type = "other"
        case.urgency = {
            "routine": "low",
            "important": "medium",
            "time_sensitive": "high",
            "critical": "urgent",
        }.get(case.urgency, "medium")
        case.stage = stages.get(case.stage, "new")
        case.save(update_fields=["visa_type", "urgency", "stage"])


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0002_emailverification"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(old_name="Ticket", new_name="Case"),
        migrations.RenameModel(old_name="Comment", new_name="CaseMessage"),
        migrations.RemoveIndex(
            model_name="case", name="tickets_tic_status_15eec8_idx"
        ),
        migrations.RemoveIndex(
            model_name="case", name="tickets_tic_request_c36389_idx"
        ),
        migrations.RenameField(model_name="case", old_name="description", new_name="summary"),
        migrations.RenameField(model_name="case", old_name="category", new_name="visa_type"),
        migrations.RenameField(model_name="case", old_name="priority", new_name="urgency"),
        migrations.RenameField(model_name="case", old_name="status", new_name="stage"),
        migrations.RenameField(model_name="case", old_name="requester", new_name="client"),
        migrations.RenameField(model_name="case", old_name="assignee", new_name="advisor"),
        migrations.RenameField(model_name="casemessage", old_name="ticket", new_name="case"),
        migrations.AlterModelOptions(name="case", options={"ordering": ["-updated_at"]}),
        migrations.AlterField(
            model_name="case",
            name="title",
            field=models.CharField(max_length=140, verbose_name="Case name"),
        ),
        migrations.AlterField(
            model_name="case",
            name="summary",
            field=models.TextField(
                help_text="A concise record of the client's situation, goals and relevant context.",
                verbose_name="Background and goals",
            ),
        ),
        migrations.AlterField(
            model_name="case",
            name="visa_type",
            field=models.CharField(
                choices=[
                    ("skilled", "Skilled migration"),
                    ("employer", "Employer sponsored"),
                    ("student", "Student & graduate"),
                    ("partner", "Partner & family"),
                    ("business", "Business & investment"),
                    ("other", "Not sure / other"),
                ],
                default="other",
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="case",
            name="urgency",
            field=models.CharField(
                choices=[
                    ("routine", "Routine"),
                    ("important", "Important"),
                    ("time_sensitive", "Time-sensitive"),
                    ("critical", "Critical deadline"),
                ],
                default="routine",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="case",
            name="stage",
            field=models.CharField(
                choices=[
                    ("enquiry", "Initial enquiry"),
                    ("assessment", "Eligibility assessment"),
                    ("strategy", "Strategy confirmed"),
                    ("documents", "Preparing documents"),
                    ("awaiting_client", "Waiting on client"),
                    ("lodged", "Application lodged"),
                    ("awaiting_decision", "Awaiting decision"),
                    ("finalised", "Finalised"),
                ],
                default="enquiry",
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="case",
            name="client",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="migration_cases",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="case",
            name="advisor",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"is_staff": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="advised_cases",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="casemessage",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="case_messages",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="casemessage",
            name="case",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="tickets.case",
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="key_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="case",
            name="next_action",
            field=models.CharField(blank=True, max_length=220),
        ),
        migrations.AddField(
            model_name="casemessage",
            name="is_internal",
            field=models.BooleanField(
                default=False, help_text="Internal notes are visible to staff only."
            ),
        ),
        migrations.RunPython(migrate_legacy_values, restore_legacy_values),
        migrations.AddIndex(
            model_name="case",
            index=models.Index(
                fields=["stage", "-updated_at"], name="tickets_cas_stage_4bb750_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="case",
            index=models.Index(
                fields=["client", "-updated_at"], name="tickets_cas_client_341585_idx"
            ),
        ),
        migrations.CreateModel(
            name="CaseEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=160)),
                ("detail", models.CharField(blank=True, max_length=300)),
                ("happened_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("visible_to_client", models.BooleanField(default=True)),
                (
                    "case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="tickets.case",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="case_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-happened_at", "-id"]},
        ),
        migrations.CreateModel(
            name="ConsultationRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("location", models.CharField(blank=True, max_length=120)),
                (
                    "visa_interest",
                    models.CharField(
                        choices=[
                            ("skilled", "Skilled migration"),
                            ("employer", "Employer sponsored"),
                            ("student", "Student & graduate"),
                            ("partner", "Partner & family"),
                            ("business", "Business & investment"),
                            ("other", "Not sure / other"),
                        ],
                        default="other",
                        max_length=24,
                    ),
                ),
                ("current_visa", models.CharField(blank=True, max_length=120)),
                ("visa_expiry", models.DateField(blank=True, null=True)),
                (
                    "preferred_contact",
                    models.CharField(
                        choices=[
                            ("email", "Email"),
                            ("phone", "Phone"),
                            ("video", "Video call"),
                        ],
                        default="email",
                        max_length=12,
                    ),
                ),
                ("message", models.TextField(max_length=2000)),
                ("privacy_consent", models.BooleanField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("contacted", "Contacted"),
                            ("booked", "Consultation booked"),
                            ("converted", "Converted to case"),
                            ("closed", "Closed"),
                        ],
                        default="new",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"is_staff": True},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="consultation_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DocumentItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=160)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("received", "Received"),
                            ("reviewing", "Under review"),
                            ("more_info", "More information needed"),
                            ("accepted", "Accepted"),
                        ],
                        default="requested",
                        max_length=16,
                    ),
                ),
                ("due_date", models.DateField(blank=True, null=True)),
                ("notes", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="tickets.case",
                    ),
                ),
            ],
            options={"ordering": ["status", "due_date", "name"]},
        ),
    ]
