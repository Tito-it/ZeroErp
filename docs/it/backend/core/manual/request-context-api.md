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
- `X-Request-ID` del client si accetta solo se è un UUID, in forma canonica (BB `optional_uuid`), ed è rimandato in risposta. Se manca, è vuoto o non è un UUID se ne genera uno, senza rifiutare la richiesta: finisce in colonne `uuid` (`dbops.request_log`, `dbops.sessioni_utente`), e un valore qualunque ne faceva fallire l'INSERT (S-1, chiuso 2026-09-27).
- Idempotency key: si legge `Idempotency-Key`, in alternativa `X-Idempotency-Key`; il valore viene ripulito dagli spazi e una chiave vuota o più lunga di 128 caratteri è **ignorata** (nessun header in risposta, nessun `meta.idempotency_key`).
- La chiave valida viene propagata per tracing (policy retry/write).
- Il contesto (`contextvars`) è azzerato a fine risposta e in caso di eccezione.

## Dipendenze DB
- Nessuna

## Note di migrazione
- Introdotto per migliorare tracing/debug cross-layer senza impattare i service dominio.
