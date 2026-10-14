from django.contrib import admin

from .models import (
    Case,
    CaseEvent,
    CaseMessage,
    ConsultationRequest,
    DocumentItem,
    EmailVerification,
    PasswordResetVerification,
)


class DocumentInline(admin.TabularInline):
    model = DocumentItem
    extra = 0


class MessageInline(admin.TabularInline):
    model = CaseMessage
    extra = 0
    readonly_fields = ("author", "body", "is_internal", "created_at")


class EventInline(admin.TabularInline):
    model = CaseEvent
    extra = 0


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_reference",
        "title",
        "client",
        "visa_type",
        "stage",
        "advisor",
        "key_date",
        "updated_at",
    )
    list_filter = ("stage", "visa_type", "urgency")
    search_fields = (
        "title",
        "summary",
        "client__username",
        "client__email",
    )
    autocomplete_fields = ("client", "advisor")
    inlines = (DocumentInline, MessageInline, EventInline)

    @admin.display(description="Reference")
    def case_reference(self, obj):
        return obj.reference


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "location",
        "visa_interest",
        "preferred_contact",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "visa_interest", "preferred_contact")
    search_fields = ("name", "email", "phone", "location", "current_visa", "message")
    autocomplete_fields = ("assigned_to",)


@admin.register(DocumentItem)
class DocumentItemAdmin(admin.ModelAdmin):
    list_display = ("name", "case", "status", "due_date", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "case__title", "case__client__email")


@admin.register(CaseMessage)
class CaseMessageAdmin(admin.ModelAdmin):
    list_display = ("case", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
    search_fields = ("body", "case__title", "author__username")


@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    list_display = ("case", "title", "happened_at", "visible_to_client")
    list_filter = ("visible_to_client",)
    search_fields = ("title", "detail", "case__title")


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "sent_at", "expires_at", "attempts", "verified_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("code_hash", "sent_at", "verified_at")


@admin.register(PasswordResetVerification)
class PasswordResetVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "sent_at", "expires_at", "attempts", "used_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("code_hash", "sent_at", "used_at")


admin.site.site_header = "Common Ground administration"
admin.site.site_title = "Common Ground"
admin.site.index_title = "Migration practice operations"
