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
| `DomainAPIView` | [base_views.py](../../../../backend/apps/core/api/base_views.py) | Base view per endpoint dominio con JWT + ZeroERPPermission. Supporta `model_permission = ("app_label", "model_name")` per attivare livello oggetto (v2 permessi). |
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
| `JwtAuditAuthentication` | [jwt_audit_authentication.py](../../../../backend/apps/core/api/jwt_audit_authentication.py) | **Subclass `JWTAuthentication`** che propaga `app.jwt_user` + `app.current_user_id` come GUC PG session-scoped subito dopo `authenticate()` di successo. E' il punto del flusso DRF in cui l'identita JWT e' gia risolta E il view body non e ancora partito → i trigger DB di audit/scope vedono le GUC durante le scritture. Registrata in `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` + `DomainAPIView` + `AdminAPIView`. Setta marker `request._zeroerp_jwt_guc_set` letto da `JwtAuditMiddleware.process_response` per il reset simmetrico. Vedi guida `risorse-umane-e-accessi.md` sezione "Propagazione identita utente al database (GUC)" |

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
| `PermissionResolver.get_livello_oggetto` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Livello accesso per singolo model (override oggetto con fallback area). Usato da `ZeroERPPermission` quando la view dichiara `model_permission` o ha queryset ORM. |
| `PermissionResolver.check_azione` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Verifica se azione processo è consentita |
| `PermissionResolver.get_emittenti_ids` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Lista PK `emittenti_fiscali.id` autorizzati per l'utente (`None` = vede tutto). **Usare solo per lookup diretti su emittenti_fiscali.** |
| `PermissionResolver.get_emittenti_sr_ids` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Lista `soggetto_ruolo_id` degli emittenti autorizzati via `fn_get_emittenti_scope_sr_ids` (`None` = vede tutto). **Usare per query che filtrano su `emittente_soggetto_ruolo_id`** (search universale, lista clienti, efba). |
| `PermissionResolver.get_emittente_for_user` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | **Refactor operatore-emittenti 1-a-1**: ritorna l'**unico** `emittenti_fiscali.id` (PK reale) assegnato all'utente via `script.fn_resolve_emittente_for_user`. `None` per admin globale o istanza "0 emittenti". Pattern `_cached`. **Diverso da `get_emittenti_ids`**: quello e' lista whitelist, questo e' single PK 1-a-1. **Vedi anche** `ParameterService.get_emittente_fiscale_id_for_user` (semantica simile ma fa fallback al gestore globale, ritorna sempre un id se sistema configurato) |
| `load_user_cache` / `invalidate_user` / `invalidate_all` | [permissions_cache.py](../../../../backend/apps/core/services/permissions_cache.py) | Cache permessi Redis L2 (load, invalidate utente/reparto/tutti) |
| `encrypt` / `decrypt` | [crypto_service.py](../../../../backend/apps/core/services/crypto_service.py) | Crittografia Fernet derivata da SECRET_KEY |
| `IdempotencyStore.claim_or_replay` | [idempotency_store.py](../../../../backend/apps/core/services/idempotency_store.py) | Claim atomico chiave idempotency o replay risposta precedente |
| `IdempotencyStore.mark_completed` | [idempotency_store.py](../../../../backend/apps/core/services/idempotency_store.py) | Marca richiesta completata con payload risposta |
| `record_login` / `record_logout` / `record_refresh` | [session_audit_service.py](../../../../backend/apps/core/services/session_audit_service.py) | Registra eventi sessione (LOGIN, LOGOUT, REFRESH, REVOCA) |
| `fn_list_lookup_codici` | [lookup_service.py](../../../../backend/apps/core/services/lookup_service.py) | Lookup generico tabelle codici con paginazione |
| `as_bool` / `empty_to_none` | [value_normalizer.py](../../../../backend/apps/core/services/value_normalizer.py) | Normalizzazione valori (bool, stringa vuota → None) |
| `set_request_context` / `get_request_id` / `get_client_ip` | [request_context.py](../../../../backend/apps/core/services/request_context.py) | Context vars per request_id, idempotency_key, IP client |
| `validate_and_extract_token` | [auth_helpers.py](../../../../backend/apps/core/services/auth_helpers.py) | Valida token monouso senza consumo, estrae auth_user_id e meta |
| `apply_new_password` | [auth_helpers.py](../../../../backend/apps/core/services/auth_helpers.py) | Set password + reset flag + blacklist JWT in transazione atomica |
| `ComplexityValidator` | [password_validators.py](../../../../backend/apps/core/password_validators.py) | Validator password: maiuscola + minuscola + numero + carattere speciale |
| `ParameterService.get_parameter` | [parameter_service.py](../../../../backend/apps/core/services/parameter_service.py) | Risolve parametro singolo con override (user → group → emittente → default). Lancia `E_PARAMETER_NOT_FOUND` se assente |
| `ParameterService.get_parameter_int` | [parameter_service.py](../../../../backend/apps/core/services/parameter_service.py) | Risolve parametro e converte a intero. Lancia `E_PARAMETER_VALIDATION` se non numerico |
| `ParameterService.get_defaults` | [parameter_service.py](../../../../backend/apps/core/services/parameter_service.py) | Risolve N parametri in un colpo. Restituisce `{code: valore}`, codici assenti esclusi silenziosamente |
| `ParameterService.list_parameters_for_user` | [parameter_service.py](../../../../backend/apps/core/services/parameter_service.py) | Lista completa parametri con valori a ogni livello di scope e valore risolto finale |
| `ParameterService.upsert_user_override` | [parameter_service.py](../../../../backend/apps/core/services/parameter_service.py) | Crea/aggiorna override personale utente per un parametro (UPSERT) |
| `ParameterService.delete_user_override` | [parameter_service.py](../../../../backend/apps/core/services/parameter_service.py) | Rimuove override personale utente con verifica ownership |
| `ParameterService.get_emittente_fiscale_id_for_user` | [parameter_service.py](../../../../backend/apps/core/services/parameter_service.py) | Risolve emittente_fiscale_id dal bridge HR utente |
| `PayloadValidator` | [payload_helpers.py](../../../../backend/apps/core/services/payload_helpers.py) | Validator parametrizzato per `validation_code` di dominio. Metodi: `validate_allowed_keys`, `guard_positive_int`, `require_string`, `require_positive_int`, `optional_positive_int`, `optional_smallint`, `optional_bool`, `optional_meta`. Rigore tipi (bool != int, int != float, stringhe numeriche ammesse solo per id), nessun default implicito. Usato dai service CRUD admin (categorie_clienti, utilities_tipi_ruolo, tipi_ruolo_tipi_indirizzo) |
| `map_integrity_error` | [payload_helpers.py](../../../../backend/apps/core/services/payload_helpers.py) | Traduce `IntegrityError` in `ServiceError` via mappe `unique_constraints`/`fk_constraints` (frammento nome vincolo DB -> `(error_code, message)`). Match case-insensitive. Fallback configurabile con `fallback_code`/`fallback_message` |

---

## Anagrafiche — Billing Account (`apps/anagrafiche/`)

| Building Block | File | Descrizione |
|---|---|---|
| `BillingAccountRepository.search_lookup` | [billing_account_repository.py](../../../../backend/apps/anagrafiche/db/billing_account_repository.py) | Ricerca ricca BA (codice, ragione sociale, id fiscale, PDP) con JOIN a `istanze_utilities/pdp`, `vw_soggetti_ruoli_dettaglio`, `config.utilities`. Filtri: `utility_id`, validita' temporale (`valid_at`), scope emittente via `emittenti_fiscali_billing_account`. Ordinamento alfabetico. Restituisce `(rows, total_count)` |
| `BillingAccountRepository.get_lookup_by_id` | [billing_account_repository.py](../../../../backend/apps/anagrafiche/db/billing_account_repository.py) | Restore singolo BA arricchito per ricostruire `_obj` dell'AutoComplete in modalita' edit senza round-trip |
| `BillingAccountRepository.get_emittente_fiscale_id` | [billing_account_repository.py](../../../../backend/apps/anagrafiche/db/billing_account_repository.py) | Wrapper su `anagrafiche.fn_get_emittente_fiscale_pk`: ritorna la **PK reale** `emittenti_fiscali.id` (catena specifico → default globale, filtro `ef.attivo`). Usato per check di scope emittente su singolo BA. **Importante**: ritorna PK, non `soggetto_ruolo_id` (vedi memoria progetto `feedback_emittente_pk_vs_soggetto_ruolo`) |
| `BillingAccountRepository.exists` | [billing_account_repository.py](../../../../backend/apps/anagrafiche/db/billing_account_repository.py) | Esistenza BA per check 404 prima di scope/lookup. Usato dal flusso `list_utilities_for_ba` per non leakare 403 su id non esistenti |
| `BillingAccountService.search_lookup` | [billing_account_service.py](../../../../backend/apps/anagrafiche/services/billing_account_service.py) | Facade lookup BA: valida `q >= 2 char`, cap `limit` a 50 (default 20), delega a repository. Restituisce `{results, total_count, limit}` per gestione UI "affina la ricerca" |
| `BillingAccountService.get_lookup_by_id` | [billing_account_service.py](../../../../backend/apps/anagrafiche/services/billing_account_service.py) | Facade restore BA per edit. Solleva `E_ANAG_NOT_FOUND` se inesistente |
| `BillingAccountService.list_utilities_for_ba` | [billing_account_service.py](../../../../backend/apps/anagrafiche/services/billing_account_service.py) | Lista utility "guidate da emittente" per un BA (refactor operatore-emittenti, sez. 3 del WIP). Whitelist `ruolo ∈ {CL, FO, GE}`. Scope check applicativo confronta `user_emittente_id` con l'emittente del BA (bypass per superuser e admin globale `user_emittente_id is None`). Solleva `E_ANAG_NOT_FOUND`/`E_PERMESSO_NEGATO`. Delega lookup riga a `LookupRepository.list_utilities_per_billing_account`. Restituisce `{results: [...]}` |

**Endpoint**:
- `GET /api/v1/anagrafiche/billing-account/lookup/?q=<min2>&utility_id=&solo_validi=&valid_at=&limit=` — autocomplete
- `GET /api/v1/anagrafiche/billing-account/<id>/lookup/` — restore per edit
- `GET /api/v1/anagrafiche/billing-account/<id>/utilities/?ruolo=CL` — utility BA-driven (refactor operatore-emittenti)

**Scope emittente lookup**: applicato automaticamente dalla view via `PermissionResolver.get_emittenti_sr_ids` (ritorna `soggetto_ruolo_id`). Un operatore vede solo i BA mappati al suo emittente fiscale + quelli del gestore globale (`is_default=true` in `emittenti_fiscali_billing_account`).

**Scope emittente per `list_utilities_for_ba`**: usa il pattern 1-a-1 del refactor operatore-emittenti (`PermissionResolver.get_emittente_for_user` → PK reale, vedi sotto). Semantica diversa da `get_emittenti_sr_ids`: il primo ritorna l'unico EF assegnato all'utente (o `None` per admin globale), il secondo ritorna la lista `soggetto_ruolo_id` filtrata per scope.

---

## Anagrafiche — Clienti (`apps/anagrafiche/`)

| Building Block | File | Descrizione |
|---|---|---|
| `ClientiRepository.check_user_can_create_ba` | [clienti_repository.py](../../../../backend/apps/anagrafiche/db/clienti_repository.py) | Wrapper `script.fn_check_user_can_create_ba`. Vedi WIP refactor operatore-emittenti Q6 (la motivazione di dominio sta nel service) |
| `ClientiService.crea_cliente` (param `auth_user_id`) | [clienti_service.py](../../../../backend/apps/anagrafiche/services/clienti_service.py) | Orchestratore creazione cliente completa (istanza + BA + cliente in transazione atomica). **Refactor operatore-emittenti**: param `auth_user_id` opzionale; se valorizzato e si crea un nuovo BA (no `billing_account_id` in payload), chiama `_guard_can_create_ba` che blocca admin globale + emittenti con `ServiceError(E_BA_ADMIN_GLOBALE_VIETATO)`. Defense-in-depth: il trigger DB `trgfn_billing_account_guard_admin_globale` e' la difesa finale |

---

## Database Helpers (`apps/core/db/`)

| Building Block | File | Descrizione |
|---|---|---|
| `row_to_dict` | [_helpers.py](../../../../backend/apps/core/db/_helpers.py) | Converte riga cursor in dizionario |
| `rows_to_list` | [_helpers.py](../../../../backend/apps/core/db/_helpers.py) | Converte tutte le righe cursor in lista di dizionari |
| `dynamic_update` | [_helpers.py](../../../../backend/apps/core/db/_helpers.py) | UPDATE generico con field builder None-safe |
| `CoreRepository.get_user_profile` | [core_repository.py](../../../../backend/apps/core/db/core_repository.py) | Profilo utente completo via script.fn_get_user_profile |
| `SearchRepository.search_soggetti` | [search_repository.py](../../../../backend/apps/core/db/search_repository.py) | Ricerca universale soggetti full-text |
| `LookupRepository` | [lookup_repository.py](../../../../backend/apps/core/db/lookup_repository.py) | Lookup tipi soggetto, ruoli per natura, forme giuridiche, matrice indirizzi, utility per ruolo (strict da `config.utilities_tipi_ruolo`), **matrice utility per entita'** (`list_entity_utility_matrix`: LEFT JOIN matrice ruolo + override entita', pattern slot/override generico cross-dominio con whitelist statica tabelle ammesse) |
| `LookupRepository.list_utilities_per_billing_account` | [lookup_repository.py](../../../../backend/apps/core/db/lookup_repository.py) | **Refactor operatore-emittenti**: utility "guidate da emittente" per un BA. Wrapper su `anagrafiche.fn_lookup_utilities_per_ba(ba_id, ruolo_codice_soggetto)`. Politica ibrida: utility ammesse per ruolo soggetto BA ∩ utility ammesse per ruolo EF dell'emittente associato, decorate con `is_personalizzata_per_ef` + parametri override (soglie, arrotondamento) quando esistono per la coppia (emittente, utility). Le utility ammesse-non-personalizzate restano visibili con default sistema |
| `LookupRepository.list_conti_contabili` | [lookup_repository.py](../../../../backend/apps/core/db/lookup_repository.py) | Lookup dedicato conti contabili con filtro `tipo` (A=Acquisto, V=Vendita). Espone `tipo_conto` che il lookup generico non ritornerebbe. Whitelist del parametro per sicurezza. Usato da `LookupContiContabiliView` (endpoint `GET /api/v1/core/lookup/conti-contabili/?tipo=A` o `?tipo=V`). |
| `SessionAuditRepository` | [session_audit_repository.py](../../../../backend/apps/core/db/session_audit_repository.py) | Insert/list eventi sessione |
| `TokenRepository` | [token_repository.py](../../../../backend/apps/core/db/token_repository.py) | CRUD token monouso (create, find_valid, consume, invalidate) |
| `EmailRepository` | [email_repository.py](../../../../backend/apps/core/db/email_repository.py) | Risoluzione template/account, log email, gestione bozze e allegati |
| `ParameterRepository.get_parameter` | [parameter_repository.py](../../../../backend/apps/core/db/parameter_repository.py) | Risolve parametro singolo via `script.fn_get_parameter_full` con override user/group/emittente |
| `ParameterRepository.get_parameters` | [parameter_repository.py](../../../../backend/apps/core/db/parameter_repository.py) | Risolve N parametri (max 20) in una sessione DB. Restituisce `{code: valore}` |
| `ParameterRepository.list_for_user` | [parameter_repository.py](../../../../backend/apps/core/db/parameter_repository.py) | Lista parametri con valori per livello via `script.fn_list_parameters_for_user` |
| `ParameterRepository.upsert_user_override` | [parameter_repository.py](../../../../backend/apps/core/db/parameter_repository.py) | UPSERT override personale utente su `config.parameter_overrides` |
| `ParameterRepository.delete_user_override` | [parameter_repository.py](../../../../backend/apps/core/db/parameter_repository.py) | DELETE override con check ownership `django_user_id` |
| `ParameterRepository.get_emittente_fiscale_id_for_user` | [parameter_repository.py](../../../../backend/apps/core/db/parameter_repository.py) | Risolve emittente_fiscale_id da bridge HR (risorse_umane_auth_user) |

---

## Middleware (`apps/core/middleware/`)

| Building Block | File | Descrizione |
|---|---|---|
| `ApiExceptionMiddleware` | [api_exception_middleware.py](../../../../backend/apps/core/middleware/api_exception_middleware.py) | Converte eccezioni in envelope errore JSON per /api/* |
| `RequestContextMiddleware` | [request_context_middleware.py](../../../../backend/apps/core/middleware/request_context_middleware.py) | Assegna request_id e idempotency_key, aggiunge header risposta |
| `JwtAuditMiddleware` | [jwt_audit_middleware.py](../../../../backend/apps/core/middleware/jwt_audit_middleware.py) | Pre-load cache permessi Redis L2, rifiuto early `DISABILITATO` con 403, **reset simmetrico** delle GUC `app.jwt_user`/`app.current_user_id` settate da `JwtAuditAuthentication` (vedi sotto). Il setting delle GUC NON avviene piu' qui dallo sprint BE-2.0ter |

---

## Preventivi vendita (`apps/vendite/`)

| Building Block | File | Descrizione |
|---|---|---|
| `PreventiviRepository` | [preventivi_repository.py](../../../../backend/apps/vendite/db/preventivi_repository.py) | Accesso DB preventivi: CRUD testata, righe, indirizzi, scope emittente, stato fatturazione, pratiche collegate |
| `PreventiviRepository.resolve_contesto_pratica` | [preventivi_repository.py](../../../../backend/apps/vendite/db/preventivi_repository.py) | Risolve emittente_fiscale (default), soggetto_id, soggetto_ruolo_id dal BA del preventivo |
| `preventivi_service.*` | [preventivi_service.py](../../../../backend/apps/vendite/services/preventivi_service.py) | Facade preventivi: list, get, crea, aggiorna, cambia_stato, crea_revisione, righe, indirizzi, push_commessa, genera_pratica (via BB `pratiche_service.crea_pratica`) |
| `PreventivoListRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict riga lista preventivi con JOIN stato/cliente |
| `PreventivoDetailRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict dettaglio preventivo con tutte le decodifiche |
| `PreventivoRigaRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict riga preventivo con articolo/UoM/IVA |
| `PreventivoStatoFatturazioneRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict stato fatturazione downstream (commessa/AF/fatturato) |
| `PreventivoPraticaRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict pratica collegata via pratiche_sorgenti |

---

## Mixin e Tipi (`apps/core/`)

| Building Block | File | Descrizione |
|---|---|---|
| `EmittenteFiscaleScopeMixin` | [mixins.py](../../../../backend/apps/core/mixins.py) | Mixin queryset: filtra per emittenti fiscali autorizzati |
| TypedDict vari | [types.py](../../../../backend/apps/core/types.py) | Definizioni tipo per AuditLog, DominioTask, EmailAccount, Token, Outbox, ecc. |
