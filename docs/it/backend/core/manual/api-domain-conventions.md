# API domain conventions (Core Django)

## Scopo
Definire uno standard unico per costruire future API di dominio.

## Contesto
Per ridurre duplicazioni tra app dominio usare helper core:
- `apps/core/api/endpoint_helpers.py`
- `apps/core/api/request_parsers.py`
- `apps/core/api/error_responses.py`
- Template di partenza: `apps/core/api/examples/domain_post_example.py`
- Esempio search (throttling + min length): `SearchUniversaleView` in `apps/core/api/search_view.py` (l'esempio `domain_search_example.py` è stato rimosso il 2026-10-21)

## Input
- `Request` DRF con body JSON
- handler dominio che riceve `payload: dict`

## Output
- `JsonResponse` con contratto uniforme:
  - successo: `{ "data": ..., "meta": { "request_id": ... } }`
  - errore: `{ "error": ..., "meta": { "request_id": ... } }`

## Regole
- Versioning URL: tutti gli endpoint sono sotto `/api/v1/...` (fuori da `/api/v1/` restano solo `health`, `/api/schema/` e `/api/docs/`).
- Autenticazione: endpoint `/api/v1/*` protetti con JWT Bearer.
- Emissione token:
  - `POST /api/v1/admin/token/` + `POST /api/v1/admin/token/refresh/` (operatori interni)
  - `POST /api/v1/portale/token/` + `POST /api/v1/portale/token/refresh/` (vesti portale)
  - `POST /api/v1/shop/token/` + `POST /api/v1/shop/token/refresh/` (veste shop)
- Endpoint POST JSON: usare `handle_post_json(request, handler=...)`.
- Per endpoint write critici, impostare `require_idempotency_key=True`.
- Nel handler dominio: validare campi specifici e invocare service.
- Errori applicativi: sempre via `ErrorManager`/`ServiceError`.
- Niente parser JSON/date duplicati nelle singole app dominio.
- Evitare `try/except Exception` generici nella view: il fallback globale su errori non gestiti e` nel middleware `apps/core/middleware/api_exception_middleware.py`.
- Se serve disattivare fallback middleware (debug mirato), usare `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED=0`.
- Context middleware assegna `request_id` (header `X-Request-ID`) e propaga `Idempotency-Key` se presente.
- Rate limiting applicativo (`apps/core/api/throttling.py`): `LoginRateThrottle` (5 ogni 5 minuti per IP) sui login, `PasswordResetRateThrottle` (3 ogni 15 minuti per IP) su reset password e attivazioni, `SearchBurstRateThrottle` sulle ricerche (sotto). Per gli altri endpoint write/retryable la baseline resta su Nginx/API gateway.
- Paginazione/ricerca: seguire la policy `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md`;
  parametri, tetti e soglia di ricerca stanno in `docs/it/dev/api.md` §«Paginazione» e
  §«Ricerca e throttling» (non si ricopiano qui).
  - Throttling search: DRF `SearchBurstRateThrottle` attivo su view con `is_search_endpoint = True`.

## Dipendenze DB
- Nessuna diretta (layer API)

## Note di migrazione
- Vendite usa gia` questo pattern su `run_lotto_pipeline`.
- Le nuove API (acquisti/anagrafiche/...) devono partire da questo standard.
- Per endpoint write usare la checklist operativa: `api_write_checklist.md`.
- OpenAPI/Swagger:
  - schema: `GET /api/schema/`
  - UI: `GET /api/docs/`

## Promemoria JWT (ambiente test/dev)
- Durata `access_token`: 10 minuti (dal 2026-09-28); il frontend lo tiene solo in memoria e lo rinnova in silenzio.
- Durata `refresh_token`: 1 giorno; viaggia solo nel cookie HttpOnly `zeroerp_refresh`, mai nel corpo (vedi [api_multi_veste_token.md](api_multi_veste_token.md#cookie-di-refresh)).
- Dopo modifiche a `SIMPLE_JWT` in settings, riavviare Gunicorn per applicare i nuovi valori.

## Checklist operativa (nuove API dominio)
1. **View**: creare endpoint in `apps/<dominio>/api/views.py` con `handle_post_json(...)`.
2. **Routing**: registrare path in `apps/<dominio>/api/urls.py` e includere in `zeroerp_backend/urls.py`.
3. **Service**: spostare logica business in `apps/<dominio>/services/` (view sottile).
4. **Errori**: usare `ErrorManager.require(...)` / `ErrorManager.raise_error(...)` nel service.
5. **Test**: aggiungere test API (status/envelope) e test service (regole dominio).
6. **Doc**: aggiornare manuale area dominio e indice con endpoint, input/output e regole.
7. **Liste/Search**: applicare policy paginazione/ricerca e usare gli helper core (`pagina_da_query` in `payload_validators.py`, `search_validators.py`).
