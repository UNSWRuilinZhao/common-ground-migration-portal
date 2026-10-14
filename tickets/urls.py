from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("services/", views.services, name="services"),
    path("about/", views.about, name="about"),
    path("guides/", views.guides, name="guides"),
    path("consultation/", views.consultation, name="consultation"),
    path(
        "consultation/thank-you/",
        views.consultation_thanks,
        name="consultation_thanks",
    ),
    path("health/", views.health, name="health"),
    path("signup/", views.signup, name="signup"),
    path("verify-email/", views.verify_email, name="verify_email"),
    path(
        "verify-email/resend/",
        views.resend_verification,
        name="resend_verification",
    ),
    path(
        "accounts/password-reset/send-code/",
        views.send_password_reset_code,
        name="send_password_reset_code",
    ),
    path(
        "accounts/password-reset/confirm/",
        views.confirm_password_reset,
        name="confirm_password_reset",
    ),
    path("portal/", views.dashboard, name="dashboard"),
    path("portal/cases/new/", views.case_create, name="case_create"),
    path("portal/cases/<uuid:pk>/", views.case_detail, name="case_detail"),
    path("portal/cases/<uuid:pk>/edit/", views.case_edit, name="case_edit"),
    path(
        "portal/cases/<uuid:pk>/documents/add/",
        views.document_add,
        name="document_add",
    ),
    path(
        "portal/cases/<uuid:pk>/documents/<int:document_pk>/update/",
        views.document_update,
        name="document_update",
    ),
]
