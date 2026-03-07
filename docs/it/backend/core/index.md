# Area 'core' (Backend)

## API
- [api-domain-conventions](manual/api-domain-conventions.md) — Definire uno standard unico per costruire future API di dominio.
- [api_diagnostics_error_envelope](manual/api_diagnostics_error_envelope.md) — Fornire un endpoint tecnico per validare contratto error envelope e policy retry.
- [api_endpoint_helpers](manual/api_endpoint_helpers.md) — Centralizzare il flusso standard dei POST JSON (parse, validazione base, envelope, idempotenza).
- [api_lookup_codici](manual/api_lookup_codici.md) — Espone una ricerca generica su tabelle di configurazione con struttura id / codice / descrizione. Permette autocompletamento e ricerca ILIKE da UI senza dover creare endpoint dedicati per ogni tabella config.
- [api_pagination](manual/api_pagination.md) — Fornire configurazioni DRF standard per paginazione coerente su endpoint list/search.
- [api_permessi_audit](manual/api_permessi_audit.md) — Endpoint che restituisce la timeline audit delle modifiche ai permessi di un utente. Interroga le 7 tabelle storico del sistema permessi con filtri opzionali e paginazione.
- [api_permessi_effettivi](manual/api_permessi_effettivi.md) — Esporre un endpoint diagnostico che restituisce i permessi effettivi risolti per un utente, iterando tutte le aree funzionali attive e mostrando il livello di accesso, le azioni consentite e lo stato del profilo reparto.
- [api_response_envelope](manual/api_response_envelope.md) — Definire il formato uniforme delle risposte successo/errore per tutte le API.
- [api_retry_policies](manual/api_retry_policies.md) — Uniformare gestione idempotency key e semantica retry lato API.
- [api_routing_core](manual/api_routing_core.md) — Documentare il routing core tra path legacy e path versionato v1.
- [api_search_validation](manual/api_search_validation.md) — Evitare query di ricerca troppo generiche che degradano performance e selettivita`.
- [api_throttling](manual/api_throttling.md) — Limitare burst di chiamate sugli endpoint search per proteggere backend e DB.
- [api_tracciamento](manual/api_tracciamento.md) — Espone in lettura i tre livelli di tracciamento del sistema: audit log operativo, task registry multi-dominio e log esecuzioni job pgAgent. Fornisce agli anelli esterni e alla futura UI una vista unificata sulle operazi…
- [api_write_checklist](manual/api_write_checklist.md) — Fornire una checklist operativa pronta per nuovi endpoint write (POST/PUT/PATCH/DELETE con side effect).
- [error-handling-api](manual/error-handling-api.md) — Definire un contratto errore uniforme per tutte le API backend Django.
- [payload-validation-api](manual/payload-validation-api.md) — Centralizzare validazioni/coercizioni dei payload JSON API per ridurre logica duplicata nelle view dominio.
- [request-context-api](manual/request-context-api.md) — Assegnare metadati di correlazione request (request_id) e idempotenza (idempotency_key) in modo uniforme per tutte le API.
- [request-parsing-api](manual/request-parsing-api.md) — Centralizzare parsing JSON/body e parsing date ISO per le API Django.

## Utility
- [value-normalizer](manual/value-normalizer.md) — Centralizzare utility riusabili di normalizzazione valori input.

## Altri contenuti
- [auth_views_audit](manual/auth_views_audit.md) — Override delle view SimpleJWT per registrare eventi di login e refresh nella tabella dbops.sessioni_utente.
- [emittente_fiscale_scope_mixin](manual/emittente_fiscale_scope_mixin.md) — Mixin per ViewSet e GenericAPIView che filtra automaticamente il queryset in base agli emittenti fiscali autorizzati per l'utente corrente.
- [gen-bk-docs](manual/gen-bk-docs.md) — Automatizzare la generazione degli indici index.md (e opzionalmente index.ci.md) per docs/it/backend/<area>/, includendo una descrizione breve estratta dalla sezione **Scopo**.
- [jwt_audit_middleware](manual/jwt_audit_middleware.md) — Middleware Django che propaga l'identita' dell'utente autenticato nella sessione PostgreSQL tramite GUC (SET LOCAL) e rifiuta anticipatamente gli utenti disabilitati sugli endpoint API.
- [permissions_cache](manual/permissions_cache.md) — Cache Redis L2 per i permessi utente. Integra la cache per-request (L1 dict) con Redis (L2) per evitare query DB su ogni richiesta HTTP.
- [permissions_resolver](manual/permissions_resolver.md) — Risolutore centrale dei permessi ZeroErp. Implementa la catena di risoluzione: ruolo_sistema → override utente → profilo reparto → BLOCCATO (default sicuro).
- [request_log_middleware](manual/request_log_middleware.md) — Registrare ogni request API autenticata nella tabella dbops.request_log con metodo, path, status, durata e utente.
- [session_audit_service](manual/session_audit_service.md) — Registrare eventi di sessione JWT (login, refresh) nella tabella dbops.sessioni_utente.
- [zeroerp_permission](manual/zeroerp_permission.md) — Permission class DRF centrale per ZeroErp. Risolve automaticamente l'area funzionale dallo schema del model e verifica il livello di accesso tramite PermissionResolver.
