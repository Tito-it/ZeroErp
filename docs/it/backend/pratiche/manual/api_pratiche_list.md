# API pratiche_list (Django)

## Scopo

Esporre via HTTP l'elenco paginato delle pratiche con filtri e la creazione di nuove pratiche.

## Contesto

Endpoint di lettura e scrittura su `pratiche.pratiche`. La GET interroga il repository con JOIN su `config.stati_pratiche` per filtro stato. La POST delega a `pratiche_service.crea_pratica` che risolve lo stato iniziale BOZZA e inserisce la pratica in transazione atomica.

## Input

### GET — Lista pratiche

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Query param:
  - `emittente_fiscale_id` (int, **obbligatorio**) — ID emittente fiscale
  - `stato` (string, opzionale) — codice_interno stato pratica (es. `BOZZA`, `APERTA`)
  - `tipo_prestazione_id` (int, opzionale) — filtro tipo prestazione
  - `soggetto_id` (string UUID, opzionale) — filtro UUID soggetto
  - `solo_interna` (bool, opzionale) — filtro flag solo_interna
  - `limit` (int, opzionale) — righe per pagina, default `50`, max `200`
  - `offset` (int, opzionale) — offset paginazione, default `0`

### POST — Creazione pratica

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `emittente_fiscale_id` (int, **obbligatorio**) — ID emittente fiscale (> 0)
  - `tipo_prestazione_id` (int, **obbligatorio**) — ID tipo prestazione (> 0)
  - `priorita_id` (int, **obbligatorio**) — ID priorita' (> 0)
  - `soggetto_id` (UUID, opzionale) — UUID soggetto
  - `risorsa_umana_id` (int, opzionale) — risorsa umana assegnata
  - `unita_organizzativa_id` (int, opzionale) — unita' organizzativa
  - `canale_origine_id` (int, opzionale) — canale di origine
  - `solo_interna` (bool, opzionale, default `false`) — pratica solo interna
  - `descrizione` (string, opzionale) — descrizione libera
  - `data_scadenza` (date, opzionale) — scadenza
  - `meta` (dict, opzionale) — metadati JSON

## Output

### GET 200:
```json
{
  "data": {
    "count": 1,
    "results": [
      {
        "id": 42,
        "emittente_fiscale_id": 10,
        "tipo_prestazione_id": 5,
        "soggetto_id": null,
        "stato_id": 1,
        "priorita_id": 2,
        "codice": "P-001",
        "descrizione": "Test pratica",
        "solo_interna": false,
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
    "pratica_id": 42,
    "status": "ok"
  }
}
```

- `400`: validazione fallita (`E_PRATICA_VALIDATION`), JSON non valido
- `401`: JWT mancante o non valido

## Regole

- `emittente_fiscale_id` obbligatorio su GET; se assente → 400.
- Su POST, `emittente_fiscale_id`, `tipo_prestazione_id` e `priorita_id` devono essere > 0.
- Lo stato iniziale della pratica e' `BOZZA`, risolto automaticamente da `config.stati_pratiche`.
- `is_search_endpoint = True` sulla view GET: attiva throttling `SearchBurstRateThrottle`.
- Ordinamento GET: `data_insert DESC, id DESC`.
- Paginazione offset: `COUNT(*)` + dati con `LIMIT/OFFSET`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.pratiche` (tabella principale)
- `config.stati_pratiche` (JOIN per filtro stato, lookup stato iniziale)

## Note di migrazione

- Query raw nel repository (`PraticheRepository.list_pratiche`, `PraticheRepository.create_pratica`).
- Il codice pratica `P-XXX` viene generato dal DB (trigger/default).
