from django.urls import path

from apps.core.api.emittente_attivo_views import EmittenteAttivoView
from apps.core.api.me_view import UserProfileView
from apps.core.api.sessioni_view import (
    SessioneRevocaView,
    SessioniAttiveListView,
    SessioniRevocaTutteView,
)
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
    LookupContiContabiliView,
    LookupTipiEntitaView,
    LookupAzioniRigaView,
    LookupFormeGiuridicheView,
    LookupMatriceIndirizziView,
    LookupMatriceIndirizziRuoloView,
    LookupSistemaCodiciView,
    LookupTipiRuoliPerNaturaView,
    LookupTipiSoggettoDettaglioView,
    LookupUtilitiesPerEmittenteView,
    LookupUtilitiesPerRuoloView,
    SearchStradarioGeneraleView,
    SearchStradarioView,
)
from apps.core.api.views_config_crud import (
    ConfigTableMetadataView,
    ConfigTableRecordDetailView,
    ConfigTableRecordsView,
    ConfigTablesListView,
)
from apps.core.api.email_views import (
    EmailAllegatoDeleteView,
    EmailAllegatoDownloadView,
    EmailAllegatoListView,
    EmailAllegatoUploadView,
    EmailLogOperatoreListView,
    EmailLogStatiLookupView,
    EmailOutboxCancelView,
    EmailOutboxDetailView,
    EmailOutboxListView,
    EmailOutboxSendView,
    EmailPrepareView,
)
from apps.core.api.views_parameters import (
    ParameterDefaultsView,
    ParameterOverrideDeleteView,
    ParameterOverrideView,
    ParameterSettingsView,
)
from apps.core.api.views_tracciamento import (
    ApiAuditLog,
    ApiCodaLavoriAnnulla,
    ApiCodaLavoriArchivia,
    ApiCodaLavoriDetail,
    ApiCodaLavoriList,
    ApiCodaLavoriRequeue,
    ApiCodaLavoriRipristina,
    ApiCodaStampaArchivia,
    ApiCodaStampaList,
    ApiCodaStampaRipristina,
    ApiCodeConteggi,
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
        "me/emittente-attivo/",
        EmittenteAttivoView.as_view(),
        name="core-emittente-attivo",
    ),
    path(
        "me/sessioni/",
        SessioniAttiveListView.as_view(),
        name="core-sessioni-attive",
    ),
    path(
        "me/sessioni/revoca-tutte/",
        SessioniRevocaTutteView.as_view(),
        name="core-sessioni-revoca-tutte",
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
        "lookup/tipi-ruolo/<str:tipo_ruolo_codice>/utilities/",
        LookupUtilitiesPerRuoloView.as_view(),
        name="core-lookup-utilities-per-ruolo",
    ),
    path(
        "lookup/utilities-per-emittente/",
        LookupUtilitiesPerEmittenteView.as_view(),
        name="core-lookup-utilities-per-emittente",
    ),
    path(
        "lookup/conti-contabili/",
        LookupContiContabiliView.as_view(),
        name="core-lookup-conti-contabili",
    ),
    path(
        "lookup/tipi-entita/",
        LookupTipiEntitaView.as_view(),
        name="core-lookup-tipi-entita",
    ),
    path(
        "lookup/azioni-riga/",
        LookupAzioniRigaView.as_view(),
        name="core-lookup-azioni-riga",
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
    # Gestione code (brief-be-fe-gestione-code-lavori-stampa): badge conteggi,
    # liste coda lavori/stampa, dettaglio job e azioni annulla/requeue.
    path(
        "tracciamento/code/conteggi/",
        ApiCodeConteggi.as_view(),
        name="core-code-conteggi",
    ),
    path(
        "tracciamento/coda-lavori/",
        ApiCodaLavoriList.as_view(),
        name="core-coda-lavori-list",
    ),
    path(
        "tracciamento/coda-lavori/<int:job_id>/",
        ApiCodaLavoriDetail.as_view(),
        name="core-coda-lavori-detail",
    ),
    path(
        "tracciamento/coda-lavori/<int:job_id>/annulla/",
        ApiCodaLavoriAnnulla.as_view(),
        name="core-coda-lavori-annulla",
    ),
    path(
        "tracciamento/coda-lavori/<int:job_id>/requeue/",
        ApiCodaLavoriRequeue.as_view(),
        name="core-coda-lavori-requeue",
    ),
    # Archiviazione: toglie le righe dall'ELENCO senza toccarne lo stato, cosi'
    # i conteggi restano fermi (brief-db-archiviazione-righe-code, 2026-09-04).
    # ⭐ Rotte di COLLEZIONE con l'elenco nel corpo (`{"ids": [...]}`): il menu
    # di riga manda un elenco di uno. Un verbo di massa e uno singolo sarebbero
    # due contratti da tenere allineati per lo stesso rifiuto, che e' per riga.
    path(
        "tracciamento/coda-lavori/archivia/",
        ApiCodaLavoriArchivia.as_view(),
        name="core-coda-lavori-archivia",
    ),
    path(
        "tracciamento/coda-lavori/ripristina/",
        ApiCodaLavoriRipristina.as_view(),
        name="core-coda-lavori-ripristina",
    ),
    path(
        "tracciamento/coda-stampa/",
        ApiCodaStampaList.as_view(),
        name="core-coda-stampa-list",
    ),
    path(
        "tracciamento/coda-stampa/archivia/",
        ApiCodaStampaArchivia.as_view(),
        name="core-coda-stampa-archivia",
    ),
    path(
        "tracciamento/coda-stampa/ripristina/",
        ApiCodaStampaRipristina.as_view(),
        name="core-coda-stampa-ripristina",
    ),
    # --- Config CRUD generico ---
    path("config/tables/", ConfigTablesListView.as_view(), name="core-config-tables"),
    path("config/tables/<str:rel>/metadata/", ConfigTableMetadataView.as_view(), name="core-config-metadata"),
    path("config/tables/<str:rel>/", ConfigTableRecordsView.as_view(), name="core-config-records"),
    path("config/tables/<str:rel>/<int:pk>/", ConfigTableRecordDetailView.as_view(), name="core-config-record-detail"),
    # --- Email operatore (outbox, allegati, log) ---
    path("email/prepare/", EmailPrepareView.as_view(), name="core-email-prepare"),
    path("email/outbox/", EmailOutboxListView.as_view(), name="core-email-outbox-list"),
    path("email/outbox/<int:outbox_id>/", EmailOutboxDetailView.as_view(), name="core-email-outbox-detail"),
    path("email/outbox/<int:outbox_id>/send/", EmailOutboxSendView.as_view(), name="core-email-outbox-send"),
    path("email/outbox/<int:outbox_id>/cancel/", EmailOutboxCancelView.as_view(), name="core-email-outbox-cancel"),
    path("email/outbox/<int:outbox_id>/allegati/", EmailAllegatoUploadView.as_view(), name="core-email-allegato-upload"),
    path("email/outbox/<int:outbox_id>/allegati/list/", EmailAllegatoListView.as_view(), name="core-email-allegato-list"),
    path("email/allegati/<int:allegato_id>/", EmailAllegatoDeleteView.as_view(), name="core-email-allegato-delete"),
    path("email/allegati/<int:allegato_id>/download/", EmailAllegatoDownloadView.as_view(), name="core-email-allegato-download"),
    path("email/log/", EmailLogOperatoreListView.as_view(), name="core-email-log-list"),
    path("email/log/stati/", EmailLogStatiLookupView.as_view(), name="core-email-log-stati-lookup"),
    # --- Parametri di sistema ---
    path("parameters/defaults/", ParameterDefaultsView.as_view(), name="core-parameters-defaults"),
    path("parameters/settings/", ParameterSettingsView.as_view(), name="core-parameters-settings"),
    path("parameters/settings/override/", ParameterOverrideView.as_view(), name="core-parameters-override"),
    path("parameters/settings/override/<int:override_id>/", ParameterOverrideDeleteView.as_view(), name="core-parameters-override-delete"),
]
