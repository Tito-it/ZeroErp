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
  - `order_by` (string) — colonna di ordinamento, da **whitelist**
    (`VenditeRepository.LOTTI_SORT_COLUMNS`); la chiave è il `campo_sorgente` del
    catalogo liste, non il `codice` logico
  - `order_dir` (`asc` | `desc`)

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
        "emittente_ragione_sociale": "Emittente S.p.A.",
        "data_insert": "2026-02-18T10:00:00+01:00",
        "user_insert": "zeroerp",
        "n_fatture": 5,
        "totale_documenti": "1234.56",
        "ha_errori_gravi": false,
        "riaperto": false,
        "data_documento": null,
        "stato_congela_fiscale": false
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
- Ordinamento: **`data_insert DESC, id DESC` è il DEFAULT**, non un vincolo — la
  lista accetta `order_by`/`order_dir` su whitelist, con tiebreak deterministico.
  ⚠️ La riga precedente diceva «ordinamento fisso»: era falsa, corretta il
  2026-08-25.
- ⚠️ `totale_documenti` è una **stringa**: un totale fiscale non passa da un
  binario a virgola mobile. Zero è un totale valido (lotto senza documenti), non
  un vuoto.
- ⚠️ `data_documento` è la **dichiarazione** sul lotto, non la data che i
  documenti portano: `null` significa «nessuno ha dichiarato niente, decide la
  politica del registro» (`OGGI` / `FINE_MESE_COMPETENZA`), **non** «manca la
  data». È anche la ragione per cui la colonna di catalogo è `filtrabile = f`:
  un filtro su una colonna nulla nella maggioranza delle righe è una trappola.
- ⭐ `riaperto` = il lotto è stato riportato in lavorazione e lo step non è
  ancora stato rifatto (`fatturazione_lotti.riaperto_il`). Serve al FE per
  NOMINARE giusto la prossima esecuzione: su un lotto riaperto il run **rifà** lo
  step e il lotto resta in DRAFT.
  🔴 Fino al 2026-08-25 il mapper leggeva l'indice sbagliato e il flag valeva
  «questo lotto ha un totale diverso da zero» — invertito proprio sui casi veri.
  Presidio: `apps/vendite/tests/services/test_lotto_row_mapping.py`.
- ⭐ `stato_congela_fiscale` = lo stato fiscale del lotto **congela** il documento
  (`config.stati_doc_fiscale.congela_fiscale`). È la **soglia**, non un codice:
  serve a chi deve decidere se su quel lotto una pipeline ha ancora senso, senza
  enumerare stati — e uno stato nuovo a catalogo entra nel gate senza toccare
  nessun consumatore.
  ⚠️ *Fatto datato 2026-09-08*: il flag è vero su `DEFINITIVA`, `INVIATA`,
  `REGISTRATA`, `ANNULLATA` e falso su `DRAFT`/`EMESSA`. È il **contenuto** del
  catalogo, non la regola: si legge il flag, non questa riga.
  ⚠️ **`null` è un valore, e non significa «non congela»**: il JOIN sullo stato è
  LEFT (un lotto senza stato fiscale resta una riga), quindi `null` vuol dire
  «non lo so». Chi legge dev'essere **fail-closed** — `false` è l'unico valore
  che apre. È così che lo legge `verbiPipeline` in `useLottoAzioni`, per la
  stessa ragione per cui `can_reset_fattura` è fail-closed nel drawer: su un
  verbo che riesegue la pipeline «non lo so» non può voler dire «vai».
  ⛔ **Non ha una colonna a catalogo e non deve averla**: è un campo di *payload*
  per il gate delle azioni, non una colonna da mostrare. La regola in «Note di
  migrazione» vale nell'altro verso (catalogo ⇒ proiezione), non in questo.
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
- `anagrafiche.soggetti_ruoli` + `anagrafiche.soggetti` (ragione sociale emittente)
- `vendite.fatturazione_lotti_fatture` + `vendite.fatture` (conteggio, totale,
  spia errori gravi — sotto-query, non JOIN: un JOIN sul ponte moltiplicherebbe
  la riga del lotto per il numero delle sue fatture)

## Note di migrazione

- Query raw nel repository (`VenditeRepository.list_lotti`); nessuna funzione SQL dedicata.
- Due query per request: `COUNT(*)` + dati con `LIMIT/OFFSET` (pattern offset pagination).
- ⛔ **Il payload lo compone `_LOTTO_SELECT_COLS`, non una vista**: `vendite.lotti`
  è l'unica delle liste documento **senza `vista_sql`**. Chi aggiunge una colonna
  al catalogo (`ui.lista_colonna`) deve quindi aggiungerla **prima** qui, o la
  colonna compare a video **vuota su tutte le righe**; e se la dichiara
  `ordinabile = t` deve aggiungerla anche a `LOTTI_SORT_COLUMNS`, o la freccia
  risponde 400. Entrambe le cose sono presidiate da
  `apps/core/tests/test_liste_configurabili_seed.py`.
- `data_documento` (2026-08-25): colonna di catalogo `ui.lista_colonna` id 552,
  `ordine_default 25`, `priorita 85`, `filtrabile = f`. Brief:
  `dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md`.
- `stato_congela_fiscale` (2026-09-08): aggiunto in **coda** alla proiezione, e
  la posizione è una scelta — il mapper è posizionale e un indice sbagliato non
  fallisce, legge la colonna accanto (difetto reale del 2026-08-25 su
  `riaperto`). Inserirlo in mezzo avrebbe rinumerato 24 posizioni per ottenere
  una lettura più bella. Nessun JOIN nuovo: `sdf` c'era già.
  🔴 **Perché è nato**: il gate dei verbi di pipeline in `useLottoAzioni`
  leggeva `stato_doc_fiscale_codice !== 'DRAFT'`, cioè l'ennesima copia della
  soglia di congelamento che `D33` ha portato a leggere il database — l'ultima
  fuori dal DB era stata tolta da `LottoDrawer` il 2026-08-31 (F5) con la stessa
  motivazione. Su un lotto `ANNULLATA` rimasto in `stato_lotto = 'ERRORE'` quel
  gate proponeva «Rilancia lo step» (segnalazione team DB, lotto LTF-0009971).

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
