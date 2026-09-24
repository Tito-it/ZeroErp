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
- Se `X-Request-ID` manca (o è vuoto), viene generato un UUID; se il client lo invia, il valore è accettato così com'è, senza controlli di formato né di lunghezza, ed è rimandato in risposta.
  - ⚠️ Difetto noto ([S-1](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md)): un `X-Request-ID` che non è un UUID fa fallire in silenzio le INSERT di `dbops.request_log` e `dbops.sessioni_utente`, che lo scrivono in colonne `uuid`.
- Idempotency key: si legge `Idempotency-Key`, in alternativa `X-Idempotency-Key`; il valore viene ripulito dagli spazi e una chiave vuota o più lunga di 128 caratteri è **ignorata** (nessun header in risposta, nessun `meta.idempotency_key`).
- La chiave valida viene propagata per tracing (policy retry/write).
- Il contesto (`contextvars`) è azzerato a fine risposta e in caso di eccezione.

## Dipendenze DB
- Nessuna

## Note di migrazione
- Introdotto per migliorare tracing/debug cross-layer senza impattare i service dominio.
