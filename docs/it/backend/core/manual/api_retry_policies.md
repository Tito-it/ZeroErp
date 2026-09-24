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
- Una key oltre 128 caratteri, o vuota, viene trattata come **assente**.
- Endpoint write critici devono richiedere la key (`require_idempotency_key=True`):
  senza key → `E_IDEMPOTENCY_KEY_REQUIRED` (400).
- In strong mode la key governa claim/replay su tabella tecnica DB. La strong mode e'
  attiva solo se l'endpoint richiede la key, la key c'e' **e**
  `DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1` (default `0`).
  - Replay di una key gia' completata → `200` col payload salvato e header
    `X-Idempotency-Replayed: 1`.
  - Stessa key ancora in elaborazione → `E_IDEMPOTENCY_IN_PROGRESS` (409),
    `retryable`, quindi con `Retry-After`.

## Dipendenze DB
- `dbops.idempotency_keys` (solo strong mode).

## Note di migrazione
- Le policy retry non vanno duplicate nei domini.
- La validazione key deve restare centralizzata.
