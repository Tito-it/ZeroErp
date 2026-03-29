# API pratiche_list (Django)

## Scopo

Esporre via HTTP l'elenco paginato delle pratiche con filtri e la creazione di nuove pratiche.

## Contesto

Endpoint di lettura e scrittura su `pratiche.pratiche`. La GET interroga il repository con JOIN
su 6 tabelle (tipi_prestazione, stati, priorita', soggetti, risorse_umane, unita_organizzative)
per restituire dati pronti per la UI con display fields. La POST delega a
`pratiche_service.crea_pratica` che valida il contesto anagrafico, risolve lo stato iniziale
BOZZA e inserisce la pratica in transazione atomica.

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
  - `search` (string, opzionale) — ricerca ILIKE su codice, descrizione, ragione_sociale soggetto
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
  - `soggetto_ruolo_id` (int, opzionale) — FK a soggetti_ruoli (richiede soggetto_id)
  - `istanza_utility_id` (int, opzionale) — FK a istanze_utilities (richiede soggetto_ruolo_id)
  - `risorsa_umana_id` (int, opzionale) — risorsa umana assegnata
  - `unita_organizzativa_id` (int, opzionale) — unita' organizzativa
  - `canale_origine_id` (int, opzionale) — canale di origine
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
        "soggetto_id": "aaa-bbb-ccc",
        "soggetto_ruolo_id": 100,
        "istanza_utility_id": null,
        "stato_id": 1,
        "priorita_id": 2,
        "risorsa_umana_id": null,
        "unita_organizzativa_id": null,
        "pratica_padre_id": null,
        "flusso_origine_id": null,
        "canale_origine_id": null,
        "codice": "PRA-0000001",
        "descrizione": "Manutenzione caldaia",
        "data_apertura": null,
        "data_scadenza": "2026-04-30",
        "meta": {},
        "data_insert": "2026-03-28T10:00:00+00:00",
        "user_insert": "operatore1",
        "tipo_prestazione_codice": "MANUTENZIONE",
        "tipo_prestazione_descrizione": "Manutenzione ordinaria",
        "stato_codice_interno": "BOZZA",
        "stato_descrizione": "Bozza",
        "priorita_codice_interno": "NORMALE",
        "priorita_descrizione": "Normale",
        "soggetto_display": "Rossi Mario",
        "risorsa_umana_display": null,
        "unita_organizzativa_descrizione": null
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

- `400`: validazione fallita (`E_PRATICA_VALIDATION`), JSON non valido, contesto anagrafico incoerente
- `401`: JWT mancante o non valido

## Regole

- `emittente_fiscale_id` obbligatorio su GET; se assente → 400.
- Su POST, `emittente_fiscale_id`, `tipo_prestazione_id` e `priorita_id` devono essere > 0.
- Lo stato iniziale della pratica e' `BOZZA`, risolto automaticamente da `config.stati_pratiche`.
- Il codice pratica `PRA-NNNNNNN` e' generato dal trigger DB via `config.sistema_codici`.
- Validazione contesto anagrafico (service + trigger DB guard):
  - `istanza_utility_id` richiede `soggetto_ruolo_id`
  - `soggetto_ruolo_id` richiede `soggetto_id`
  - Il ruolo deve appartenere al soggetto
  - L'istanza deve appartenere al soggetto
- `is_search_endpoint = True` sulla view GET: attiva throttling `SearchBurstRateThrottle`.
- Ordinamento GET: `data_insert DESC, id`.
- Paginazione offset: `COUNT(*)` + dati con `LIMIT/OFFSET`.

## Dipendenze DB

- `pratiche.pratiche` (tabella principale)
- `pratiche.tipi_prestazione` (JOIN display)
- `config.stati_pratiche` (JOIN display + filtro)
- `config.priorita_pratiche` (JOIN display)
- `anagrafiche.soggetti` (LEFT JOIN display)
- `anagrafiche.risorse_umane` → `anagrafiche.soggetti_ruoli` → `anagrafiche.soggetti` (LEFT JOIN catena per nome risorsa)
- `config.unita_organizzative` (LEFT JOIN display)

## Note di migrazione

- v2 (28 marzo 2026): aggiunti `soggetto_ruolo_id`, `istanza_utility_id`, display fields via JOIN, parametro `search`.
- v2.1 (29 marzo 2026): aggiunto `data_apertura` (DATE, valorizzato da trigger alla transizione BOZZA → APERTA).
- Rimosso `solo_interna` (campo eliminato dal DB).
- I display fields eliminano la necessita' di lookup client-side per le colonne lista.
