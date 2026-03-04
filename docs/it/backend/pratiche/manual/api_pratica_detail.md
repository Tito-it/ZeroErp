# API pratica_detail (Django)

## Scopo

Esporre via HTTP il dettaglio e l'aggiornamento di una singola pratica.

## Contesto

GET restituisce la pratica dal repository. PATCH delega a `pratiche_service.aggiorna_pratica` che verifica esistenza e aggiorna solo i campi consentiti. Entrambi i metodi operano su `pratiche.pratiche`.

## Input

### GET — Dettaglio pratica

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/`
- Header sicurezza: `Authorization: Bearer <access_token>`

### PATCH — Aggiornamento pratica

- Metodo: `PATCH`
- Path canonico: `/api/v1/pratiche/<pratica_id>/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body (campi aggiornabili):
  - `descrizione` (string, opzionale)
  - `data_scadenza` (date, opzionale)
  - `soggetto_id` (UUID, opzionale)
  - `risorsa_umana_id` (int, opzionale)
  - `unita_organizzativa_id` (int, opzionale)
  - `meta` (dict, opzionale)

## Output

### GET 200:
```json
{
  "data": {
    "id": 1,
    "emittente_fiscale_id": 10,
    "tipo_prestazione_id": 5,
    "stato_id": 1,
    "priorita_id": 2,
    "codice": "P-001",
    "descrizione": "Pratica di esempio",
    "solo_interna": false,
    "meta": {},
    "data_insert": "2026-03-04T10:00:00+00:00",
    "user_insert": "zeroerp"
  }
}
```

### PATCH 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: JSON non valido
- `401`: JWT mancante o non valido
- `404`: pratica non trovata (`E_PRATICA_NOT_FOUND`)

## Regole

- GET: se la pratica non esiste → `E_PRATICA_NOT_FOUND` (404).
- PATCH: solo i campi nella whitelist sono aggiornabili; campi non riconosciuti vengono ignorati.
- PATCH: `pratica_id` deve essere > 0, altrimenti → `E_INVALID_ID` (400).
- PATCH: verifica esistenza pratica prima dell'update.
- PATCH: wrappato in `@transaction.atomic()`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.pratiche` (tabella principale)

## Note di migrazione

- Update dinamico con SET costruito da whitelist (`PraticheRepository.update_pratica`).
- Campo `meta` serializzato come `jsonb`.
