from django.urls import path

from apps.core.api.views import diagnostics_error_envelope

urlpatterns = [
    path(
        "diagnostics/error-envelope/",
        diagnostics_error_envelope,
        name="core-diagnostics-error-envelope",
    ),
]
