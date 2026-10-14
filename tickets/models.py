import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Case(models.Model):
    class VisaType(models.TextChoices):
        SKILLED = "skilled", "Skilled migration"
        EMPLOYER = "employer", "Employer sponsored"
        STUDENT = "student", "Student & graduate"
        PARTNER = "partner", "Partner & family"
        BUSINESS = "business", "Business & investment"
        OTHER = "other", "Not sure / other"

    class Urgency(models.TextChoices):
        ROUTINE = "routine", "Routine"
        IMPORTANT = "important", "Important"
        TIME_SENSITIVE = "time_sensitive", "Time-sensitive"
        CRITICAL = "critical", "Critical deadline"

    class Stage(models.TextChoices):
        ENQUIRY = "enquiry", "Initial enquiry"
        ASSESSMENT = "assessment", "Eligibility assessment"
        STRATEGY = "strategy", "Strategy confirmed"
        DOCUMENTS = "documents", "Preparing documents"
        AWAITING_CLIENT = "awaiting_client", "Waiting on client"
        LODGED = "lodged", "Application lodged"
        AWAITING_DECISION = "awaiting_decision", "Awaiting decision"
        FINALISED = "finalised", "Finalised"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=140, verbose_name="Case name")
    summary = models.TextField(
        verbose_name="Background and goals",
        help_text="A concise record of the client's situation, goals and relevant context.",
    )
    visa_type = models.CharField(
        max_length=24, choices=VisaType.choices, default=VisaType.OTHER
    )
    urgency = models.CharField(
        max_length=16, choices=Urgency.choices, default=Urgency.ROUTINE
    )
    stage = models.CharField(
        max_length=24, choices=Stage.choices, default=Stage.ENQUIRY
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="migration_cases",
    )
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="advised_cases",
        null=True,
        blank=True,
        limit_choices_to={"is_staff": True},
    )
    next_action = models.CharField(max_length=220, blank=True)
    key_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["stage", "-updated_at"],
                name="tickets_cas_stage_4bb750_idx",
            ),
            models.Index(
                fields=["client", "-updated_at"],
                name="tickets_cas_client_341585_idx",
            ),
        ]

    def __str__(self):
        return f"{self.reference} · {self.title}"

    @property
    def reference(self):
        return f"CGM-{str(self.id).split('-')[0].upper()}"

    @property
    def progress_percent(self):
        progress = {
            self.Stage.ENQUIRY: 8,
            self.Stage.ASSESSMENT: 20,
            self.Stage.STRATEGY: 35,
            self.Stage.DOCUMENTS: 52,
            self.Stage.AWAITING_CLIENT: 58,
            self.Stage.LODGED: 72,
            self.Stage.AWAITING_DECISION: 86,
            self.Stage.FINALISED: 100,
        }
        return progress.get(self.stage, 0)

    def get_absolute_url(self):
        return reverse("case_detail", kwargs={"pk": self.pk})


class CaseMessage(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="case_messages",
    )
    body = models.TextField(max_length=2000)
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal notes are visible to staff only.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message by {self.author} on {self.case.reference}"


class DocumentItem(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        RECEIVED = "received", "Received"
        REVIEWING = "reviewing", "Under review"
        MORE_INFO = "more_info", "More information needed"
        ACCEPTED = "accepted", "Accepted"

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=160)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.REQUESTED
    )
    due_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "due_date", "name"]

    def __str__(self):
        return f"{self.name} · {self.case.reference}"


class CaseEvent(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=160)
    detail = models.CharField(max_length=300, blank=True)
    happened_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="case_events",
    )
    visible_to_client = models.BooleanField(default=True)

    class Meta:
        ordering = ["-happened_at", "-id"]

    def __str__(self):
        return f"{self.title} · {self.case.reference}"


class ConsultationRequest(models.Model):
    class ContactMethod(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        VIDEO = "video", "Video call"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        BOOKED = "booked", "Consultation booked"
        CONVERTED = "converted", "Converted to case"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=120, blank=True)
    visa_interest = models.CharField(
        max_length=24, choices=Case.VisaType.choices, default=Case.VisaType.OTHER
    )
    current_visa = models.CharField(max_length=120, blank=True)
    visa_expiry = models.DateField(null=True, blank=True)
    preferred_contact = models.CharField(
        max_length=12, choices=ContactMethod.choices, default=ContactMethod.EMAIL
    )
    message = models.TextField(max_length=2000)
    privacy_consent = models.BooleanField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NEW
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"is_staff": True},
        related_name="consultation_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} · {self.get_visa_interest_display()}"


class EmailVerification(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification",
    )
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Email verification for {self.user}"


class PasswordResetVerification(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_verification",
    )
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Password reset verification for {self.user}"
