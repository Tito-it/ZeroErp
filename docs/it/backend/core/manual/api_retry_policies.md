# API retry policies (Core Django)

## Scopo
Uniformare gestione idempotency key e semantica retry lato API.

## Contesto
Regole implementate in:
- `apps/core/api/retry_policies.py`
- `apps/core/api/endpoint_helpers.py`

## Input
- Header `Idempotency-Key` (o `X-Idempotency-Key`).
- Errore API tradotto (`ApiError.retryable`).

## Output
- Key normalizzata (o `None` se non valida).
- Header `Retry-After` per errori ritentabili.

## Regole
- `Idempotency-Key` valida se:
  - non vuota dopo trim
  - lunghezza <= 128
- Se `retryable=True`, viene aggiunto `Retry-After` (default 3s, env `DJANGO_API_RETRY_AFTER_SECONDS`).
- Endpoint write critici devono richiedere la key (`require_idempotency_key=True`).
- In strong mode la key governa claim/replay su tabella tecnica DB.

## Dipendenze DB
- `dbops.idempotency_keys` (solo strong mode).

## Note di migrazione
- Le policy retry non vanno duplicate nei domini.
- La validazione key deve restare centralizzata.
