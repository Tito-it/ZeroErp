from django.urls import path

from apps.core.api.views import ApiDiagnosticsErrorEnvelope

urlpatterns = [
    path(
        "diagnostics/error-envelope/",
        ApiDiagnosticsErrorEnvelope.as_view(),
        name="core-diagnostics-error-envelope",
    ),
]
