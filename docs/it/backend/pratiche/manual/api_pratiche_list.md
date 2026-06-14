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
  - **Lente di contesto canonica (D1, workflow v2)** — al massimo UNA tra:
    - `soggetto_ruolo_id` (int, opzionale) — pratiche del ruolo soggetto
    - `istanza_utility_id` (int, opzionale) — pratiche dell'istanza utility
    - `solo_interne` (bool, opzionale) — solo pratiche interne (senza soggetto)

    La verità del filtro vive in `pratiche.fn_lista_pratiche_per_contesto`
    (semi-join sulla query display standard). Due o più lenti insieme →
    `400 PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI` (catalogo DB id 484,
    validato fail-fast nel service + guard nella fn).
  - `priorita_id` (int, opzionale) — filtro priorità pratica (fix 2026-06-12:
    prima inviato dalla dashboard ma ignorato dalla view)
  - `risorsa_umana_id` (int, opzionale) — filtro operatore assegnato
  - `search` (string, opzionale) — ricerca ILIKE su codice, descrizione, ragione_sociale soggetto
  - `data_da` (string ISO date, opzionale) — filtro data inserimento da (>=)
  - `data_a` (string ISO date, opzionale) — filtro data inserimento a (<= fine giorno)
  - `limit` (int, opzionale) — righe per pagina, default `50`, max `200`
  - `offset` (int, opzionale) — offset paginazione, default `0`
  - `order_by` (string, opzionale) — colonna ordinamento, default `data_insert`
  - `order_dir` (string, opzionale) — direzione (`asc`/`desc`), default `desc`

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

Envelope paginata standard (`paginated_envelope`):

```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
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
- Ordinamento GET: configurabile via `order_by`/`order_dir`, default `data_insert DESC`, tiebreaker `id`.
- Whitelist colonne ordinamento: `codice`, `descrizione`, `data_apertura`, `data_scadenza`, `data_insert`, `tipo_prestazione_descrizione`, `stato_descrizione`, `priorita_descrizione`, `soggetto_display`, `risorsa_umana_display`.
- Paginazione offset: `COUNT(*)` + dati con `LIMIT/OFFSET`. Risposta via `paginated_envelope` (count, page, page_size, total_pages, results).
- Parsing parametri via `parse_list_params` e `qp_int_strict` (building block core).

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
- v2.2 (1 aprile 2026): risposta GET allineata a `paginated_envelope` (aggiunto page, page_size, total_pages). Parsing via `parse_list_params`/`qp_int_strict`. Aggiunti parametri `data_da`, `data_a`, `order_by`, `order_dir`.
