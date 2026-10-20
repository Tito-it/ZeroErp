# API routing core (Core Django)

## Scopo

Indice delle rotte del dominio `core`: per ogni path, la view che lo serve e
la doc che ne descrive il contratto.

## Contesto

- Routing locale: `apps/core/api/urls_v1.py`.
- Include a livello progetto: `zeroerp_backend/urls.py`, riga
  `path("api/v1/core/", include("apps.core.api.urls_v1"))`.
- Le rotte di autenticazione (`/api/v1/auth/*`, `/api/v1/{admin,portale,shop}/token/*`)
  non stanno qui: sono dichiarate direttamente in `zeroerp_backend/urls.py`.

## Regole

- Base path unico: `/api/v1/core/`. Non esistono rotte legacy `/api/core/*`.
- Le view ereditano da `DomainAPIView` (JWT + permessi area, salvo
  `skip_area_check`).

## Rotte

Path relativi a `/api/v1/core/`. «—» = nessuna doc dedicata in questa cartella.

| Path | View | Doc |
| --- | --- | --- |
| `me/` | `UserProfileView` | [api_user_profile.md](api_user_profile.md) |
| `me/emittente-attivo/` | `EmittenteAttivoView` | [api_user_profile.md](api_user_profile.md) |
| `me/sessioni/` | `SessioniAttiveListView` | [api_sessioni_attive.md](api_sessioni_attive.md) |
| `me/sessioni/revoca-tutte/` | `SessioniRevocaTutteView` | [api_sessioni_attive.md](api_sessioni_attive.md) |
| `me/sessioni/<str:jti>/revoca/` | `SessioneRevocaView` | [api_sessioni_attive.md](api_sessioni_attive.md) |
| `diagnostics/error-envelope/` | `ApiDiagnosticsErrorEnvelope` | [api_diagnostics_error_envelope.md](api_diagnostics_error_envelope.md) |
| `lookup/codici/` | `ApiLookupCodici` | [api_lookup_codici.md](api_lookup_codici.md) |
| `lookup/tipi-ruoli/` | `LookupTipiRuoliView` | [api_search_universale.md](api_search_universale.md) |
| `lookup/tipi-soggetto-dettaglio/` | `LookupTipiSoggettoDettaglioView` | [api_lookup_dedicati.md](api_lookup_dedicati.md) |
| `lookup/tipi-soggetto-dettaglio/<int:tipo_soggetto_dettaglio_id>/indirizzi/` | `LookupMatriceIndirizziView` | [api_lookup_codici.md](api_lookup_codici.md) |
| `lookup/tipi-ruolo/<str:tipo_ruolo_codice>/indirizzi/` | `LookupMatriceIndirizziRuoloView` | [api_lookup_codici.md](api_lookup_codici.md) |
| `lookup/tipi-ruolo/<str:tipo_ruolo_codice>/utilities/` | `LookupUtilitiesPerRuoloView` | [api_lookup_codici.md](api_lookup_codici.md) |
| `lookup/utilities-per-emittente/` | `LookupUtilitiesPerEmittenteView` | [api_lookup_dedicati.md](api_lookup_dedicati.md) |
| `lookup/conti-contabili/` | `LookupContiContabiliView` | [api_lookup_dedicati.md](api_lookup_dedicati.md) |
| `lookup/tipi-entita/` | `LookupTipiEntitaView` | [api_tipi_entita_lookup.md](api_tipi_entita_lookup.md) |
| `lookup/tipi-ruoli-natura/` | `LookupTipiRuoliPerNaturaView` | [api_lookup_dedicati.md](api_lookup_dedicati.md) |
| `lookup/sistema-codici/` | `LookupSistemaCodiciView` | [api_lookup_dedicati.md](api_lookup_dedicati.md) |
| `lookup/forme-giuridiche/` | `LookupFormeGiuridicheView` | [api_lookup_dedicati.md](api_lookup_dedicati.md) |
| `lookup/comuni/` | `LookupComuniView` | [api_lookup_dedicati.md](api_lookup_dedicati.md) |
| `search/stradario/` | `SearchStradarioView` | [api_search_universale.md](api_search_universale.md) |
| `search/stradario-generale/` | `SearchStradarioGeneraleView` | [api_search_universale.md](api_search_universale.md) |
| `users/<int:user_id>/permessi-effettivi/` | `ApiPermessiEffettivi` | [api_permessi_effettivi.md](api_permessi_effettivi.md) |
| `users/<int:user_id>/permessi-audit/` | `ApiPermessiAudit` | [api_permessi_audit.md](api_permessi_audit.md) |
| `search/` | `SearchUniversaleView` | [api_search_universale.md](api_search_universale.md) |
| `search/<uuid:soggetto_id>/detail/` | `SearchDetailView` | [api_search_universale.md](api_search_universale.md) |
| `tracciamento/audit-log/` | `ApiAuditLog` | [api_tracciamento.md](api_tracciamento.md) |
| `tracciamento/domini-task/` | `ApiDominiTask` | [api_tracciamento.md](api_tracciamento.md) |
| `tracciamento/task-registry/` | `ApiTaskRegistry` | [api_tracciamento.md](api_tracciamento.md) |
| `tracciamento/task-implementations/` | `ApiTaskImplementations` | [api_tracciamento.md](api_tracciamento.md) |
| `tracciamento/job-runs/` | `ApiJobRuns` | [api_tracciamento.md](api_tracciamento.md) |
| `tracciamento/job-summary/` | `ApiJobSummary` | [api_tracciamento.md](api_tracciamento.md) |
| `tracciamento/code/conteggi/` | `ApiCodeConteggi` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-lavori/` | `ApiCodaLavoriList` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-lavori/<int:job_id>/` | `ApiCodaLavoriDetail` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-lavori/<int:job_id>/annulla/` | `ApiCodaLavoriAnnulla` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-lavori/<int:job_id>/requeue/` | `ApiCodaLavoriRequeue` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-lavori/archivia/` | `ApiCodaLavoriArchivia` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-lavori/ripristina/` | `ApiCodaLavoriRipristina` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-stampa/` | `ApiCodaStampaList` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-stampa/archivia/` | `ApiCodaStampaArchivia` | [api_gestione_code.md](api_gestione_code.md) |
| `tracciamento/coda-stampa/ripristina/` | `ApiCodaStampaRipristina` | [api_gestione_code.md](api_gestione_code.md) |
| `config/tables/` | `ConfigTablesListView` | [api_config_tables.md](api_config_tables.md) |
| `config/tables/<str:rel>/metadata/` | `ConfigTableMetadataView` | [api_config_tables.md](api_config_tables.md) |
| `config/tables/<str:rel>/` | `ConfigTableRecordsView` | [api_config_tables.md](api_config_tables.md) |
| `config/tables/<str:rel>/<int:pk>/` | `ConfigTableRecordDetailView` | [api_config_tables.md](api_config_tables.md) |
| `email/prepare/` | `EmailPrepareView` | [api_email.md](api_email.md) |
| `email/outbox/` | `EmailOutboxListView` | [api_email.md](api_email.md) |
| `email/outbox/<int:outbox_id>/` | `EmailOutboxDetailView` | [api_email.md](api_email.md) |
| `email/outbox/<int:outbox_id>/send/` | `EmailOutboxSendView` | [api_email.md](api_email.md) |
| `email/outbox/<int:outbox_id>/cancel/` | `EmailOutboxCancelView` | [api_email.md](api_email.md) |
| `email/outbox/<int:outbox_id>/allegati/` | `EmailAllegatoUploadView` | [api_email.md](api_email.md) |
| `email/outbox/<int:outbox_id>/allegati/list/` | `EmailAllegatoListView` | [api_email.md](api_email.md) |
| `email/allegati/<int:allegato_id>/` | `EmailAllegatoDeleteView` | [api_email.md](api_email.md) |
| `email/allegati/<int:allegato_id>/download/` | `EmailAllegatoDownloadView` | [api_email.md](api_email.md) |
| `email/log/` | `EmailLogOperatoreListView` | [api_email.md](api_email.md) |
| `email/log/stati/` | `EmailLogStatiLookupView` | [api_email.md](api_email.md) |
| `parameters/defaults/` | `ParameterDefaultsView` | [api_parameters.md](api_parameters.md) |
| `parameters/settings/` | `ParameterSettingsView` | [api_parameter_settings.md](api_parameter_settings.md) |
| `parameters/settings/override/` | `ParameterOverrideView` | [api_parameter_settings.md](api_parameter_settings.md) |
| `parameters/settings/override/<int:override_id>/` | `ParameterOverrideDeleteView` | [api_parameter_settings.md](api_parameter_settings.md) |

## Dipendenze DB

- Nessuna diretta.
