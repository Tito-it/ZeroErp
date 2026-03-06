# API pratica_riattiva (Django)

## Scopo

Esporre via HTTP la riattivazione di una pratica sospesa.

## Contesto

Endpoint di scrittura che delega a `pratiche_service.riattiva_pratica`. Il servizio cerca la sospensione attiva (data_fine IS NULL, flusso_id IS NULL), cambia lo stato pratica ad APERTA e chiude la sospensione impostando data_fine = NOW(). Il trigger DB ripristina gli stati dei flussi sospesi e registra nel giornale.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/riattiva/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body: `{}` (nessun parametro richiesto)

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: `pratica_id` non valido (`E_INVALID_ID`), nessuna sospensione attiva (`E_PRATICA_VALIDATION`)
- `401`: JWT mancante o non valido
- `404`: sospensione non trovata o gia' chiusa (`E_SOSPENSIONE_NOT_FOUND`)
- `409`: transizione di stato non ammessa (`E_PRATICHE_TRANSIZIONE_NON_AMMESSA`)

## Regole

- `pratica_id` deve essere > 0.
- Deve esistere una sospensione attiva sulla pratica (flusso_id IS NULL, data_fine IS NULL).
- Lo stato pratica torna ad APERTA.
- Il trigger DB ripristina i flussi che erano stati sospesi automaticamente.
- Wrappato in `@transaction.atomic()`.
- Permission: `riattiva_pratica` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.sospensioni` (UPDATE data_fine = NOW())
- `pratiche.pratiche` (UPDATE stato_id → APERTA)
- `pratiche.flussi` (ripristino stati via trigger)
- `pratiche.giornale` (INSERT automatico via trigger)

## Note di migrazione

- La chiusura sospensione con guard `data_fine IS NULL` previene doppie chiusure concorrenti.
