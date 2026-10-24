# API flusso_riattiva (Django)

## Scopo

Esporre via HTTP la riattivazione di un singolo flusso sospeso.

## Contesto

Endpoint di scrittura che delega a `pratiche_service.riattiva_flusso`. Il servizio verifica l'ownership flusso/pratica, cerca la sospensione attiva sul flusso, cambia lo stato a IN_CORSO e chiude la sospensione impostando data_fine = NOW(). Il trigger DB registra nel giornale.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/riattiva/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body: `{}` (nessun parametro richiesto)

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: ID non validi (`E_INVALID_ID`), flusso non della pratica (`E_FLUSSO_OWNERSHIP`), nessuna sospensione attiva (`E_FLUSSO_VALIDATION`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`), sospensione non trovata (`E_SOSPENSIONE_NOT_FOUND`)
- `409`: transizione di stato non ammessa (`E_FLUSSI_TRANSIZIONE_NON_AMMESSA`)

## Regole

- `pratica_id` e `flusso_id` devono essere > 0.
- Il flusso deve appartenere alla pratica indicata (ownership check).
- Deve esistere una sospensione attiva sul flusso (data_fine IS NULL).
- Lo stato flusso torna a IN_CORSO (ripresa manuale).
- Wrappato in `@transaction.atomic()`.
- Permission: `riattiva_flusso` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.sospensioni` (UPDATE data_fine = NOW())
- `pratiche.flussi` (UPDATE stato_id → IN_CORSO, verifica ownership)
- `pratiche.giornale` (INSERT automatico via trigger)

## Note di migrazione

- L'ownership check e' centralizzato nella funzione helper `_verifica_flusso_pratica` nel service.
- La guard `data_fine IS NULL` nell'UPDATE previene chiusure concorrenti.
