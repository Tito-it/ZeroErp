from django.urls import path

from apps.core.api.views import ApiDiagnosticsErrorEnvelopeV1

urlpatterns = [
    path(
        "diagnostics/error-envelope/",
        ApiDiagnosticsErrorEnvelopeV1.as_view(),
        name="core-v1-diagnostics-error-envelope",
    ),
]
