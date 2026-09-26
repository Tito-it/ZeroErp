# Zero ERP – Policy Ricerca e Paginazione (API/DB)

> **Obiettivo:** evitare risposte “a valanga” (migliaia/milioni di righe) che appesantiscono rete/UI e degradano il DB.
>
> **Principio:** *UI = paginazione + filtri*; *export = canale dedicato*.

---

## 1) Liste con crescita temporale (fatture, letture, movimenti, log, …)

### Regole

* **Filtro temporale di default** (per utente/ruolo), es.: ultimi **24–36 mesi**.
* Paginazione **obbligatoria** (mai “tutto”).
* **Max page size** fisso (es. 200/500) e non superabile da client.
* Sorting deterministico (es. `data DESC, id DESC`).

### Note UX

* Preferenze salvabili per utente (anno/periodo), così l’operatore non “subisce” il default.

---

## 2) Ricerche anagrafiche / descrittive (es. ragione sociale)

### 2.1 Regola “Smart default”

* Ricerca **prefix** di default (es. `term%`) quando applicabile.
* Ricerca **contains** (es. `%term%`) ammessa solo se:

  * lunghezza termine ≥ la **soglia della lista**: sulle liste configurabili
    la dichiara il catalogo (`ui.lista_definizione.ricerca_min_caratteri`, 1
    sulle tabelle di configurazione a codici corti, 3 sulle altre); altrove la
    soglia di progetto, **3**
  * paginazione obbligatoria + max page size

### 2.2 Protezioni lato API (DRF)

* **Min length** per `contains`/`icontains` (es. 3):

  * se `term` troppo corto → errore controllato o richiesta di raffinamento.
  * ⭐ **Sulle liste configurabili nessun errore**: sotto la soglia della lista
    il termine non filtra (decisione del 2026-09-26). L'errore resta per le
    ricerche dedicate e i lookup.
* **Rate limiting/throttling** sugli endpoint di search.
* **Hard cap** risultati navigabili (es. “result window” massima 10.000): oltre, richiedere filtri o export.
* Separare endpoint:

  * `GET /soggetti` (lista paginata, leggera)
  * `GET /soggetti/{id}` (dettaglio)
  * `GET /search/soggetti?term=...` (search dedicata)

### 2.3 Strategie DB (PostgreSQL)

* Per ricerche `ILIKE '%term%'` su campi testuali: usare **pg_trgm** + indice GIN.
* Valutare **FTS** (tsvector) per ricerche “a parole” con ranking (opzionale/fase 2).

> Esempio già adottato (ottimo):
> indice trigram su `anagrafiche.soggetti.ragione_sociale_completa`.

---

## 3) Paginazione consigliata (API)

* **Cursor pagination** consigliata per liste grandi e/o in continuo aggiornamento.
* **Offset pagination** ammessa solo per liste piccole/medie o casi specifici.

---

## 4) Export massivi

* Nessun export “tirando tutte le pagine”.
* Endpoint dedicato (asincrono):

  * `POST /exports/...` con filtri
  * creazione job
  * download quando pronto

---

## 5) Regola di stop (anti-coglione 😄)

* Query con `term` troppo corto (es. `"a"`, `"%a%"`) **non devono** poter generare carichi imprevedibili.
* Se la ricerca è troppo generica:

  * chiedere raffinamento (min length / filtri)
  * oppure fornire risultati limitati + avviso

---

## 6) Checklist implementativa (minima)

* [ ] Max page size fissato a livello DRF
* [ ] Min length su ricerche `contains`
* [ ] Cursor pagination per liste grandi
* [ ] Default temporale su archivi time-growing
* [ ] Throttling sugli endpoint search
* [ ] Export asincrono via job
