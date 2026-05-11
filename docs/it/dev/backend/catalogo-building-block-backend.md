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
| `AdminAPIView` | [base_views.py](../../../../backend/apps/core/api/base_views.py) | Base view per endpoint admin-only (check binding `SUPER_ADMIN` via `PermissionResolver.is_super_admin`). Post multi-face auth sostituisce il vecchio check `ruolo_sistema = ADMIN`. |
| `PortaleAPIView` | [base_views.py](../../../../backend/apps/core/api/base_views.py) | Base view per `/api/portale/*` (clienti + fornitori). JWT + `PortaleBasePermission` (`ruolo_applicativo ∈ {CLIENTE_PORTALE, FORNITORE_PORTALE}`). `skip_area_check = True` implicito (scope dati applicato via RLS). |
| `ShopAPIView` | [base_views.py](../../../../backend/apps/core/api/base_views.py) | Base view per `/api/shop/*` (negozio online). JWT opzionale + `ShopBasePermission` (anonimo o `SHOP_CUSTOMER`). Le view che richiedono autenticazione (checkout, ordini) devono verificare `request.user.is_authenticated`. |
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
| `IsAdminZeroERP` | [permissions.py](../../../../backend/apps/core/api/permissions.py) | Permission check per binding `SUPER_ADMIN` (via `PermissionResolver.is_super_admin`). Nome invariato per retrocompat con `AdminAPIView`; la semantica e' passata da "ruolo_sistema=ADMIN" a "binding SUPER_ADMIN attivo". |
| `ZeroERPPermission` | [permissions.py](../../../../backend/apps/core/api/permissions.py) | Permission resolver centrale con area/action/livello. Multi-face: check `ruolo_applicativo=DISABILITATO` -> 403 immediato; poi `is_super_admin` -> bypass; altrimenti catena livello area/oggetto/azione. |
| `PortaleBasePermission` | [permissions.py](../../../../backend/apps/core/api/permissions.py) | Permission class per `/api/portale/*`. Richiede `ruolo_applicativo ∈ {CLIENTE_PORTALE, FORNITORE_PORTALE}`. Non verifica livello area (set endpoint portale ristretto). Usata da `PortaleAPIView`. |
| `ShopBasePermission` | [permissions.py](../../../../backend/apps/core/api/permissions.py) | Permission class per `/api/shop/*`. Ammette anonimo (catalogo pubblico) o `SHOP_CUSTOMER` autenticato. Altri ruoli (OPERATORE, CLIENTE_PORTALE, ...) respinti con 403. Usata da `ShopAPIView`. |
| `LoginRateThrottle` | [throttling.py](../../../../backend/apps/core/api/throttling.py) | Rate limit login (5/5min) |
| `PasswordResetRateThrottle` | [throttling.py](../../../../backend/apps/core/api/throttling.py) | Rate limit reset password (3/15min) |
| `SearchBurstRateThrottle` | [throttling.py](../../../../backend/apps/core/api/throttling.py) | Rate limit endpoint search |
| `get_idempotency_key` | [retry_policies.py](../../../../backend/apps/core/api/retry_policies.py) | Estrae Idempotency-Key dagli header |
| `apply_retry_headers` | [retry_policies.py](../../../../backend/apps/core/api/retry_policies.py) | Aggiunge header Retry-After se errore ritentabile |
| `DEFAULT_LIMIT` / `MAX_LIMIT` | [constants.py](../../../../backend/apps/core/api/constants.py) | Costanti paginazione (50 / 200) |
| `JwtAuditAuthentication` | [jwt_audit_authentication.py](../../../../backend/apps/core/api/jwt_audit_authentication.py) | **Subclass `JWTAuthentication`** che propaga **5 GUC** di sessione PG subito dopo `authenticate()` di successo: `app.jwt_user`, `app.current_user_id` (sempre), `app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id` (solo se identita attiva, altrimenti stringa vuota — fail-open documentato). Single round-trip via CTE che risolve `identita_digitali` attiva. Registrata in `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` + tutte le base view (`DomainAPIView`, `AdminAPIView`, `PortaleAPIView`, `ShopAPIView`). Setta marker `request._zeroerp_jwt_guc_set` letto da `JwtAuditMiddleware.process_response` per il reset simmetrico dei 5 GUC. Vedi guida `risorse-umane-e-accessi.md` sezione "Propagazione identita utente al database (GUC)" e `architettura-multi-face-auth.md`. |

### Pattern: lookup cross-dominio su sub-resource

Quando un sub-resource di area X (es. `/X/<id>/Y/`) deve essere usato come **lookup di selezione cross-dominio** (autocomplete da drawer di altre aree), splittare in due endpoint:

| Endpoint | Permission | Caso d'uso |
| --- | --- | --- |
| `GET /<area_X>/<id>/Y/` | `area_funzionale=X` + `model_permission` | Admin di X che gestisce il sub-resource (CRUD context) |
| `GET /<area_X>/<id>/Y/lookup/` | `skip_area_check=True` | Lookup di selezione per drawer di altre aree |

Le operazioni di scrittura (`POST`, `PATCH`, `DELETE` sul path classico) restano protette dall'area: solo la lettura "lookup" e' libera. Difese che restano: JWT obbligatorio, `is_search_endpoint=True` (throttling), eventuale scope dati lato repository.

**Esempio applicato — `catalogo.articoli.uom`:**

| Endpoint | Permission | Consumer |
| --- | --- | --- |
| `GET /catalogo/articoli/<id>/uom/` (`ApiArticoloUomList`) | `area=catalogo` + `model_permission=articolo` | `ArticoloDrawer`, `ArticoloUomDrawer` (admin catalogo) |
| `GET /catalogo/articoli/<id>/uom/lookup/` (`ApiArticoloUomLookup`) | `skip_area_check=True` | 5 consumer cross-dominio via `useArticoloUomOptions`: `PreventiviRigaForm`, `PromoArticoloDrawer`, `ContrattoRigheDrawer`, `VersioneDrawer`, `TestResolverDialog` |
| `POST /catalogo/articoli/<id>/uom/` | `area=catalogo` (METHOD_REQUIRES POST → add) | `ArticoloUomDrawer` |
| `PATCH /catalogo/articoli/<id>/uom/<uom_id>/` | `area=catalogo` | `ArticoloUomDrawer` |
| `DELETE /catalogo/articoli/<id>/uom/<uom_id>/` | `area=catalogo` | `ArticoloUomDrawer` |

**Razionale.** Forzare `area_funzionale` sul GET costringe l'operatore di un altro dominio (es. vendite) ad avere LETTURA su catalogo solo per popolare un combo: gonfia il profilo permessi e produce 403 silenti che svuotano gli autocomplete senza UX di errore (sintomo classico: "scelgo articolo, combo UoM vuota, save fallisce con E_QTA_MISSING"). Splittare e' lineare e non ha controindicazioni di sicurezza per dati non sensibili (UoM, lookup di selezione). Per casi che necessitano ulteriori restrizioni granulari, vedi `feedback_lookup_skip_area_check.md` (leve disponibili: scope dati, azione di processo dedicata, ScopePolicy). Per il pattern dei lookup top-level (non sub-resource) liberati: `ApiArticoliLookup`, `BillingAccountLookupView`, `IstanzaUtilityLookupView`, `BillingAccountLookupByIdView`, `IstanzaUtilityLookupByIdView`.

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
| `PermissionResolver.is_super_admin` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Verifica binding `SUPER_ADMIN` attivo per l'utente (bypass totale). Delega a `script.fn_is_super_admin`. Sostituisce il vecchio `get_ruolo_sistema() == "ADMIN"`. |
| `PermissionResolver.get_ruolo_applicativo` | [permissions_resolver.py](../../../../backend/apps/core/services/permissions_resolver.py) | Ritorna `ruolo_applicativo` dell'identita attiva (`OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`, `API_CLIENT`, `DISABILITATO`). GUC-first (`app.ruolo_applicativo`) con fallback query su `anagrafiche.identita_digitali`. Sostituisce il vecchio `get_ruolo_sistema`. |
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
| `BillingAccountRepository.get_istanza_utility_id` | [billing_account_repository.py](../../../../backend/apps/anagrafiche/db/billing_account_repository.py) | Risolve l'`istanza_utility_id` del BA (FK NOT NULL). Usato dai service di dominio per derivare l'istanza quando il payload specifica solo il BA (es. `crea_preventivo` post brief DB rev2). |
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

## Anagrafiche — Istanze utility (`apps/anagrafiche/`)

| Building Block | File | Descrizione |
|---|---|---|
| `IstanzeUtilityRepository.search_lookup` | [istanze_utility_repository.py](../../../../backend/apps/anagrafiche/db/istanze_utility_repository.py) | Ricerca ricca istanze (codice istanza, ragione sociale soggetto, indirizzo normalizzato) con JOIN a `soggetti`, `vw_indirizzi_dettaglio`, BA campione (LATERAL). Filtri: `utility_id` strict (post Strategia C: EXISTS su BA / IDP / clienti), `soggetto_id`, scope emittente via BA collegato (`emittenti_fiscali_billing_account`). Ordinamento per ragione sociale + codice istanza + id. Restituisce `(rows, total_count)`. |
| `IstanzeUtilityRepository.get_lookup_by_id` | [istanze_utility_repository.py](../../../../backend/apps/anagrafiche/db/istanze_utility_repository.py) | Restore singola istanza arricchita per ricostruire `_obj` dell'AutoComplete in edit. Niente scope check (id gia' noto). |
| `IstanzeUtilityRepository.exists` | [istanze_utility_repository.py](../../../../backend/apps/anagrafiche/db/istanze_utility_repository.py) | Esistenza istanza per check 404 prima di scope/lookup. |
| `IstanzeUtilityRepository.check_utility_istanza_coerenza` | [istanze_utility_repository.py](../../../../backend/apps/anagrafiche/db/istanze_utility_repository.py) | Wrapper `script.fn_check_utility_istanza_coerenza`. Pre-validazione coerenza coppia `(istanza_utility_id, utility_id)` prima dell'INSERT preventivo: errore parlante prima del trigger DB. Defense-in-depth: il trigger `trgfn_preventivi_guard_utility_istanza_coerenza` applica la stessa regola in DB. |
| `IstanzeUtilityService.search_lookup` | [istanze_utility_service.py](../../../../backend/apps/anagrafiche/services/istanze_utility_service.py) | Facade lookup istanze: valida `q >= 2 char`, cap `limit` a 50 (default 20), delega a repository. Restituisce `{results, total_count, limit}`. |
| `IstanzeUtilityService.get_lookup_by_id` | [istanze_utility_service.py](../../../../backend/apps/anagrafiche/services/istanze_utility_service.py) | Facade restore istanza per edit. Solleva `E_ANAG_NOT_FOUND` se inesistente. |

**Endpoint**:

- `GET /api/v1/anagrafiche/istanze-utility/lookup/?q=<min2>&utility_id=&soggetto_id=&limit=` — autocomplete
- `GET /api/v1/anagrafiche/istanze-utility/<id>/lookup/` — restore per edit

**Scope emittente lookup**: applicato automaticamente dalla view via `PermissionResolver.get_emittenti_sr_ids`. Un operatore vede solo le istanze con almeno un BA collegato nel suo scope EF (catena `emittenti_fiscali_billing_account`). Le istanze totalmente orfane (no BA — possibili solo in business non-utility post Strategia C, vedi brief DB rev2 §2.1) sono visibili solo ad admin globale e superuser.

**Consumer**: `PreventiviForm` (drawer prospect senza BA). Riusabile in altri flow utility-aware dove l'istanza e' un identificatore di dominio centrale (future: contratti standalone, attivita_fatturabili dirette).

---

## Anagrafiche — Valuta resolver (`apps/anagrafiche/services/`)

| Building Block | File | Descrizione |
|---|---|---|
| `resolve_valuta_default` | [valuta_resolver.py](../../../../backend/apps/anagrafiche/services/valuta_resolver.py) | BB stateless cross-dominio per risolvere `valuta_id` di default applicando la catena standard: **1)** `ba.valuta_id` (se BA presente) → **2)** EF del BA via `get_emittente_valuta(ba_id)` (catena `fn_get_emittente_fiscale_pk`) → **3)** EF dell'utente loggato via `ParameterService.get_emittente_fiscale_id_for_user(auth_user_id)` (con fallback gestore globale per admin globale) → **4)** `{}` se nessuna sorgente. Composizione di BB esistenti: `BillingAccountRepository.get_lookup_by_id` + `.get_emittente_valuta`, `ParameterService.get_emittente_fiscale_id_for_user`, `EmittentiFiscaliRepository.get_emittente`. Zero SQL nuovo. Param `ba_obj` opzionale per riusare BA gia' fetched dal caller (no double round-trip). Ritorna `{valuta_id, valuta_codice, valuta_descrizione}` o `{}`. Mapping `valuta_iso → valuta_codice` nel branch user-EF per coerenza shape (le valute standard hanno `iso_code == codice`). Consumer attuali: `vendite_form_defaults_service.fn_get_preventivo_form_defaults`. Da adottare ovunque serva un default coerente di valuta (contratti, ordini, fatture, ecc.). |

---

## Anagrafiche — Clienti (`apps/anagrafiche/`)

| Building Block | File | Descrizione |
|---|---|---|
| `ClientiRepository.check_user_can_create_ba` | [clienti_repository.py](../../../../backend/apps/anagrafiche/db/clienti_repository.py) | Wrapper `script.fn_check_user_can_create_ba`. Vedi WIP refactor operatore-emittenti Q6 (la motivazione di dominio sta nel service) |
| `ClientiService.crea_cliente` (param `auth_user_id`) | [clienti_service.py](../../../../backend/apps/anagrafiche/services/clienti_service.py) | Orchestratore creazione cliente completa (istanza + BA + cliente in transazione atomica). **Refactor operatore-emittenti**: param `auth_user_id` opzionale; se valorizzato e si crea un nuovo BA (no `billing_account_id` in payload), chiama `_guard_can_create_ba` che blocca admin globale + emittenti con `ServiceError(E_BA_ADMIN_GLOBALE_VIETATO)`. Defense-in-depth: il trigger DB `trgfn_billing_account_guard_admin_globale` e' la difesa finale |
| `ClientiInvitaPortaleView` / `ClientiInvitaShopView` / `FornitoriInvitaPortaleView` | [views_invito_portale.py](../../../../backend/apps/anagrafiche/api/views_invito_portale.py) | View admin per `POST /api/v1/anagrafiche/{clienti\|fornitori}/<id>/invita-{portale\|shop}/`. Body `{email, reinvio?}`. Delegano a `InvitoPortaleService` (fornitori solo portale; shop = B2C, non per fornitori). |

---

## Portale + Shop — Invito veste (`apps/portale/`, `apps/shop/`)

Building block per onboarding self-service vesti non-operatore
(CLIENTE_PORTALE, FORNITORE_PORTALE, SHOP_CUSTOMER). Vedi
[api_invito_portale_shop.md](../../backend/core/manual/api_invito_portale_shop.md)
per il contratto end-to-end.

| Building Block | File | Descrizione |
|---|---|---|
| `InvitoPortaleService.invia_invito_cliente / fornitore / shop_customer` | [invito_portale_service.py](../../../../backend/apps/portale/services/invito_portale_service.py) | 3 metodi pubblici simmetrici, stesso flow comune `_invia_invito_common` parametrizzato su `_VESTE_CONFIG`. Branching automatico email NUOVA → flow INVITO (set password) vs ESISTENTE → flow CROSS (one-click). Transazione atomica + email best-effort (token resta valido se SMTP fallisce). Equivalenti `reinvia_*` invalidano token precedenti. |
| `_VESTE_CONFIG` (TypedDict `_VesteConfig`) | [invito_portale_service.py](../../../../backend/apps/portale/services/invito_portale_service.py) | Single source of truth per veste: `token_invito`, `token_cross`, `template`, `link_path`, `scadenza_ore`. **Aggiungere una nuova veste = una nuova entry**, no altre modifiche al service. |
| `resolve_portale_token` / `resolve_shop_token` | [invito_portale_service.py](../../../../backend/apps/portale/services/invito_portale_service.py) | Risolvono (no consume) un token cercandolo nei tipi della veste. Il FE non deve sapere il tipo in anticipo: `_resolve_token_in(token, tipi)` itera. |
| `PortaleRepository` | [portale_repository.py](../../../../backend/apps/portale/db/portale_repository.py) | DB ops invito veste: `get_cliente_info`, `get_fornitore_info`, `find_identita_portale`, `find_auth_user_by_email`, `create_auth_user_portale`, `create_identita_portale`, `riattiva_identita`. Generico su `ruolo_applicativo` — usato anche da shop (cross-app import documentato come debito, refactor PR-D = estrarre in `IdentitaRepository`). |
| `AttivazionePortaleValidateView` / `AttivazionePortaleView` | [portale/api/views.py](../../../../backend/apps/portale/api/views.py) | Endpoint pubblici (`AllowAny`) `GET /portale/attivazione/validate/<token>/` + `POST /portale/attivazione/conferma/`. Consume token + apply password (INVITO) oppure riattiva identita (CROSS). Throttle `PasswordResetRateThrottle`. |
| `AttivazioneShopValidateView` / `AttivazioneShopView` | [shop/api/views_attivazione.py](../../../../backend/apps/shop/api/views_attivazione.py) | Simmetrici al portale, tipi token `INVITO_SHOP` / `ATTIVAZIONE_SHOP_CROSS`. Codice errore distinto `E_ATTIVAZIONE_SHOP`. Codice ~80% duplicato col portale: refactor base class rimandato a PR-D. |
| `ProfileActivateShopView` | [portale/api/views.py](../../../../backend/apps/portale/api/views.py) | `POST /portale/profile/activate-shop/` autenticato. Cross-veste self-service: cliente portale loggato aggiunge identita SHOP_CUSTOMER sullo stesso `soggetto_ruolo` (letto da GUC `app.soggetto_ruolo_id`), immediatamente attiva. Idempotente + anti-tampering (`auth_user_id` divergente → 400). Solo `CLIENTE_PORTALE` (FORNITORE blocca a 400). |

**Token tipi** in `config.token_monouso.tipo` (varchar, 4 valori
gestiti dal service): `INVITO_PORTALE`, `ATTIVAZIONE_PORTALE_CROSS`,
`INVITO_SHOP`, `ATTIVAZIONE_SHOP_CROSS`. Scadenza 72h, mutuamente
esclusivi grazie al `UNIQUE (token_hash)`.

**Codici errore** registrati in `error_policies.py`: `E_INVITO_PORTALE`,
`E_ATTIVAZIONE_PORTALE`, `E_ATTIVAZIONE_SHOP`, `E_ATTIVAZIONE_SHOP_CROSS`
(tutti HTTP 400, `show_error_banner`).

**Dipendenza DB**: template email `INVITO_SHOP` da seedare in
`config.email_template`. Proposta SQL idempotente in
[backend/scripts/db-proposals/PROPOSTA_seed_email_invito_shop.sql](../../../../backend/scripts/db-proposals/PROPOSTA_seed_email_invito_shop.sql).

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

## Multi-Face Auth — Costanti e Modelli (`apps/core/services/`, `apps/anagrafiche/`, `apps/config/`)

| Building Block | File | Descrizione |
|---|---|---|
| `RUOLO_APPLICATIVO`, `RUOLI_PORTALE`, `RUOLI_SHOP` | [auth_constants.py](../../../../backend/apps/core/services/auth_constants.py) | Enum dei ruoli applicativi (`OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`, `API_CLIENT`, `DISABILITATO`) + subset per i namespace portale/shop. Fonte unica lato Python; equivalente DB: `config.ruolo_applicativo`. |
| `TIPO_PROFILO_ACCESSO`, `SUPER_ADMIN_PROFILO_CODICE` | [auth_constants.py](../../../../backend/apps/core/services/auth_constants.py) | Enum tipo profilo (`REPARTO`, `PORTALE`, `AD_HOC`, `SUPER_ADMIN`) + codice riservato del profilo di bypass totale (seed id 9100). |
| `IdentitaDigitale` | [anagrafiche/models.py](../../../../backend/apps/anagrafiche/models.py) | Model ORM (`managed=False`) del bridge generico `soggetti_ruoli <-> auth_user`. Campi stateful: `ruolo_applicativo`, `attivo`, `valido_dal/al`, `deve_cambiare_password`, `invito_inviato_at`, `tentativi_falliti`, `bloccato_fino_a`, `totp_obbligatorio`, `storicizza`. Sostituisce `RisorseUmaneAuthUser` (ora vista in transizione). |
| `ProfiloAccesso`, `ProfiloAccessoArea`, `ProfiloAccessoAzione`, `ProfiloAccessoBinding` | [config/models.py](../../../../backend/apps/config/models.py) | Model ORM dei profili accesso generalizzati (tipo REPARTO / PORTALE / AD_HOC / SUPER_ADMIN). I bindings supportano xor 3-vie: reparto, identita' singola, ruolo applicativo. Sostituiscono `ProfiloRepartoArea/Azione` (kept per lettura legacy). |
| `ScopePolicy`, `IdentitaScopeBinding` | [config/models.py](../../../../backend/apps/config/models.py) | Model ORM per le policy di scope dati (EF_WHITELIST, BA_OWNERSHIP, FORNITORE_OWNERSHIP). La funzione SQL di check e' indicata in `funzione_db`. Bindings opzionali con `parametri JSONB`. |
| `RisorseUmaneAuthUser` | [anagrafiche/models.py](../../../../backend/apps/anagrafiche/models.py) | **DEPRECATO** post-cutover §4.6.H.2: ora read-only (vista su `identita_digitali`). I writer passano a `IdentitaDigitale`. |

---

## Middleware (`apps/core/middleware/`)

| Building Block | File | Descrizione |
|---|---|---|
| `ApiExceptionMiddleware` | [api_exception_middleware.py](../../../../backend/apps/core/middleware/api_exception_middleware.py) | Converte eccezioni in envelope errore JSON per /api/* |
| `RequestContextMiddleware` | [request_context_middleware.py](../../../../backend/apps/core/middleware/request_context_middleware.py) | Assegna request_id e idempotency_key, aggiunge header risposta |
| `JwtAuditMiddleware` | [jwt_audit_middleware.py](../../../../backend/apps/core/middleware/jwt_audit_middleware.py) | Pre-load cache permessi Redis L2, rifiuto early `ruolo_applicativo=DISABILITATO` con 403 (via `PermissionResolver.get_ruolo_applicativo`), **reset simmetrico** dei 5 GUC settati da `JwtAuditAuthentication` (`app.jwt_user`, `app.current_user_id`, `app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id`). Il setting delle GUC NON avviene piu' qui dallo sprint BE-2.0ter. |

---

## Vendite — Pricing v5 (`apps/vendite/`)

| Building Block | File | Descrizione |
|---|---|---|
| `PricingRepository.resolve_prezzo_listino_v2` | [pricing_repository.py](../../../../backend/apps/vendite/db/pricing_repository.py) | Wrapper `vendite.fn_resolve_prezzo_listino_v2(uuid,bigint,date,bigint,integer,bigint,integer)`. Resolver a 3 stadi (promo → contratto → categoria). Ritorna 1 riga con prezzo + metadati snapshot. |
| `PricingRepository.resolve_prezzo_composito` | [pricing_repository.py](../../../../backend/apps/vendite/db/pricing_repository.py) | Wrapper `vendite.fn_resolve_prezzo_composito(...)`. BoM ibrido A/B1/B2: ritorna N righe (CASO A) o 1 riga (B1/B2) secondo esposizione in fattura dei componenti. |
| `PricingService.resolve_prezzo` | [pricing_service.py](../../../../backend/apps/vendite/services/pricing_service.py) | Facade `fn_resolve_prezzo_listino_v2`: valida input (UUID, int > 0, date), delega al repo, traduce `DatabaseError` P0001 in `ServiceError` con codice preservato quando MESSAGE matcha un marker noto (`E_PREZZO_LISTINO_NON_TROVATO`, `E_CATEGORIA_LISTINO_NON_MAPPATA`, `E_PREZZO_LISTINO_RIGA_NON_TROVATA`, `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`). Fallback `E_VENDITE_PRICING_FAILED`. `emittente_soggetto_ruolo_id` deve essere gia' risolto dal caller (derivato dal JWT). |
| `PricingService.resolve_prezzo_composito` | [pricing_service.py](../../../../backend/apps/vendite/services/pricing_service.py) | Facade `fn_resolve_prezzo_composito`: stessa policy di validazione e traduzione errori. Caller tipico: pipeline di espansione attivita' commessa (F2-BE-12). |
| `PromoArticoliRepository` | [promo_articoli_repository.py](../../../../backend/apps/vendite/db/promo_articoli_repository.py) | CRUD su `vendite.promo_articoli` (STADIO 0 resolver). Lista arricchita con JOIN articolo/uom. |
| `PromoArticoliService` | [promo_articoli_service.py](../../../../backend/apps/vendite/services/promo_articoli_service.py) | Service admin promo. `PayloadValidator` + `map_integrity_error`. Ammette `tipo_variazione=PREZZO_FISSO` (vietato in listini e matrice categoria). Coerenza tipo/valore anticipata lato service. |
| `CatalogoRepository.ARTICOLI_CREATE_COLUMNS.listino_tipologia_id` | [catalogo_repository.py](../../../../backend/apps/catalogo/db/catalogo_repository.py) | Colonna smallint nullable (FK `config.listini_tipologie`). Ereditata da `ARTICOLI_UPDATE_COLUMNS` e proiettata in `ARTICOLI_DETAIL_COLUMNS` insieme ai decode `tipologia_listino_codice`/`tipologia_listino_descrizione` via `vw_articoli_dettaglio`. Coerenza articolo↔riga listino imposta dal trigger DB `trgfn_listini_righe_guard_tipologia` (§7.2 v5). |
| `CatalogoRepository.list_articoli(listino_tipologia_id=)` | [catalogo_repository.py](../../../../backend/apps/catalogo/db/catalogo_repository.py) | Filtro opzionale sulla lista articoli. Esposto via query param `listino_tipologia_id` su `GET /api/v1/catalogo/articoli/`. |
| `CatalogoBomRepository.COMPONENTE_WRITE_COLUMNS.esposto_in_fattura` | [catalogo_bom_repository.py](../../../../backend/apps/catalogo/db/catalogo_bom_repository.py) | Flag bool (DDL default `false`) che decide la modalita' A/B1/B2 del `fn_resolve_prezzo_composito` (§8 v5): se almeno un componente ha `esposto_in_fattura=true`, il resolver emette N righe (una per componente) e la pipeline di creazione attivita' espande in `commesse_attivita`. |
| `PricingResolveView` | [views_pricing.py](../../../../backend/apps/vendite/api/views_pricing.py) | Endpoint `POST /api/v1/vendite/pricing/resolve/`. Esposizione REST di `PricingService.resolve_prezzo` per UI di debug, smoke test e supporto operativo. `emittente_soggetto_ruolo_id` derivato automaticamente dal JWT operatore (override opzionale nel payload per diagnostica). Area `vendite` livello `LETTURA`. Nessun side-effect: solo lettura. |
| `vendite_lookups_service.fn_list_*` | [vendite_lookups_service.py](../../../../backend/apps/vendite/services/vendite_lookups_service.py) | **Fase 2 refactor frontend vendite.** Lookup statici per enum di dominio: `fn_list_tipi_variazione_contratto` (PERCENTUALE/VALORE_FISSO), `fn_list_tipi_variazione_promo` (+ PREZZO_FISSO), `fn_list_ambiti_contratto` (COMMODITY/COMMERCIO), `fn_list_modalita_pricing_contratto` (A/B/C). Single source of truth: rispetta le whitelist gia' presenti nei service di dominio (`contratti_service._TIPI_VARIAZIONE`, `_AMBITI_VALIDI`; `promo_articoli_service._TIPI_VARIAZIONE`). Niente DB. Modello: `catalogo_service.fn_list_uom_rounding_modes`. |
| `Api*Lookup` (4 view) | [views_lookups.py](../../../../backend/apps/vendite/api/views_lookups.py) | Endpoint `GET /api/v1/vendite/lookup/{tipi-variazione-contratto,tipi-variazione-promo,ambiti-contratto,modalita-pricing-contratto}/`. Area `vendite` LETTURA, JWT obbligatorio. Sostituiscono i magic string `'PERCENTUALE'`/`'COMMODITY'`/`'A'` cablati nel FE. |
| `vendite_form_defaults_service.fn_get_*` | [vendite_form_defaults_service.py](../../../../backend/apps/vendite/services/vendite_form_defaults_service.py) | **Fase 2.B3-B5 refactor frontend vendite.** 5 funzioni read-only per defaults BA-aware (`fn_get_contratto_form_defaults`, `fn_get_preventivo_form_defaults`) e contestuali a listino/versione (`fn_get_versione_new_defaults`, `fn_get_versione_clone_defaults`, `fn_get_versione_close_defaults`). Combinano `BillingAccountRepository.get_lookup_by_id` (categoria_cliente, utility) + query diretta `anagrafiche.clienti` su tripletta `(istanza_utility_id, soggetto_ruolo_id, utility_id)` per termine_pagamento_id/iva_id/modalita_pagamento_id + fallback emittente per `valuta_id` (catena `fn_get_emittente_fiscale_pk`) + `ParameterService.get_defaults` per i lead_gg/suffisso. Errori `E_VENDITE_NOT_FOUND` (404 BA/listino/versione mancante) e `E_VENDITE_VALIDATION` (input non intero positivo). |
| `Api*FormDefaults` (5 view) | [views_form_defaults.py](../../../../backend/apps/vendite/api/views_form_defaults.py) | Endpoint `GET /api/v1/vendite/{contratti,preventivi}/form-defaults/?billing_account_id=...` + `/listini/<id>/versioni/{form-defaults,<ver>/clone-defaults,<ver>/close-defaults}/`. Area `vendite` LETTURA, JWT obbligatorio. Path versioni montate prima di `versioni/` lista per non collidere con il pattern `<int:>`. Single source of truth lato BE per defaults FE: sostituiscono derivazioni cablate nei drawer (`new Date()`, `addDaysToToday(N)`, suffisso `-clone`, lookup categoria dal BA). Vedi [api_vendite_form_defaults.md](../../backend/vendite/manual/api_vendite_form_defaults.md). |
| `approvazioni_prezzo_service.crea_richiesta_approvazione` | [approvazioni_prezzo_service.py](../../../../backend/apps/vendite/services/approvazioni_prezzo_service.py) | **L3 Sprint E / sviluppo-listini-v5 §14.6.** Orchestra creazione pratica APPROVAZIONE_PREZZO quando `gestisci_riga`/`aggiorna_riga` vengono chiamate con `richiesta_approvazione=true` e il prezzo viola L2. Pattern: crea pratica BOZZA→APERTA via `pratiche_service.crea_pratica`, lookup cache modulo-level di `tipo_prestazione_id`/`priorita_id`, invio email best-effort al recipient configurato via parameter `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`. La FK `riga_preventivo_id` viene aggiunta al meta pratica via `link_riga_a_pratica` post-`create_riga`. |
| `approvazioni_prezzo_service.approva` / `rifiuta` | [approvazioni_prezzo_service.py](../../../../backend/apps/vendite/services/approvazioni_prezzo_service.py) | Workflow esito L3: verifica permesso azione `approva_prezzo_override` (seed `config.azioni_processo` id 10), UPDATE riga `stato_approvazione_prezzo='APPROVED'/'REJECTED'` (ENUM nativo `config.stato_approvazione_prezzo`), transizione pratica APERTA→CHIUSA, nota INTERNA con esito + nota/motivazione opzionale. Idempotente: rifiuta riga non PENDING con `E_APPROVAZIONE_PREZZO_NON_AMMESSA`. Defense-in-depth: permesso check PRIMA del lookup riga (no leak info su esistenza). |
| `approvazioni_prezzo_service.lista_coda` | [approvazioni_prezzo_service.py](../../../../backend/apps/vendite/services/approvazioni_prezzo_service.py) | Coda paginata pratiche tipo APPROVAZIONE_PREZZO in stato APERTA. Scope emittente derivato dall'utente via `PermissionResolver.get_emittente_for_user` (richiede emittente assegnato; admin globale solleva `E_APPROVAZIONE_PREZZO_NON_AMMESSA`). Usata da `GET /vendite/approvazioni-prezzo/` (UI ApprovazioniPrezzoListView). |
| `BoMComponentExpander` | [commesse_source_handlers.py](../../../../backend/apps/vendite/services/commesse_source_handlers.py) | **F2-BE-12 / sviluppo-listini-v5 §14.4.** Single-point per l'espansione BoM v5 nella pipeline commesse. Una `PushableRow` di articolo composito (CASO A: almeno un componente esposto in fattura) viene espansa in N `PushableRow` (una per componente obbligatorio attivo). CASO B (1 riga padre): pass-through. Pre-filtri: `articolo_id`/`uom_id`/`utility_id` None → pass-through. Detect `is_composito` via callable iniettabile (default: query lean su `catalogo.articoli`). Cache per-istanza su `is_composito` (1 lookup/articolo) e su risultato resolver (chiave `(articolo, BA, utility, data, emittente)` → 1 round-trip per chiave nel ciclo `_process_rows`). Costruisce ogni componente con: `articolo_id`/`uom_id`/`prezzo_snapshot` dal resolver, `quantita = padre × coeff_qta` no rounding (DEC-3), `segment_key` suffix `#CMP:{componente_id}` (DEC-2), `meta` arricchito con `esposto_in_fattura`+`componente_di`+`coeff_qta` (DEC-6), tutti gli altri campi (`tipo_doc_fiscale_id`, `valuta_id`, `billing_account_id`, `utility_id`, `sorgente_uid`, `emittente_soggetto_ruolo_id`, `competenza_*`, `fatturazione_immediata`) ereditati dal padre (DEC-5). Iniettabile in `BaseSourceHandler(repo, bom_expander=...)`; default applicato a tutti i 5 handler (preventivi/ordini/contratti/ddt). `HandlerConsumi` mantiene il proprio override `_expand_rows` (fan-out consumi ortogonale alla BoM). **Dipendenza DB**: richiede `coeff_qta` nel return di `fn_resolve_prezzo_composito` (DB-3 in lavorazione team DB). |

**Consumer previsti** — `PricingService.resolve_prezzo` e' il building block centrale per **qualsiasi calcolo prezzo** in domini downstream. Al posto di duplicare logica (lookup listino / matrice / contratto) chiamare sempre il service:

| Consumer | Stato | Dove chiamarlo |
|---|---|---|
| `commesse_attivita` (snapshot audit) | **Done** (F2-BE-11) | Il DB `fn_upsert_commessa_attivita` popola gia' le 8 colonne snapshot |
| `preventivi_service.calcola_prezzo_riga` | **Da integrare** | Al momento della creazione/modifica riga preventivo, sostituire lookup manuale con `PricingService.resolve_prezzo` |
| `ordini_vendita` (riga ordine) | **Da integrare** | Stesso pattern preventivi |
| `pipeline fatturazione compositi` (F2-BE-12) | **BE done 22-04** | `BoMComponentExpander` integrato in `BaseSourceHandler._expand_rows` per i 5 handler; attesa DB-3 (`coeff_qta` nel return resolver) per esecuzione reale. Vedi sviluppo-listini-v5 §14.4 |
| Endpoint diagnostico `/pricing/resolve/` | **Done** | Vedi `PricingResolveView` |

Regola pratica: **mai** leggere direttamente `listini_righe.prezzo` o `categorie_clienti_listini` in un service di dominio. Sempre passare per `PricingService`: garantisce i 3 stadi del resolver, la traduzione errori uniforme e lo snapshot dei metadati (origine, listino, contratto, promo, categoria).

---

## Preventivi vendita (`apps/vendite/`)

| Building Block | File | Descrizione |
|---|---|---|
| `PreventiviRepository` | [preventivi_repository.py](../../../../backend/apps/vendite/db/preventivi_repository.py) | Accesso DB preventivi: CRUD testata, righe, indirizzi, scope emittente, stato fatturazione, pratiche collegate |
| `PreventiviRepository.resolve_contesto_pratica` | [preventivi_repository.py](../../../../backend/apps/vendite/db/preventivi_repository.py) | Risolve emittente_fiscale (default), soggetto_id, soggetto_ruolo_id dal BA del preventivo |
| `preventivi_service.*` | [preventivi_service.py](../../../../backend/apps/vendite/services/preventivi_service.py) | Facade preventivi: list, get, crea, aggiorna, cambia_stato, crea_revisione, righe, indirizzi, componenti BoM CASO A (list_componenti_riga, update_componente, delete_componente), push_commessa, genera_pratica (via BB `pratiche_service.crea_pratica`) |
| `PreventiviRepository` — Componenti BoM CASO A | [preventivi_repository.py](../../../../backend/apps/vendite/db/preventivi_repository.py) | **Refactor componenti 2026-05-11**. Metodi su `vendite.preventivi_righe_componenti`: `init_componenti_riga(riga_id, emittente_sr_id, data)` wrapper su `fn_preventivo_riga_componenti_init` (idempotente: no-op se gia' presenti o articolo non composito CASO A); `list_componenti_riga(riga_id)` con JOIN articolo/uom/iva, filtro `attivo=TRUE`, ORDER BY ordine NULLS LAST + id tiebreaker; `get_componente(id)` lookup singolo arricchito; `update_componente(id, **kwargs)` con whitelist `_COMPONENTE_UPDATE_ALLOWED` (12 campi, esclude struttura immutabile `componente_id`/`articolo_componente_id`/`coeff_qta_snapshot`/`riga_preventivo_id`/`quantita`); `delete_componente(id)` soft delete; `purge_componenti_riga(riga_id)` hard delete tutti i componenti (per re-init service, distinto dal pattern soft `delete_*` del file). Trigger DB ricalcola `prezzo_unitario` padre come SUM(componenti × coeff_qta_snapshot). Brief: [brief-db-preventivi-righe-componenti-override.md](../work-in-progress/brief-db-preventivi-righe-componenti-override.md), piano: [refactor-componenti.md](../work-in-progress/refactor-componenti.md). |
| `_resolve_emittente_sr_id_or_raise` / `_resolve_emittente_sr_id_safe` | [preventivi_service.py](../../../../backend/apps/vendite/services/preventivi_service.py) | Helper privati per estrarre `emittente_soggetto_ruolo_id` dall'utente loggato via `PermissionResolver.get_emittenti_sr_ids`. Variante `_or_raise` solleva `E_PREV_VALIDAZIONE` (usata da `suggerisci_prezzo_riga` dove l'emittente e' obbligatorio); variante `_safe` ritorna `None` per admin globale o utente inesistente (usata da `gestisci_riga` per il flusso init componenti CASO A — admin globale non deve essere bloccato sulla create di righe non composite). |
| `PreventivoListRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict riga lista preventivi con JOIN stato/cliente |
| `PreventivoDetailRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict dettaglio preventivo con tutte le decodifiche |
| `PreventivoRigaRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict riga preventivo con articolo/UoM/IVA |
| `PreventivoRigaComponenteRow` | [types.py](../../../../backend/apps/vendite/types.py) | **Refactor componenti 2026-05-11**. TypedDict componente CASO A: `componente_id` (UUID articolo componente, NB: NON `articolo_id` che e' del padre), `articolo_componente_id` (UUID riga BoM snapshot), `coeff_qta_snapshot`, `quantita` (= coeff × qta padre, ricalcolata da trigger DB), `prezzo_unitario` (override ammesso L1), `origine_prezzo` (5 valori: PROMO/CONTRATTO_OVERRIDE/CONTRATTO_LISTINO/CATEGORIA/MANUALE — niente LISTINO), `prezzo_resolver_context` JSONB (audit override + error context), `stato_approvazione_prezzo` + `pratica_approvazione_prezzo_id` (L3). |
| `PreventivoStatoFatturazioneRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict stato fatturazione downstream (commessa/AF/fatturato) |
| `PreventivoPraticaRow` | [types.py](../../../../backend/apps/vendite/types.py) | TypedDict pratica collegata via pratiche_sorgenti |

---

## Documenti — Motore documentale parametrico (`apps/documenti/`)

Foundation v1 del motore documentale (Decisioni 25/30/72-76 di `sviluppo-documenti.md`). Read-only: lista/dettaglio template + versioni. CRUD admin + render in PR successive.

| Building Block | File | Descrizione |
|---|---|---|
| `DocumentStorage` | [storage/base.py](../../../../backend/apps/documenti/services/storage/base.py) | Interfaccia astratta storage documentale: `write(key, content) -> storage_uri`, `read/delete/exists(storage_uri)`. `delete` best-effort (no raise se assente, evento `STORAGE_ORPHAN` per cleanup post-fail commit). |
| `FilesystemDocumentStorage` | [storage/filesystem.py](../../../../backend/apps/documenti/services/storage/filesystem.py) | Provider filesystem v1. Persiste sotto `DOCUMENTI_STORAGE_ROOT` + `documenti_storage_prefix`. Guard path traversal (`..`, backslash, leading slash). storage_uri formato `filesystem:<prefix>/<key>`. |
| `build_filesystem_storage` | [storage/filesystem.py](../../../../backend/apps/documenti/services/storage/filesystem.py) | Factory esposta separatamente dal selector per consentire ai test di iniettare un root temporaneo. |
| `get_storage` | [storage/selector.py](../../../../backend/apps/documenti/services/storage/selector.py) | Selector che istanzia il provider attivo leggendo `documenti_storage_provider` da `config.parameters`. Provider whitelisted v1: `filesystem`. Cambio provider richiede solo upsert parametro (no restart). |
| `DocumentContextBuilder` | [context_builders/base.py](../../../../backend/apps/documenti/services/context_builders/base.py) | Interfaccia astratta builder di contesto. Le impl concrete vivono nei domini sorgente (es. `PreventivoDocumentContextBuilder` in `apps/vendite/`). `CODE` matcha 1:1 con `template_documenti.context_builder_code`. |
| `register_builder` / `get_builder` / `registered_codes` | [context_builders/registry.py](../../../../backend/apps/documenti/services/context_builders/registry.py) | Registry centrale dict `CODE -> Builder`. Registrazione via import esplicito (no auto-discovery via signal). `get_builder` solleva `E_DOCUMENTI_VALIDATION` se la chiave non e' whitelisted (Decisione 18+74). Stesso pattern di `pipeline_task_registry_impl` di vendite. |
| `DocumentiRepository.list_templates` | [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py) | Lista paginata template con scope emittente (whitelist `bigint[]` via `ANY(%s)`), filtri (`attivo`, `tipo_documento_output_id`, `sorgente_tipo_id`, `emittente_fiscale_id`), search ILIKE su 3 colonne, ORDER BY whitelisted con `t.id` come tiebreaker (paginazione deterministica). |
| `DocumentiRepository.get_template` | [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py) | Dettaglio template + scope emittente: ritorna `None` se inesistente o fuori scope (il service traduce in 404 unificato senza leak). |
| `DocumentiRepository.list_versioni` / `get_versione` | [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py) | Versioni di un template ordinate per `versione DESC`. `get_versione` binda `template_documento_id` (defense-in-depth: id versione orfano di altro template via path errato -> nessun match). |
| `TemplateService` | [template_service.py](../../../../backend/apps/documenti/services/template_service.py) | Facade lettura template + versioni. Risolve scope emittente automatico via `PermissionResolver.get_emittenti_ids` (admin globale -> None, operatore -> lista, anon/non-auth -> `[]`). Valida stato versione contro whitelist `{BOZZA,PUBBLICATA,OBSOLETA}`, guard id positivo prima del DB. |
| `TemplateService.download_asset` / `ApiAssetFileDownload` | [template_service.py](../../../../backend/apps/documenti/services/template_service.py) / [views.py](../../../../backend/apps/documenti/api/views.py) | Download binario asset admin `GET /api/v1/documenti/asset/<id>/file/`. Riusa `get_asset` per id positivo + scope emittente (404 unificato no leak), ricostruisce `storage_uri` via `DocumentStorage.build_storage_uri(storage_key)` e ritorna `HttpResponse` attachment senza envelope JSON. GET puro: nessun evento/audit per non introdurre side effect sulle letture di configurazione. |
| `TemplateAdminService.create_template` | [template_admin_service.py](../../../../backend/apps/documenti/services/template_admin_service.py) | **Tranche E.** Create testata template con `PayloadValidator` + scope emittente. Mappa IntegrityError DB su codici applicativi parlanti via `map_integrity_error` (UNIQUE codice/codice_interno per emittente+sorgente, partial-unique `is_default` per output+sorgente+emittente, FK su tipo_output/sorgente/emittente). Defaults espliciti: `is_default=False`, `attivo=True`. |
| `TemplateAdminService.update_template` | [template_admin_service.py](../../../../backend/apps/documenti/services/template_admin_service.py) | **Tranche E.** PATCH testata template. Pre-verifica visibilita' tramite `TemplateService.get_template` (404 unificato no leak). Rifiuta campi immutabili (`tipo_documento_output_id`, `sorgente_tipo_id`, `emittente_fiscale_id`) PRIMA di altre validazioni. Empty payload post-validation -> errore parlante. |
| `DocumentiRepository.create_template` / `update_template` | [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py) | **Tranche E.** INSERT/UPDATE su `template_documenti` con whitelist colonne `TEMPLATE_CREATE_COLUMNS` / `TEMPLATE_UPDATE_COLUMNS` (immutabili escluse dalla update). Defense-in-depth: chiavi extra fuori whitelist sono silently ignorate. |
| `TemplateVersioniAdminService` | [template_versioni_admin_service.py](../../../../backend/apps/documenti/services/template_versioni_admin_service.py) | **Tranche F.** Ciclo vita versione template: 5 metodi `create_versione`, `update_versione`, `delete_versione`, `clone_versione`, `pubblica_versione`. Numero versione calcolato come `MAX+1` per template (race protetta da unique vincolo DB). Validazione service-side dello stato (BOZZA modificabile/eliminabile, PUBBLICATA immutabile) con trigger DB A1/A2 come guardrail finale. Pubblicazione atomica `BOZZA -> PUBBLICATA` con `valido_dal NOT NULL` guard, EXCLUDE GiST DB blocca overlap con altre `PUBBLICATA` attive (errore parlante via mapper, no demote automatico del precedente). Mapping IntegrityError per tutti i 8 vincoli DDL (unique versione, GiST overlap, 7 CHECK su versione/stato/formato/orientamento/page_format/margini/titolo/valido_dal_pubblicata). |
| `DocumentiRepository.next_versione_num` | [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py) | **Tranche F.** `SELECT COALESCE(MAX(versione), 0) + 1` per template. Race window protetta dal vincolo unique `(template_documento_id, versione)`. |
| `DocumentiRepository.create_versione` / `update_versione` / `delete_versione` / `pubblica_versione` | [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py) | **Tranche F.** INSERT/UPDATE/DELETE su `template_documenti_versioni` con whitelist `VERSIONE_CREATE_COLUMNS` / `VERSIONE_UPDATE_COLUMNS`. `pubblica_versione` e' UPDATE atomic con filtro `WHERE stato='BOZZA'` (idempotenza per design: una seconda chiamata su versione gia' pubblicata torna `False` senza errore DB). Trigger DB A1 (protect_pubblicata) e A2 (block_delete) sono i guardrail finali per UPDATE/DELETE su versioni protette. |
| TypedDict template/versione | [types.py](../../../../backend/apps/documenti/types.py) | `TemplateDocumentoListRow`/`DetailRow` (no html/css/markdown nella list, presente nel detail), `TemplateVersioneListRow`/`DetailRow` (proiezione leggera vs payload pesante). |
| `render_service.render_pdf` | [render_service.py](../../../../backend/apps/documenti/services/render_service.py) | **Tranche I.** Funzione pura `render_pdf(template_versione, context) -> bytes`. Whitelist applicativa engine (v1: `WEASYPRINT`, case-insensitive normalizzato uppercase, Decisione 3 — l'engine resta estensibile via lookup `documenti.render_engine_documento`). Render Jinja2 con `StrictUndefined` (variabile mancante nel context -> errore parlante invece di silent empty), `autoescape=False` (template fidati creati da admin). WeasyPrint `HTML(string=...)+CSS(string=...)` (lazy import per non risolvere Pango/Cairo a meno che il render non sia effettivamente invocato). Tutti gli errori interni (Jinja syntax/undefined, WeasyPrint parse/font/IO) mappati a `E_DOCUMENTI_RENDER_FAILED` con `detail` diagnostico. |
| `DocumentGenerationService.genera_documento` | [document_generation_service.py](../../../../backend/apps/documenti/services/document_generation_service.py) | **Tranche I.** Orchestratore generazione persistita. Pipeline: auth+scope -> resolve template (override `template_documento_id` -> reader; default `is_default=true` -> `repo.find_template_applicabile`; coerenza emittente/sorgente_tipo) -> resolve versione PUBBLICATA attiva (`validita @> CURRENT_DATE`) -> resolve context_builder via registry -> `builder.build_context()` -> `render_pdf(...)` PRIMA del DB (Decisione 32: render fail = niente record orfano) -> hashes audit (`context_hash`/`template_hash`/`pdf_hash` sha256, JSON canonical sort_keys per context) -> `nome_file` via `str.format(file_name_pattern, **context)` (KeyError -> `E_DOCUMENTI_RENDER_FAILED` parlante) -> lookup `tipi_file_documento` per codice `PDF_FINALE` (no ID hardcoded) -> `next_progressivo_sorgente` (race protetta da unique DDL) -> `transaction.atomic`: INSERT 3 record (testata + file `is_principale=true` + evento `GENERATO/OK` SENZA `tx_id` esplicito Decisione 76) + `storage.write` (atomic) -> commit. Cleanup STORAGE_ORPHAN best-effort se commit fail post-write (Decisione 72): `storage.delete` + log warning, no raise per non mascherare l'eccezione del commit. |
| `DocumentiRepository` (Tranche I) | [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py) | **Tranche I.** 7 nuovi metodi: `find_template_applicabile` (filtro `is_default=true`+`attivo`+scope `ANY(%s)`), `get_versione_pubblicata_attiva` (`stato='PUBBLICATA'`+`attivo=true`+`validita @> %s::date`+`versione DESC LIMIT 1`), `next_progressivo_sorgente` (branching `IS NULL` vs `=` su `sorgente_riga` per coerenza con unique `NULLS NOT DISTINCT`), `create_documento_generato` (RETURNING id+uid), `create_documento_generato_file`, `emit_evento_documento` (whitelist `EVENTO_DOCUMENTO_CREATE_COLUMNS` esclude `tx_id` per design), `get_tipo_file_documento_by_codice` (lookup PDF_FINALE). Whitelist colonne `DOCUMENTO_GENERATO_*` per defense-in-depth contro chiavi extra. |
| `PreventivoDocumentContextBuilder` | [apps/vendite/services/preventivo_document_context_builder.py](../../../../backend/apps/vendite/services/preventivo_document_context_builder.py) | **Tranche J.** Context builder concreto per sorgente PREVENTIVO. `CODE = "PREVENTIVO"`, `build_context(sorgente_id, *, auth_user_id, locale)` legge `PreventiviRepository` (testata + righe + riepilogo IVA + indirizzi) e ritorna dict a 6 sezioni stabili (`preventivo`, `cliente`, `indirizzi`, `righe`, `riepilogo_iva`, `_meta`). `_meta` contiene solo dati stabili a parita' di chiamata (locale, auth_user_id, context_code, context_version) — niente timestamp/random per garantire `context_hash` deterministico. Auto-register al boot via `VenditeConfig.ready()` -> import esplicito del modulo (no auto-discovery via signal Django). Confine: non applica scope/permessi — responsabilita' del caller (Tranche K view con permessi `vendite_*`). |
| `apps.documenti.services._scope` | [_scope.py](../../../../backend/apps/documenti/services/_scope.py) | **Tranche I+J review.** Helper di dominio condivisi per auth + scope `emittente_fiscale`. 4 funzioni standalone: `guard_user_authenticated`, `resolve_emittente_scope`, `guard_emittente_in_scope`, `guard_emittente_in_scope_for_user` (composizione end-to-end). Estratto da `template_admin_service`, `template_asset_admin_service` e `document_generation_service` che duplicavano la stessa logica. L'orchestrator generazione usa le 3 utility separate per cachare lo scope (un solo round-trip a `PermissionResolver.get_emittenti_ids` per intera invocazione). |
| `PayloadValidator.guard_non_empty_string` | [payload_helpers.py](../../../../backend/apps/core/services/payload_helpers.py) | **Tranche I+J review.** Guard scalare su stringa non vuota (post-strip). Speculare a `guard_positive_int`: opera su valori scalari (kwarg, parametro di firma) anziche' estrarre da payload. Usato dall'orchestrator generazione per `sorgente_uid` non vuoto pre-DB. |
| `DocumentGenerationService.anteprima_documento` / `list_documenti_per_sorgente` / `download_documento` | [document_generation_service.py](../../../../backend/apps/documenti/services/document_generation_service.py) | **Tranche K.** 3 comandi pubblici aggiuntivi: `anteprima_documento` (pipeline render senza persist - Decisione 30); `list_documenti_per_sorgente` (lista paginata building block riusabile per qualsiasi dominio sorgente); `download_documento` (`storage.read` + emit evento `SCARICATO` in tx separata best-effort - Decisione 31, audit non blocca il file). |
| `DocumentiRepository` (Tranche K) | [documenti_repository.py](../../../../backend/apps/documenti/db/documenti_repository.py) | **Tranche K.** 4 nuovi metodi per gli endpoint generazione/lista/download: `get_sorgente_tipo_id_by_codice` (lookup `config.sorgenti` per codice, no ID hardcoded); `list_documenti_per_sorgente` (filtri sorgente con branching `IS NULL` vs `=` su `sorgente_riga`, scope `ANY(%s)`, paginazione cap 200, `ORDER BY generato_at DESC, id DESC`); `get_documento_generato` (404 unificato via scope opzionale, no leak); `get_documento_generato_file_principale` (filtro `is_principale=true` con `LIMIT 1`). |
| `PreventiviRepository.get_for_documento_generation` | [preventivi_repository.py](../../../../backend/apps/vendite/db/preventivi_repository.py) | **Tranche K.** Proiezione minima `{id, uid, emittente_fiscale_id}` per il motore documentale: `emittente_fiscale_id` e' colonna nativa NOT NULL del DDL preventivi (multi-face auth Tranche A), niente JOIN su anagrafiche/billing_account. |
| `DocumentStorage.build_storage_uri` | [storage/base.py](../../../../backend/apps/documenti/services/storage/base.py) | **Tranche K.** Aggiunto all'interfaccia astratta + impl filesystem: il caller post-fact (download Tranche K) ha solo la `storage_key` letta dal DB e ricostruisce lo storage_uri stabile prima di passare a `read/delete/exists`. Risolve la disconnessione fra `storage_uri` ritornato da `write` (memoria runtime) e `storage_key` salvato su DB. |
| API documenti per preventivi | [apps/vendite/api/preventivi_documenti_views.py](../../../../backend/apps/vendite/api/preventivi_documenti_views.py) | **Tranche K.** 4 view sotto `/api/v1/vendite/preventivi/<id>/documenti/`: `POST genera/`, `POST anteprima/` (binary inline), `GET` lista paginata, `GET <doc_id>/file/` (binary attachment + emit `SCARICATO`). `area_funzionale="vendite"` con permission default lettura preventivi (Decisione 75: permessi del dominio sorgente). Path nidificato consente difesa-in-profondita' contro tampering URL. |

**Codici errore registrati** (vedi `apps/core/services/error_policies.py`):

| Codice | HTTP | Sorgente |
|---|---|---|
| `E_DOCUMENTI_VALIDATION` | 400 | service (id non valido, stato fuori whitelist) + storage (key/storage_uri malformato) |
| `E_DOCUMENTI_NOT_FOUND` | 404 | service (template/versione fuori scope o inesistente) |
| `E_DOCUMENTI_DENIED` | 403 | (futuro: comandi versione su stato non ammesso) |
| `E_DOCUMENTI_RENDER_FAILED` | 500 | render service (engine non whitelisted, Jinja syntax/undefined, WeasyPrint exception/empty, file_name_pattern var mancante) |
| `E_DOCUMENTI_STORAGE_FAILED` | 500 | storage (file mancante in read, IO error in delete, provider mismatch) |
| `E_EVENTO_DOCUMENTO_DELETE_VIETATA` | 409 | trigger DB `trgfn_documenti_generati_eventi_a10_block_delete_dlt` |
| `E_EVENTO_DOCUMENTO_UPDATE_VIETATA` | 409 | trigger DB `trgfn_documenti_generati_eventi_a10_block_update_upd` |

**Endpoint** (vedi [api_documenti_templates.md](../../backend/documenti/manual/api_documenti_templates.md) per il contratto completo):

- `GET /api/v1/documenti/templates/` — lista paginata
- `GET /api/v1/documenti/templates/<id>/` — dettaglio
- `GET /api/v1/documenti/templates/<id>/versioni/` — versioni
- `GET /api/v1/documenti/templates/<id>/versioni/<vid>/` — dettaglio versione (incluso payload html/css/markdown)

Tutti su `DomainAPIView` con `area_funzionale = "documenti"`. CRUD admin (PR successive) usera' `post_permission = "documenti_template_manage"` / `"documenti_asset_manage"` (Decisione 75).

---

## UI — Personalizzazioni liste (`apps/ui/`)

Strato di presentazione (schema DB `ui`) per il componente Vue
`<ListaConfigurabile>`. Meta-API trasversale: tutte le view usano
`DomainAPIView` con `skip_area_check=True` (lo schema `ui` non e' in
`config.aree_funzionali` per design — la presentazione e' ortogonale
ai domini funzionali).

| Building Block | File | Descrizione |
|---|---|---|
| `UiRepository.resolve_lista_config` | [ui_repository.py](../../../../backend/apps/ui/db/ui_repository.py) | Wrapper 1:1 di `ui.fn_resolve_lista_config(VARCHAR, INTEGER, BIGINT)`. Cascata preferenza/preset di ruolo (priorita ASC) /preset emittente/preset sistema/catalogo grezzo + merge nuove colonne + filtro autorizzativo. Restituisce JSONB `{colonne[], ordinamento, filtri, pagina_dimensione, colonne_nuove}`. Veste corrente letta dalla GUC `app.ruolo_applicativo` (post DB-4 landed 2026-05-07). |
| `UiRepository.list_colonne_by_codice` | [ui_repository.py](../../../../backend/apps/ui/db/ui_repository.py) | Catalogo colonne arricchito (etichetta, gruppo, tipo_dato, formato, ecc.) con JOIN `lista_definizione` -> `lista_colonna`. Single round-trip per la modale di personalizzazione. Filtra `attivo=TRUE`; il filtro permessi e' applicato a layer service riusando la fn DB. |
| `UiRepository.get_preferenza` | [ui_repository.py](../../../../backend/apps/ui/db/ui_repository.py) | Lettura preferenza utente per (auth_user, lista_id) con metadati (`preset_base_id`, `preset_base_data_update`) per badge DEF-2. |
| `UiRepository.upsert_preferenza` | [ui_repository.py](../../../../backend/apps/ui/db/ui_repository.py) | UPSERT preferenza utente (`ON CONFLICT (auth_user_id, lista_id) DO UPDATE`). Snapshot `preset_base_data_update` calcolato dal service via `get_preset_base_snapshot`. |
| `UiRepository.delete_preferenza` | [ui_repository.py](../../../../backend/apps/ui/db/ui_repository.py) | Elimina preferenza utente. Ritorna `bool` (idempotente: `False` se non esisteva). |
| `UiRepository.get_preset_base_snapshot` | [ui_repository.py](../../../../backend/apps/ui/db/ui_repository.py) | Snapshot `(preset_id, data_update)` del preset di base risolto per l'utente. Replica la cascata Step 2b/c/d della fn DB con espressione `_GUC_VESTE_EXPR` GUC-aware. **Drift risk documentato**: se `fn_resolve_lista_config` cambia, va aggiornata anche questa fn. Soluzione futura: brief team DB per esporre `preset_base` nel JSONB della fn. |
| `UiService.get_lista_config` | [ui_service.py](../../../../backend/apps/ui/services/ui_service.py) | Facade `resolve_lista_config`: deriva `emittente_fiscale_id` 1:1 via `PermissionResolver.get_emittente_for_user` (admin globale -> `None`), traduce `DatabaseError` P0001 in `ServiceError` con marker `E_UI_LISTA_NON_TROVATA`, fallback `E_UI_GENERIC_FAILED`. |
| `UiService.get_catalogo` | [ui_service.py](../../../../backend/apps/ui/services/ui_service.py) | Catalogo per la modale: riusa `get_lista_config()` per filtrare BLOCCATE (single source of truth permessi), arricchisce con metadati ricchi via `list_colonne_by_codice`. 2 round-trip totali, error handling centralizzato. |
| `ListaPreferenzaService.upsert` | [lista_preferenza_service.py](../../../../backend/apps/ui/services/lista_preferenza_service.py) | UPSERT preferenza con `PayloadValidator` (whitelist anti-injection: `{colonne, ordinamento, filtri, pagina_dimensione}`; per colonna: `{codice, ordine, larghezza, visibile, fissata}`). `pagina_dimensione` cap a `MAX_LIMIT=200`. Snapshot `preset_base_id` + `preset_base_data_update` ritornati al chiamante per UX badge. |
| `ListaPreferenzaService.delete` | [lista_preferenza_service.py](../../../../backend/apps/ui/services/lista_preferenza_service.py) | DELETE idempotente. Solleva `E_UI_LISTA_NON_TROVATA` se la lista stessa non esiste (protezione anti-tampering URL). |
| `ApiListaConfigView` / `ApiListaCatalogoView` / `ApiListaPreferenzaView` | [views.py](../../../../backend/apps/ui/api/views.py) | Le 3 view DRF per i 4 endpoint. Tutte `skip_area_check=True`. PUT preferenza usa `handle_post_json` con `require_idempotency_key=True`. |

**Endpoint** (vedi [api_ui_liste.md](../../backend/ui/manual/api_ui_liste.md) per il contratto completo):

- `GET    /api/v1/ui/liste/<codice>/config/` — risolve configurazione effettiva
- `GET    /api/v1/ui/liste/<codice>/catalogo/` — catalogo per modale (filtrato per permessi)
- `PUT    /api/v1/ui/liste/<codice>/preferenza/` — UPSERT preferenza (Idempotency-Key obbligatoria)
- `DELETE /api/v1/ui/liste/<codice>/preferenza/` — DELETE idempotente

**Codici errore** registrati in `apps/core/services/error_policies.py`:

| Codice | HTTP | Sorgente |
|---|---|---|
| `E_UI_LISTA_NON_TROVATA` | 404 | service + fn DB (`fn_log_and_raise_error`) |
| `E_UI_VISTA_SQL_NON_TROVATA` | 400 | trigger DB B1 (admin only) |
| `E_UI_CAMPO_SORGENTE_NON_TROVATO` | 400 | trigger DB B2 (admin only) |
| `E_UI_PREFERENZA_VALIDAZIONE` | 400 | service (whitelist payload) |
| `E_UI_GENERIC_FAILED` | 400 | service (fallback DatabaseError ignote) |

---

## Mixin e Tipi (`apps/core/`)

| Building Block | File | Descrizione |
|---|---|---|
| `EmittenteFiscaleScopeMixin` | [mixins.py](../../../../backend/apps/core/mixins.py) | Mixin queryset: filtra per emittenti fiscali autorizzati |
| TypedDict vari | [types.py](../../../../backend/apps/core/types.py) | Definizioni tipo per AuditLog, DominioTask, EmailAccount, Token, Outbox, ecc. |
