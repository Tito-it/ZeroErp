# API reset_lotto_draft (Django)

## Scopo
Esporre via HTTP il reset tecnico di un lotto MASSIVO in DRAFT.

## Contesto
Endpoint applicativo che invoca il servizio Python `fn_reset_lotto_draft`, wrapper della funzione SQL `vendite.fn_reset_lotto_draft`.

## Input
- Metodo: `POST`
- Path canonico: `/api/v1/vendite/lotti/{id}/reset-draft/`
- Path legacy (deprecato): `/api/vendite/lotti/{id}/reset-draft/` (disabilitato di default)
- Header richiesto: `Idempotency-Key`
- Header sicurezza (solo path `/api/v1/...`): `Authorization: Bearer <access_token>`
- Body JSON: vuoto

## Output
- `200`: `{ "data": { "updated_lotti": <int>, "updated_attivita": <int>, "deleted_fatture": <int>, "deleted_righe": <int> }, "meta": { ... } }`
- `400/409/404`: errore applicativo o stato lotto non valido

## Regole
- `lotto_id` valido e > 0.
- Ammesso solo per lotti MASSIVO in DRAFT (validato dal DB).
- Usa il pattern standard core `handle_post_json(...)`.
- Endpoint write protetto con obbligo `Idempotency-Key`.

## Dipendenze DB
- `vendite.fn_reset_lotto_draft`

## Note di migrazione
- Azione applicativa introdotta per orchestrare il reset senza duplicare logica SQL.
