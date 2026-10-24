# API flusso_sospendi (Django)

## Scopo

Esporre via HTTP la sospensione di un singolo flusso all'interno di una pratica.

## Contesto

Endpoint di scrittura che delega a `pratiche_service.sospendi_flusso`. Il servizio verifica l'ownership flusso/pratica, controlla che non esista gia' una sospensione attiva sul flusso, cambia lo stato a SOSPESO e inserisce il record in `pratiche.sospensioni` con `flusso_id` specifico. Il trigger DB registra nel giornale.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/sospendi/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `motivo` (string, **obbligatorio**) — motivazione della sospensione
  - `data_riattivazione_prevista` (string, opzionale) — data ISO `YYYY-MM-DD` di riattivazione automatica prevista

## Output

### 200:
```json
{ "data": { "sospensione_id": 200, "status": "ok" } }
```

- `400`: motivo vuoto (`E_FLUSSO_VALIDATION`), flusso gia' sospeso (`E_FLUSSO_VALIDATION`), flusso non della pratica (`E_FLUSSO_OWNERSHIP`), ID non validi (`E_INVALID_ID`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)
- `409`: transizione di stato non ammessa (`E_FLUSSI_TRANSIZIONE_NON_AMMESSA`)

## Regole

- `pratica_id` e `flusso_id` devono essere > 0.
- Il flusso deve appartenere alla pratica indicata (ownership check).
- `motivo` non puo' essere vuoto o solo spazi.
- Non puo' esistere una sospensione attiva (data_fine IS NULL) sullo stesso flusso.
- Il trigger DB valida la transizione di stato verso SOSPESO.
- Wrappato in `@transaction.atomic()`.
- Permission: `sospendi_flusso` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.sospensioni` (INSERT sospensione con flusso_id)
- `pratiche.flussi` (UPDATE stato_id → SOSPESO, verifica ownership)
- `pratiche.giornale` (INSERT automatico via trigger)

## Note di migrazione

- L'ownership check e' centralizzato nella funzione helper `_verifica_flusso_pratica` nel service.
- A differenza della sospensione pratica, la sospensione flusso non propaga ad altri flussi.
