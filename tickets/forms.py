from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Case, CaseMessage, ConsultationRequest, DocumentItem


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Name")
    email = forms.EmailField(label="Email address")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("first_name", "email", "username", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class VerificationCodeForm(forms.Form):
    code = forms.RegexField(
        regex=r"^\d{6}$",
        label="Verification code",
        error_messages={"invalid": "Enter the six-digit code from your email."},
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "maxlength": "6",
                "placeholder": "000000",
                "class": "verification-input",
            }
        ),
    )


class ConsultationForm(forms.ModelForm):
    visa_expiry = forms.DateField(
        required=False,
        label="Current visa expiry (if known)",
        help_text="Use DD/MM/YYYY. Slashes are added automatically.",
        input_formats=["%d/%m/%Y"],
        error_messages={
            "invalid": (
                "Enter a real date in DD/MM/YYYY format "
                "(day 01–31, month 01–12, year 1900–2100)."
            )
        },
        widget=forms.DateInput(
            format="%d/%m/%Y",
            attrs={
                "placeholder": "DD/MM/YYYY",
                "inputmode": "numeric",
                "autocomplete": "off",
                "maxlength": "10",
                "pattern": "[0-9]{2}/[0-9]{2}/[0-9]{4}",
                "data-date-input": "dmy",
            },
        ),
    )
    privacy_consent = forms.BooleanField(
        label="I consent to Common Ground Migration contacting me about this enquiry."
    )

    class Meta:
        model = ConsultationRequest
        fields = (
            "name",
            "email",
            "phone",
            "location",
            "visa_interest",
            "current_visa",
            "visa_expiry",
            "preferred_contact",
            "message",
            "privacy_consent",
        )
        labels = {
            "location": "Where are you currently based?",
            "visa_interest": "What would you like help with?",
            "current_visa": "Current visa (if applicable)",
            "message": "Tell us briefly about your plans",
        }
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Your goals, timing and anything you are unsure about…",
                }
            ),
        }

    def clean_visa_expiry(self):
        visa_expiry = self.cleaned_data.get("visa_expiry")
        if visa_expiry and not date(1900, 1, 1) <= visa_expiry <= date(2100, 12, 31):
            raise forms.ValidationError(
                "Enter a year between 1900 and 2100."
            )
        return visa_expiry


class StaffCaseForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = (
            "title",
            "client",
            "visa_type",
            "stage",
            "advisor",
            "urgency",
            "summary",
            "next_action",
            "key_date",
        )
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 7}),
            "key_date": forms.DateInput(attrs={"type": "date"}),
            "next_action": forms.TextInput(
                attrs={"placeholder": "e.g. Upload certified passport copy"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["client"].queryset = user_model.objects.filter(
            is_active=True, is_staff=False
        ).order_by("first_name", "username")
        self.fields["advisor"].queryset = user_model.objects.filter(
            is_active=True, is_staff=True
        ).order_by("first_name", "username")


class CaseMessageForm(forms.ModelForm):
    class Meta:
        model = CaseMessage
        fields = ("body", "is_internal")
        labels = {
            "body": "Message",
            "is_internal": "Internal note — staff only",
        }
        widgets = {
            "body": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Share an update or ask a question…"}
            )
        }

    def __init__(self, *args, is_staff=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not is_staff:
            self.fields.pop("is_internal")


class DocumentItemForm(forms.ModelForm):
    class Meta:
        model = DocumentItem
        fields = ("name", "status", "due_date", "notes")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}
