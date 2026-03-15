# API reset_lotto_fattura_draft (Django)

## Scopo

Esporre via HTTP il reset tecnico di una singola fattura in un lotto MASSIVO in DRAFT.

## Contesto

Endpoint applicativo che invoca il servizio Python `fn_reset_lotto_fattura_draft`, wrapper della funzione SQL `vendite.fn_reset_lotto_fattura_draft`.

View in `apps/vendite/api/views.py`:

- `ApiResetLottoFatturaDraft`
- `ApiResetLottoFatturaDraft`

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/fatture/{fattura_id}/reset-draft/`
- Header richiesto: `Idempotency-Key`
- Header sicurezza (solo path `/api/v1/...`): `Authorization: Bearer <access_token>`
- Path params: `lotto_id` (int), `fattura_id` (int)
- Body JSON: vuoto

## Output

- `200`:

```json
{
  "data": {
    "updated_attivita": 1,
    "deleted_fatture": 1,
    "deleted_righe": 1
  },
  "meta": { ... }
}
```

- `400/409/404`: errore applicativo o stato lotto/fattura non valido

## Regole

- `lotto_id` e `fattura_id` validi e > 0 (estratti dal path URL).
- Ammesso solo per fatture di lotti MASSIVO in DRAFT (validato dal DB).
- Usa il pattern standard core `handle_post_json(...)`.
- Endpoint write protetto con obbligo `Idempotency-Key`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fn_reset_lotto_fattura_draft`
- `apps.vendite.services.pipeline_service.fn_reset_lotto_fattura_draft`

## Note di migrazione

- Azione granulare per ripristino singola fattura senza impattare l'intero lotto.
