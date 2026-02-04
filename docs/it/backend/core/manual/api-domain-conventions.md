# API domain conventions (Core Django)

## Scopo
Definire uno standard unico per costruire future API di dominio.

## Contesto
Per ridurre duplicazioni tra app dominio usare helper core:
- `apps/core/api/endpoint_helpers.py`
- `apps/core/api/request_parsers.py`
- `apps/core/api/error_responses.py`
- Template di partenza: `apps/core/api/examples/domain_post_example.py`

## Input
- `Request` DRF con body JSON
- handler dominio che riceve `payload: dict`

## Output
- `JsonResponse` con contratto uniforme:
  - successo: `{ "data": ..., "meta": { "request_id": ... } }`
  - errore: `{ "error": ..., "meta": { "request_id": ... } }`

## Regole
- Versioning URL: endpoint canonici sotto `/api/v1/...`; le route non versionate restano solo come compatibilita` temporanea.
- Autenticazione: endpoint `/api/v1/*` protetti con JWT Bearer.
- Emissione token:
  - `POST /api/v1/auth/token/`
  - `POST /api/v1/auth/token/refresh/`
- Endpoint POST JSON: usare `handle_post_json(request, handler=...)`.
- Per endpoint write critici, impostare `require_idempotency_key=True`.
- Nel handler dominio: validare campi specifici e invocare service.
- Errori applicativi: sempre via `ErrorManager`/`ServiceError`.
- Niente parser JSON/date duplicati nelle singole app dominio.
- Evitare `try/except Exception` generici nella view: il fallback globale su errori non gestiti e` nel middleware `apps/core/middleware/api_exception_middleware.py`.
- Se serve disattivare fallback middleware (debug mirato), usare `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED=0`.
- Context middleware assegna `request_id` (header `X-Request-ID`) e propaga `Idempotency-Key` se presente.
- Rate limiting: non e` ancora applicato a livello applicativo; baseline consigliata su Nginx/API gateway per endpoint write/retryable.
- Fase 2 deprecazione legacy:
  - route legacy abilitate/disabilitate via `DJANGO_API_LEGACY_ROUTES_ENABLED` (default `1`)
  - header deprecazione su legacy via `DJANGO_API_LEGACY_DEPRECATION_HEADERS_ENABLED` (default `1`)
  - sunset configurabile via `DJANGO_API_LEGACY_SUNSET_HEADER`

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
- Durata `access_token`: 60 minuti.
- Durata `refresh_token`: 1 giorno.
- Dopo modifiche a `SIMPLE_JWT` in settings, riavviare Gunicorn per applicare i nuovi valori.

## Checklist operativa (nuove API dominio)
1. **View**: creare endpoint in `apps/<dominio>/api/views.py` con `handle_post_json(...)`.
2. **Routing**: registrare path in `apps/<dominio>/api/urls.py` e includere in `zeroerp_backend/urls.py`.
3. **Service**: spostare logica business in `apps/<dominio>/services/` (view sottile).
4. **Errori**: usare `ErrorManager.require(...)` / `ErrorManager.raise_error(...)` nel service.
5. **Test**: aggiungere test API (status/envelope) e test service (regole dominio).
6. **Doc**: aggiornare manuale area dominio e indice con endpoint, input/output e regole.
