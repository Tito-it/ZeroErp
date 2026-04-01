# Catalogo Building Block — Backend

> Inventario dei componenti riutilizzabili nel backend Django.
> Prima di implementare logica nuova, verificare se esiste già un building block adatto.
>
> Documento vivo — aggiornare ogni volta che si aggiunge un building block.

---

## API Helpers (`apps/core/api/`)

| Building Block | File | Descrizione |
|---|---|---|
| `handle_post_json` | [endpoint_helpers.py](../../../../backend/apps/core/api/endpoint_helpers.py) | Handler unificato POST JSON con supporto idempotency |
| `get_scope_user_id` | [endpoint_helpers.py](../../../../backend/apps/core/api/endpoint_helpers.py) | Restituisce auth_user_id per scope filtering (None per superuser) |
| `get_risorsa_umana_id` | [endpoint_helpers.py](../../../../backend/apps/core/api/endpoint_helpers.py) | Risolve risorsa_umana_id dall'utente con cache per-request |
| `DomainAPIView` | [base_views.py](../../../../backend/apps/core/api/base_views.py) | Base view per endpoint dominio con JWT + ZeroERPPermission |
| `AdminAPIView` | [base_views.py](../../../../backend/apps/core/api/base_views.py) | Base view per endpoint admin-only |
| `StandardPageNumberPagination` | [pagination.py](../../../../backend/apps/core/api/pagination.py) | Paginazione DRF standard (50 default, 200 max) |
| `StandardCursorPagination` | [pagination.py](../../../../backend/apps/core/api/pagination.py) | Paginazione DRF a cursore per data_update |
| `parse_list_params` | [payload_validators.py](../../../../backend/apps/core/api/payload_validators.py) | Parsing standard parametri lista (page, page_size, order, search) |
| `paginated_envelope` | [payload_validators.py](../../../../backend/apps/core/api/payload_validators.py) | Envelope risposta paginata standard |
| `qp_bool` / `qp_int` / `qp_str` | [payload_validators.py](../../../../backend/apps/core/api/payload_validators.py) | Normalizzazione query params (bool, int, string) |
| `qp_int_strict` | [payload_validators.py](../../../../backend/apps/core/api/payload_validators.py) | Parsing int rigoroso con errore se non valido |
| `optional_int` / `optional_bool` / `optional_iso_date` / `optional_uuid` | [payload_validators.py](../../../../backend/apps/core/api/payload_validators.py) | Validazione campi opzionali da payload JSON |
| `require_min_search_length` | [search_validators.py](../../../../backend/apps/core/api/search_validators.py) | Validazione lunghezza minima termine di ricerca |
| `validate_order_params` | [search_validators.py](../../../../backend/apps/core/api/search_validators.py) | Validazione colonne di ordinamento contro whitelist |
| `parse_json_body` | [request_parsers.py](../../../../backend/apps/core/api/request_parsers.py) | Parsing e validazione body JSON dalla request |
| `parse_iso_date` | [request_parsers.py](../../../../backend/apps/core/api/request_parsers.py) | Parsing stringa data ISO |
| `success_response` | [success_responses.py](../../../../backend/apps/core/api/success_responses.py) | Envelope risposta successo unificata con metadata |
| `invalid_json_response` / `invalid_payload_response` | [error_responses.py](../../../../backend/apps/core/api/error_responses.py) | Risposte errore 400 standard |
| `exception_to_error_response` | [error_responses.py](../../../../backend/apps/core/api/error_responses.py) | Conversione eccezione in envelope errore unificata |
| `drf_exception_handler` | [error_responses.py](../../../../backend/apps/core/api/error_responses.py) | Handler eccezioni DRF con mapping unificato |
| `IsAdminZeroERP` | [permissions.py](../../../../backend/apps/core/api/permissions.py) | Permission check per ruolo ADMIN |
| `ZeroERPPermission` | [permissions.py](../../../../backend/apps/core/api/permissions.py) | Permission resolver centrale con area/action/livello |
| `LoginRateThrottle` | [throttling.py](../../../../backend/apps/core/api/throttling.py) | Rate limit login (5/5min) |
| `PasswordResetRateThrottle` | [throttling.py](../../../../backend/apps/core/api/throttling.py) | Rate limit reset password (3/15min) |
| `SearchBurstRateThrottle` | [throttling.py](../../../../backend/apps/core/api/throttling.py) | Rate limit endpoint search |
| `get_idempotency_key` | [retry_policies.py](../../../../backend/apps/core/api/retry_policies.py) | Estrae Idempotency-Key dagli header |
| `apply_retry_headers` | [retry_policies.py](../../../../backend/apps/core/api/retry_policies.py) | Aggiunge header Retry-After se errore ritentabile |
| `DEFAULT_LIMIT` / `MAX_LIMIT` | [constants.py](../../../../backend/apps/core/api/constants.py) | Costanti paginazione (50 / 200) |

---

## Services (`apps/core/services/`)

| Building Block | File | Descrizione |
|---|---|---|
| `ErrorManager.raise_error` | [error_manager.py](../../../../backend/apps/core/services/error_manager.py) | Lancia ServiceError strutturato con logging opzionale a DB |
| `ErrorManager.require` | [error_manager.py](../../../../backend/apps/core/services/error_manager.py) | Guard condizionale — lancia errore se condizione falsa |
| `ErrorManager.log_error_only` | [error_manager.py](../../../../backend/apps/core/services/error_manager.py) | Log errore a DB senza lanciare eccezione |
| `ServiceError` | [service_errors.py](../../../../backend/apps/core/services/service_errors.py) | Eccezione applicativa standard (code, message, detail, hint, retryable) |
| `ErrorTranslator.to_api_error` | [error_translator.py](../../../../backend/apps/core/services/error_translator.py) | Converte eccezione in ApiError con policy applicata |
| `ErrorPolicyRegistry.resolve` | [error_policies.py](../../../../backend/apps/core/services/error_policies.py) | Risolve policy errore (http_status, ui_action, user_message) da codice |
| `EmailDispatchService.send_email` | [email_service.py](../../../../backend/apps/core/services/email_service.py) | Invio email con risoluzione template/account e logging |
| `EmailDispatchService.resolve_and_render` | [email_service.py](../../../../backend/apps/core/services/email_service.py) | Risolve template + account con fallback e renderizza variabili |
| `EmailDispatchService.send_raw` | [email_service.py](../../../../backend/apps/core/services/email_service.py) | Invio email pre-renderizzata (senza risoluzione template) |
| `EmailDispatchService.retry_log_entry` | [email_service.py](../../../../backend/apps/core/services/email_service.py) | Ritenta invio email fallita da log |
| `EmailDispatchService.test_connection` | [email_service.py](../../../../backend/apps/core/services/email_service.py) | Test connessione SMTP per account |
| `EmailOutboxService.prepare_draft` | [email_outbox_service.py](../../../../backend/apps/core/services/email_outbox_service.py) | Crea bozza email editabile con template risolto |
| `EmailOutboxService.confirm_and_send` | [email_outbox_service.py](../../../../backend/apps/core/services/email_outbox_service.py) | Conferma e invia bozza email |
| `EmailOutboxService.add_attachment` | [email_outbox_service.py](../../../../backend/apps/core/services/email_outbox_service.py) | Aggiunge allegato a bozza email |
| `TokenService.create` | [token_service.py](../../../../backend/apps/core/services/token_service.py) | Crea token monouso (restituisce testo in chiaro una sola volta) |
| `TokenService.validate` | [token_service.py](../../../../backend/apps/core/services/token_service.py) | Valida token senza consumarlo |
| `TokenService.consume` | [token_service.py](../../../../backend/apps/core/services/token_service.py) | Consuma token (marca come usato) |
| `PermissionResolver.get_ruolo_sistema` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Ruolo utente (ADMIN, OPERATIVO, DISABILITATO) |
| `PermissionResolver.get_livello_area` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Livello accesso per area (TUTTO, LETTURA, BLOCCATO) |
| `PermissionResolver.check_azione` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Verifica se azione processo è consentita |
| `PermissionResolver.get_emittenti_ids` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | ID emittenti fiscali autorizzati per l'utente |
| `load_user_cache` / `invalidate_user` / `invalidate_all` | [permissions_cache.py](../../../../backend/apps/core/services/permissions_cache.py) | Cache permessi Redis L2 (load, invalidate utente/reparto/tutti) |
| `encrypt` / `decrypt` | [crypto_service.py](../../../../backend/apps/core/services/crypto_service.py) | Crittografia Fernet derivata da SECRET_KEY |
| `IdempotencyStore.claim_or_replay` | [idempotency_store.py](../../../../backend/apps/core/services/idempotency_store.py) | Claim atomico chiave idempotency o replay risposta precedente |
| `IdempotencyStore.mark_completed` | [idempotency_store.py](../../../../backend/apps/core/services/idempotency_store.py) | Marca richiesta completata con payload risposta |
| `record_login` / `record_logout` / `record_refresh` | [session_audit_service.py](../../../../backend/apps/core/services/session_audit_service.py) | Registra eventi sessione (LOGIN, LOGOUT, REFRESH, REVOCA) |
| `fn_list_lookup_codici` | [lookup_service.py](../../../../backend/apps/core/services/lookup_service.py) | Lookup generico tabelle codici con paginazione |
| `as_bool` / `empty_to_none` | [value_normalizer.py](../../../../backend/apps/core/services/value_normalizer.py) | Normalizzazione valori (bool, stringa vuota → None) |
| `set_request_context` / `get_request_id` / `get_client_ip` | [request_context.py](../../../../backend/apps/core/services/request_context.py) | Context vars per request_id, idempotency_key, IP client |

---

## Database Helpers (`apps/core/db/`)

| Building Block | File | Descrizione |
|---|---|---|
| `row_to_dict` | [_helpers.py](../../../../backend/apps/core/db/_helpers.py) | Converte riga cursor in dizionario |
| `rows_to_list` | [_helpers.py](../../../../backend/apps/core/db/_helpers.py) | Converte tutte le righe cursor in lista di dizionari |
| `dynamic_update` | [_helpers.py](../../../../backend/apps/core/db/_helpers.py) | UPDATE generico con field builder None-safe |
| `CoreRepository.get_user_profile` | [core_repository.py](../../../../backend/apps/core/db/core_repository.py) | Profilo utente completo via script.fn_get_user_profile |
| `SearchRepository.search_soggetti` | [search_repository.py](../../../../backend/apps/core/db/search_repository.py) | Ricerca universale soggetti full-text |
| `LookupRepository` | [lookup_repository.py](../../../../backend/apps/core/db/lookup_repository.py) | Lookup tipi soggetto, ruoli per natura, forme giuridiche, matrice indirizzi |
| `SessionAuditRepository` | [session_audit_repository.py](../../../../backend/apps/core/db/session_audit_repository.py) | Insert/list eventi sessione |
| `TokenRepository` | [token_repository.py](../../../../backend/apps/core/db/token_repository.py) | CRUD token monouso (create, find_valid, consume, invalidate) |
| `EmailRepository` | [email_repository.py](../../../../backend/apps/core/db/email_repository.py) | Risoluzione template/account, log email, gestione bozze e allegati |

---

## Middleware (`apps/core/middleware/`)

| Building Block | File | Descrizione |
|---|---|---|
| `ApiExceptionMiddleware` | [api_exception_middleware.py](../../../../backend/apps/core/middleware/api_exception_middleware.py) | Converte eccezioni in envelope errore JSON per /api/* |
| `RequestContextMiddleware` | [request_context_middleware.py](../../../../backend/apps/core/middleware/request_context_middleware.py) | Assegna request_id e idempotency_key, aggiunge header risposta |

---

## Mixin e Tipi (`apps/core/`)

| Building Block | File | Descrizione |
|---|---|---|
| `EmittenteFiscaleScopeMixin` | [mixins.py](../../../../backend/apps/core/mixins.py) | Mixin queryset: filtra per emittenti fiscali autorizzati |
| TypedDict vari | [types.py](../../../../backend/apps/core/types.py) | Definizioni tipo per AuditLog, DominioTask, EmailAccount, Token, Outbox, ecc. |
