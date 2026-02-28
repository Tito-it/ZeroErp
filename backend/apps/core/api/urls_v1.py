from django.urls import path

from apps.core.api.views import (
    ApiDiagnosticsErrorEnvelopeV1,
    ApiLookupCodiciV1,
    ApiPermessiEffettiviV1,
)

urlpatterns = [
    path(
        "diagnostics/error-envelope/",
        ApiDiagnosticsErrorEnvelopeV1.as_view(),
        name="core-v1-diagnostics-error-envelope",
    ),
    path(
        "lookup/codici/",
        ApiLookupCodiciV1.as_view(),
        name="core-v1-lookup-codici",
    ),
    path(
        "users/<int:user_id>/permessi-effettivi/",
        ApiPermessiEffettiviV1.as_view(),
        name="core-v1-permessi-effettivi",
    ),
]
