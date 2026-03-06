# API pratica_sospendi (Django)

## Scopo

Esporre via HTTP la sospensione di una pratica con motivo obbligatorio e data di riattivazione opzionale.

## Contesto

Endpoint di scrittura che delega a `pratiche_service.sospendi_pratica`. Il servizio verifica che non esista gia' una sospensione attiva sulla pratica, cambia lo stato a SOSPESA e inserisce il record in `pratiche.sospensioni`. I trigger DB propagano la sospensione ai flussi attivi e registrano nel giornale.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/sospendi/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `motivo` (string, **obbligatorio**) — motivazione della sospensione
  - `data_riattivazione_prevista` (string, opzionale) — data ISO `YYYY-MM-DD` di riattivazione automatica prevista

## Output

### 200:
```json
{ "data": { "sospensione_id": 100, "status": "ok" } }
```

- `400`: motivo vuoto (`E_PRATICA_VALIDATION`), pratica gia' sospesa (`E_PRATICA_VALIDATION`), `pratica_id` non valido (`E_INVALID_ID`)
- `401`: JWT mancante o non valido
- `409`: transizione di stato non ammessa (`E_PRATICHE_TRANSIZIONE_NON_AMMESSA`)

## Regole

- `pratica_id` deve essere > 0.
- `motivo` non puo' essere vuoto o solo spazi.
- Non puo' esistere una sospensione attiva (data_fine IS NULL) sulla stessa pratica.
- Il trigger DB valida la transizione di stato verso SOSPESA.
- Il trigger DB propaga la sospensione ai flussi con stato IN_CORSO.
- Wrappato in `@transaction.atomic()`.
- Permission: `sospendi_pratica` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.sospensioni` (INSERT sospensione)
- `pratiche.pratiche` (UPDATE stato_id → SOSPESA)
- `pratiche.flussi` (propagazione sospensione via trigger)
- `pratiche.giornale` (INSERT automatico via trigger)

## Note di migrazione

- La validazione motivo e' centralizzata nel service (non nella view).
- La propagazione ai flussi e' gestita interamente dal trigger DB `trgfn_sospensioni_after_insert`.
