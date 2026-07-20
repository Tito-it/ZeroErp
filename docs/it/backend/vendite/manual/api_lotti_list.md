# API list_lotti (Django)

## Scopo

Esporre via HTTP l'elenco paginato dei lotti di fatturazione con filtri opzionali e decodifica delle FK.

## Contesto

Endpoint di sola lettura che interroga direttamente `vendite.fatturazione_lotti` con LEFT JOIN su tabelle di decodifica (`config.utilities`, `config.stati_doc_fiscale`, `config.tipi_doc_fiscale`, `vendite.area_geografica_fatturazione`). Nessuna funzione SQL intermedia: query raw nel repository.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Query param (tutti opzionali; assente o vuoto = nessun filtro):
  - `competenza_mese` (date `YYYY-MM-DD`) — filtro mese di competenza
  - `utility_id` (int) — filtro per utility
  - `stato_lotto` (string) — filtro stato lotto (es. `DRAFT`, `COMPLETATO`)
  - `area_geografica_id` (int) — filtro per area geografica fatturazione
  - `tipo_doc_fiscale_id` (int) — filtro per tipo documento fiscale
  - `emittente_soggetto_ruolo_id` (int) — filtro per emittente fiscale
  - `page` (int) — numero pagina, default `1`
  - `page_size` (int) — righe per pagina, default `50`, max `200`

## Output

- `200`:
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
        "codice": "LOT-2026-001",
        "competenza_mese": "2026-02-01",
        "tipo_lotto": "MASSIVO",
        "utility_id": 1,
        "utility_descrizione": "Energia Elettrica",
        "stato_lotto": "DRAFT",
        "stato_operativo": "APERTO",
        "stato_doc_fiscale_id": 3,
        "stato_doc_fiscale_descrizione": "Fattura emessa",
        "tipo_doc_fiscale_id": 1,
        "tipo_doc_fiscale_descrizione": "Fattura",
        "area_geografica_id": 2,
        "area_geografica_descrizione": "Nord",
        "emittente_soggetto_ruolo_id": 7,
        "data_insert": "2026-02-18T10:00:00+01:00",
        "user_insert": "zeroerp"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```
- `400`: parametri paginazione non validi (`E_PIPELINE_VALIDATION`)
- `401`: JWT mancante o non valido

## Regole

- Tutti i filtri sono opzionali; assenza o valore vuoto equivale a nessun filtro.
- `page` deve essere >= 1; `page_size` deve essere compreso tra 1 e 200.
- Ordinamento fisso: `data_insert DESC, id DESC` (deterministico).
- LEFT JOIN su tutte le tabelle di decodifica: lotti con FK nullable restituiscono `null` nei campi descrizione corrispondenti.
- La JOIN su `area_geografica_id` punta a `vendite.area_geografica_fatturazione` (non `config.aree_geografiche`).
- `is_search_endpoint = True` sulla view: attiva throttling `SearchBurstRateThrottle`.
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fatturazione_lotti` (tabella principale)
- `config.utilities` (LEFT JOIN decodifica utility)
- `config.stati_doc_fiscale` (LEFT JOIN decodifica stato doc fiscale)
- `config.tipi_doc_fiscale` (LEFT JOIN decodifica tipo doc fiscale)
- `vendite.area_geografica_fatturazione` (LEFT JOIN decodifica area geografica)

## Note di migrazione

- Query raw nel repository (`VenditeRepository.list_lotti`); nessuna funzione SQL dedicata.
- Due query per request: `COUNT(*)` + dati con `LIMIT/OFFSET` (pattern offset pagination).

---

## Dettaglio testata lotto (cockpit Fase B)

### Scopo

Restituire la testata di un singolo lotto per il drawer diagnostico del cockpit
fatturazione (registro dei giri). Stessa proiezione della lista (nessuna vista o
colonna nuova); le sotto-risorse restano endpoint separati (`fatture/`,
`task-runs/`, `segnalazioni/`).

### Input

- Metodo: `GET`
- Path: `/api/v1/vendite/lotti/{lotto_id}/`
- Header: `Authorization: Bearer <token>`
- Path param: `lotto_id` (int)

### Output

- `200`: `{ "data": { ...testata lotto (stessi campi di una riga della lista)... } }`
- `400`: `E_LOTTO_PARAMETRO_NON_COERENTE` — `lotto_id` non valido (≤ 0)
- `401`: JWT mancante
- `404`: `E_LOTTO_NON_TROVATO` — lotto inesistente **o fuori scope emittente**
  (indistinguibili, per non leakare l'esistenza — coerente con la RLS operatori)

### Regole

- View `ApiLottoDetail` → service `fn_get_lotto` → `VenditeRepository.get_lotto`.
- Scope emittente applicato in repository (`_add_scope_emittente` su
  `emittente_soggetto_ruolo_id`, con `get_scope_user_id` dalla view): un lotto
  fuori scope torna 404, identico a un id inesistente.
- Sola lettura: nessun `Idempotency-Key`.
- Proiezione + JOIN + mapping condivisi con `list_lotti` (`_LOTTO_SELECT_COLS`,
  `_LOTTO_JOINS`, `_map_lotto_row`) — nessuna duplicazione.

### Dipendenze DB

- `vendite.fatturazione_lotti` + le stesse LEFT JOIN di decodifica della lista.
