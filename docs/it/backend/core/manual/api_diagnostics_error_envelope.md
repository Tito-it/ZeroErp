# API diagnostics error envelope (Core Django)

## Scopo
Fornire un endpoint tecnico per validare contratto error envelope e policy retry.

## Contesto
View in `apps/core/api/views.py`:
- `ApiDiagnosticsErrorEnvelope`
- `ApiDiagnosticsErrorEnvelope`

## Input
- `GET /api/v1/core/diagnostics/error-envelope/`
- Query opzionale `kind`:
  - `generic`
  - `retryable`
  - `not_found`

## Output
- Risposta errore in envelope standard (`error` + `meta`).
- `Retry-After` presente per il caso `retryable`.

## Regole
- `kind=generic` -> errore generico (`E_GENERICO`).
- `kind=retryable` -> errore retryable (`E_DATABASE_RETRYABLE`).
- `kind=not_found` -> errore not-found di dominio (`E_PIPELINE_LOTTO_NOT_FOUND`).
- Endpoint v1 richiede JWT.

## Dipendenze DB
- Nessuna diretta.

## Note di migrazione
- Utile per smoke test e verifica regressioni middleware/translator senza coinvolgere logica dominio.
