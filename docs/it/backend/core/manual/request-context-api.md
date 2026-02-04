# Request context API (Core Django)

## Scopo
Assegnare metadati di correlazione request (`request_id`) e idempotenza (`idempotency_key`) in modo uniforme per tutte le API.

## Contesto
Componenti:
- `apps/core/middleware/request_context_middleware.py`
- `apps/core/services/request_context.py`

## Input
- Header opzionali:
  - `X-Request-ID`
  - `Idempotency-Key` / `X-Idempotency-Key`

## Output
- Header risposta:
  - `X-Request-ID`
  - `X-Idempotency-Key` (se presente in request)
- Meta envelope API:
  - `meta.request_id`
  - `meta.idempotency_key` (se presente)

## Regole
- Se `X-Request-ID` manca, viene generato UUID.
- Idempotency key viene propagata per tracing (policy retry/write).

## Dipendenze DB
- Nessuna

## Note di migrazione
- Introdotto per migliorare tracing/debug cross-layer senza impattare i service dominio.
