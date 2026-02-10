# API reset lotto fattura draft

## Scopo
Endpoint applicativo che invoca il servizio Python `fn_reset_lotto_fattura_draft`.

## Contesto
Reset di una singola fattura in lotto MASSIVO DRAFT.

## Request
- Method: `POST`
- URL: `/api/vendite/lotti/{lotto_id}/fatture/{fattura_id}/reset-draft/`
- Header: `Idempotency-Key` obbligatorio
- Body: vuoto

## Response (200)
```json
{
  "data": {
    "updated_attivita": 1,
    "deleted_fatture": 1,
    "deleted_righe": 1
  }
}
```

## Regole
- `Idempotency-Key` obbligatorio.
- Autenticazione JWT per `/api/v1/*`.

## Dipendenze
- `vendite.fn_reset_lotto_fattura_draft`
- `apps.vendite.services.pipeline_service.fn_reset_lotto_fattura_draft`
