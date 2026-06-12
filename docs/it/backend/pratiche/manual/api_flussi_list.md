# API flussi_list (Django)

## Scopo

Esporre via HTTP la lista e la creazione dei flussi di una pratica.

## Contesto

GET restituisce i flussi ordinati per sequenza dal repository. POST delega a `pratiche_service.crea_flusso` che risolve lo stato iniziale DA_ESEGUIRE. Il trigger DB `trgfn_flussi_guard_prerequisiti` valida automaticamente i prerequisiti all'INSERT.

## Input

### GET — Lista flussi

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/`
- Header sicurezza: `Authorization: Bearer <access_token>`

### POST — Creazione flusso

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `template_flusso_id` (int, opzionale) — template flusso configurato
  - `risorsa_umana_id` (int, opzionale) — risorsa umana assegnata
  - `unita_organizzativa_id` (int, opzionale) — unita' organizzativa
  - `sequenza` (int, opzionale, default `0`) — ordine esecuzione nel workflow
  - `data_scadenza` (date, opzionale) — scadenza
  - `meta` (dict, opzionale) — metadati JSON

## Output

### GET 200:
```json
{
  "data": {
    "results": [
      {
        "id": 5,
        "pratica_id": 1,
        "template_flusso_id": 10,
        "stato_id": 1,
        "sequenza": 0,
        "esito": null,
        "data_scadenza": null,
        "meta": {},
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "zeroerp"
      }
    ]
  }
}
```

### POST 200:
```json
{
  "data": {
    "flusso_id": 99,
    "status": "ok"
  }
}
```

- `400`: `pratica_id` non valido (`E_INVALID_ID`), JSON non valido, prerequisiti non soddisfatti (errore DB)
- `401`: JWT mancante o non valido
- `409`: **flusso non ripetibile** (`PRATICHE_FLUSSO_NON_RIPETIBILE`, catalogo
  DB id 483, workflow v2 D3): la regola `template_flussi.ripetibilita` vieta
  una nuova istanza — `MAI` = esiste gia' un'istanza non annullata;
  `SE_NON_POSITIVO` = l'ultima istanza (`MAX(id)`) e' ancora aperta oppure
  chiusa con esito `POSITIVO`. `SEMPRE` non blocca mai.

## Regole

- GET: ordinamento `sequenza ASC, id ASC`.
- POST: `pratica_id` deve essere > 0.
- POST: lo stato iniziale `DA_ESEGUIRE` viene risolto da `config.stati_flussi_pratiche`.
- POST: se il flusso ha un `template_flusso_id`, il trigger DB `trgfn_flussi_guard_prerequisiti` verifica che tutti i prerequisiti del template siano soddisfatti; in caso contrario l'INSERT fallisce con errore DB.
- POST (2026-06-12, D3): il guard `trg_flussi_a10_guard_ripetibilita_ins`
  applica la regola di ripetibilita' del template; il service traduce
  l'errore DB nel codice parlante 483 via marker sul messaggio (vedi
  `pratiche_service._KNOWN_DB_ERROR_MARKERS`). Il FE decide se proporre
  "Ripeti" dal campo `ripetibile_adesso` del percorso (vedi
  [api_percorso](api_percorso.md)).
- POST: wrappato in `@transaction.atomic()`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.flussi` (tabella principale)
- `config.stati_flussi_pratiche` (risoluzione stato iniziale)
- `pratiche.fn_guard_prerequisiti_flusso` (trigger su INSERT)

## Note di migrazione

- La validazione prerequisiti e' interamente lato DB (trigger fail-fast).
- Il flusso senza template_flusso_id non ha prerequisiti e viene sempre creato.
