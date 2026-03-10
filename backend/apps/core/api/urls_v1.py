from django.urls import path

from apps.core.api.me_view import UserProfileView
from apps.core.api.sessioni_view import SessioneRevocaView, SessioniAttiveListView
from apps.core.api.views import (
    ApiDiagnosticsErrorEnvelopeV1,
    ApiLookupCodiciV1,
    ApiPermessiAuditV1,
    ApiPermessiEffettiviV1,
)
from apps.core.api.search_view import (
    LookupComuniView,
    LookupTipiRuoliView,
    SearchDetailView,
    SearchUniversaleView,
)
from apps.core.api.views_tracciamento import (
    ApiAuditLogV1,
    ApiDominiTaskV1,
    ApiJobRunsV1,
    ApiJobSummaryV1,
    ApiTaskImplementationsV1,
    ApiTaskRegistryV1,
)

urlpatterns = [
    path(
        "me/",
        UserProfileView.as_view(),
        name="core-v1-user-profile",
    ),
    path(
        "me/sessioni/",
        SessioniAttiveListView.as_view(),
        name="core-v1-sessioni-attive",
    ),
    path(
        "me/sessioni/<str:jti>/revoca/",
        SessioneRevocaView.as_view(),
        name="core-v1-sessione-revoca",
    ),
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
        "lookup/tipi-ruoli/",
        LookupTipiRuoliView.as_view(),
        name="core-v1-lookup-tipi-ruoli",
    ),
    path(
        "lookup/comuni/",
        LookupComuniView.as_view(),
        name="core-v1-lookup-comuni",
    ),
    path(
        "users/<int:user_id>/permessi-effettivi/",
        ApiPermessiEffettiviV1.as_view(),
        name="core-v1-permessi-effettivi",
    ),
    path(
        "users/<int:user_id>/permessi-audit/",
        ApiPermessiAuditV1.as_view(),
        name="core-v1-permessi-audit",
    ),
    # Ricerca universale soggetti
    path(
        "search/",
        SearchUniversaleView.as_view(),
        name="core-v1-search-universale",
    ),
    path(
        "search/<uuid:soggetto_id>/detail/",
        SearchDetailView.as_view(),
        name="core-v1-search-detail",
    ),
    # Tracciamento processi e job
    path(
        "tracciamento/audit-log/",
        ApiAuditLogV1.as_view(),
        name="core-v1-audit-log",
    ),
    path(
        "tracciamento/domini-task/",
        ApiDominiTaskV1.as_view(),
        name="core-v1-domini-task",
    ),
    path(
        "tracciamento/task-registry/",
        ApiTaskRegistryV1.as_view(),
        name="core-v1-task-registry",
    ),
    path(
        "tracciamento/task-implementations/",
        ApiTaskImplementationsV1.as_view(),
        name="core-v1-task-implementations",
    ),
    path(
        "tracciamento/job-runs/",
        ApiJobRunsV1.as_view(),
        name="core-v1-job-runs",
    ),
    path(
        "tracciamento/job-summary/",
        ApiJobSummaryV1.as_view(),
        name="core-v1-job-summary",
    ),
]
