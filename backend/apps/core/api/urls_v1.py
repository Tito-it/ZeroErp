from django.urls import path

from apps.core.api.me_view import UserProfileView
from apps.core.api.sessioni_view import SessioneRevocaView, SessioniAttiveListView
from apps.core.api.views import (
    ApiDiagnosticsErrorEnvelope,
    ApiLookupCodici,
    ApiPermessiAudit,
    ApiPermessiEffettivi,
)
from apps.core.api.search_view import (
    LookupTipiRuoliView,
    SearchDetailView,
    SearchUniversaleView,
)
from apps.core.api.views_lookup import (
    LookupComuniView,
    LookupFormeGiuridicheView,
    LookupMatriceIndirizziView,
    LookupMatriceIndirizziRuoloView,
    LookupSistemaCodiciView,
    LookupTipiRuoliPerNaturaView,
    LookupTipiSoggettoDettaglioView,
    SearchStradarioGeneraleView,
    SearchStradarioView,
)
from apps.core.api.views_config_crud import (
    ConfigTableMetadataView,
    ConfigTableRecordDetailView,
    ConfigTableRecordsView,
    ConfigTablesListView,
)
from apps.core.api.views_tracciamento import (
    ApiAuditLog,
    ApiDominiTask,
    ApiJobRuns,
    ApiJobSummary,
    ApiTaskImplementations,
    ApiTaskRegistry,
)

urlpatterns = [
    path(
        "me/",
        UserProfileView.as_view(),
        name="core-user-profile",
    ),
    path(
        "me/sessioni/",
        SessioniAttiveListView.as_view(),
        name="core-sessioni-attive",
    ),
    path(
        "me/sessioni/<str:jti>/revoca/",
        SessioneRevocaView.as_view(),
        name="core-sessione-revoca",
    ),
    path(
        "diagnostics/error-envelope/",
        ApiDiagnosticsErrorEnvelope.as_view(),
        name="core-diagnostics-error-envelope",
    ),
    path(
        "lookup/codici/",
        ApiLookupCodici.as_view(),
        name="core-lookup-codici",
    ),
    path(
        "lookup/tipi-ruoli/",
        LookupTipiRuoliView.as_view(),
        name="core-lookup-tipi-ruoli",
    ),
    # Lookup anagrafiche cross-dominio (Sprint 3)
    path(
        "lookup/tipi-soggetto-dettaglio/",
        LookupTipiSoggettoDettaglioView.as_view(),
        name="core-lookup-tipi-soggetto-dettaglio",
    ),
    path(
        "lookup/tipi-soggetto-dettaglio/<int:tipo_soggetto_dettaglio_id>/indirizzi/",
        LookupMatriceIndirizziView.as_view(),
        name="core-lookup-matrice-indirizzi",
    ),
    path(
        "lookup/tipi-ruolo/<str:tipo_ruolo_codice>/indirizzi/",
        LookupMatriceIndirizziRuoloView.as_view(),
        name="core-lookup-matrice-indirizzi-ruolo",
    ),
    path(
        "lookup/tipi-ruoli-natura/",
        LookupTipiRuoliPerNaturaView.as_view(),
        name="core-lookup-tipi-ruoli-natura",
    ),
    path(
        "lookup/sistema-codici/",
        LookupSistemaCodiciView.as_view(),
        name="core-lookup-sistema-codici",
    ),
    path(
        "lookup/forme-giuridiche/",
        LookupFormeGiuridicheView.as_view(),
        name="core-lookup-forme-giuridiche",
    ),
    path(
        "lookup/comuni/",
        LookupComuniView.as_view(),
        name="core-lookup-comuni",
    ),
    path(
        "search/stradario/",
        SearchStradarioView.as_view(),
        name="core-search-stradario",
    ),
    path(
        "search/stradario-generale/",
        SearchStradarioGeneraleView.as_view(),
        name="core-search-stradario-generale",
    ),
    path(
        "users/<int:user_id>/permessi-effettivi/",
        ApiPermessiEffettivi.as_view(),
        name="core-permessi-effettivi",
    ),
    path(
        "users/<int:user_id>/permessi-audit/",
        ApiPermessiAudit.as_view(),
        name="core-permessi-audit",
    ),
    # Ricerca universale soggetti
    path(
        "search/",
        SearchUniversaleView.as_view(),
        name="core-search-universale",
    ),
    path(
        "search/<uuid:soggetto_id>/detail/",
        SearchDetailView.as_view(),
        name="core-search-detail",
    ),
    # Tracciamento processi e job
    path(
        "tracciamento/audit-log/",
        ApiAuditLog.as_view(),
        name="core-audit-log",
    ),
    path(
        "tracciamento/domini-task/",
        ApiDominiTask.as_view(),
        name="core-domini-task",
    ),
    path(
        "tracciamento/task-registry/",
        ApiTaskRegistry.as_view(),
        name="core-task-registry",
    ),
    path(
        "tracciamento/task-implementations/",
        ApiTaskImplementations.as_view(),
        name="core-task-implementations",
    ),
    path(
        "tracciamento/job-runs/",
        ApiJobRuns.as_view(),
        name="core-job-runs",
    ),
    path(
        "tracciamento/job-summary/",
        ApiJobSummary.as_view(),
        name="core-job-summary",
    ),
    # --- Config CRUD generico ---
    path("config/tables/", ConfigTablesListView.as_view(), name="core-config-tables"),
    path("config/tables/<str:rel>/metadata/", ConfigTableMetadataView.as_view(), name="core-config-metadata"),
    path("config/tables/<str:rel>/", ConfigTableRecordsView.as_view(), name="core-config-records"),
    path("config/tables/<str:rel>/<int:pk>/", ConfigTableRecordDetailView.as_view(), name="core-config-record-detail"),
]
