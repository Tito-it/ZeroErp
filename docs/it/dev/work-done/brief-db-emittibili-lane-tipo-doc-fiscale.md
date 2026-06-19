# Brief DB — Discovery corsie `(emittente, tipo_doc_fiscale)` per il driver batch

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* serve e *perché*; **non contiene DDL pronto** — il *come* (nome
> funzione, firma, tipi, changeset, indici, pgTAP) è scelta del team DB.
>
> **Data**: 2026-06-18 · **Stato**: ✅ **DB IMPLEMENTATO E TESTATO (2026-06-19)** —
> `vendite.fn_list_emittibili_lane` creata (changeset `20260619-01`), pgTAP
> `test-fn-list-emittibili-lane.sql`. Seguito poi da
> [brief-db-emittibili-lane-utility-id.md](brief-db-emittibili-lane-utility-id.md) che ha
> aggiunto l'asse `utility_id` alla stessa fn. BE driver: vedi
> [brief-be-driver-batch-lane-utility.md](brief-be-driver-batch-lane-utility.md).
> Novità chiave §2.3: la **competenza** è un terzo asse, non un semplice filtro.
>
> **Decisione concordata con Tid**: approccio **A3** — *nuova* funzione dedicata,
> lasciando `vendite.fn_list_commesse_emittibili` **intatta** (continua ad alimentare
> lo step di pull). Scartate A1 (esplosione righe della fn esistente) e A2 (colonna
> array sulla fn esistente) per non intrecciare due domande diverse nella stessa fn.
>
> **Origine**: gap emerso allo **smoke live** del batch CRON (primo run reale) —
> handoff `handoff_20260618_rls_pathA_jobrun_gap_tipo_doc_fiscale`. Seguito di
> [brief-db-emittibili-filtro-fatturazione-immediata.md](../work-done/brief-db-emittibili-filtro-fatturazione-immediata.md)
> (già implementato: stesso pattern di estensione della discovery).
>
> **Prerequisito di**: il fix del **management command** `run_fatturazione_batch`
> (Fase 3 del driver). Senza questa funzione il batch resta non operativo su entrambe
> le corsie (regola "prima il brief DB, poi il BE", [feedback_be_fe_attende_prerequisiti_db]).

---

## 1. Contesto e problema

Il batch CRON crea **un lotto per emittente** e porta a termine la pipeline. Ma un
**lotto è identificato anche dal `tipo_doc_fiscale`** (`fatturazione_lotti.tipo_doc_fiscale_id`
è **NOT NULL**; `fn_get_or_create_lotto` valida la coerenza del tipo_doc). Il driver
oggi:

- scopre solo gli **emittenti** distinti (`fn_list_commesse_emittibili` → BE
  `list_emittibili_emittenti`), **senza** il tipo_doc;
- crea il lotto con `tipo_doc_fiscale_id = NULL` → `fn_create_fatturazione_lotto`
  rifiuta (`p_tipo_doc_fiscale_id obbligatorio e > 0`).

**Sintomo live**: run reale completato in best-effort ma con `falliti=1` e **0 fatture**
generate, su entrambe le corsie (immediata e differita).

### Perché il tipo_doc è un asse di segregazione (non un dettaglio)

Tracciando il modello end-to-end:

1. `commesse_attivita.tipo_doc_fiscale_id` (nullable, default da config) → la pull
   `fn_emit_attivita_fatturabili_da_commessa` lo **propaga** ad
   `attivita_fatturabili.tipo_doc_fiscale_id`.
2. La pull è **tipo_doc-agnostica**: emette in AF **tutte** le righe APPROVATE+NON_EMESSA
   della commessa e le marca `EMESSA`, indipendentemente dal tipo_doc.
3. Lo step `select_attivita` (`fn_select_attivita_fatturabili`) seleziona le AF del lotto
   **filtrando per `p_tipo_doc_fiscale_id = lotto.tipo_doc_fiscale_id`** (oltre a
   BA/utility/emittente/competenza).

**Conseguenza del modello**: per un emittente con commesse a **tipo_doc misto**, un
*singolo* lotto cattura solo la propria fetta di tipo_doc; le righe AF degli **altri**
tipo_doc, già emesse e marcate `EMESSA` sulla commessa, **resterebbero orfane** (la
commessa non è più emittibile, nessun altro lotto le ripesca) → **fatturato perso in
modo silenzioso**. Per questo il driver **deve** iterare su **tutte** le coppie
`(emittente, tipo_doc)` presenti: così la pull del primo lotto scarica tutto in AF e
ogni lotto cattura via `select` la propria fetta — incluse quelle pullate da un altro
lotto della stessa corsia.

---

## 2. Cosa serve (risultato atteso)

Una **nuova funzione read-only** che risponda alla domanda del driver:

> «Per questa corsia/competenza/perimetro, quali **coppie distinte
> `(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id)`** hanno lavoro **pronto da
> fatturare**?»

Caratteristiche richieste (il *come* è del team DB):

- **Output**: righe distinte `(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id)`, con —
  utile per dry-run/diagnostica — un conteggio delle righe candidate (es.
  `total_candidate` o `n_commesse`).
- **Filtri** (stesso spirito di `fn_list_commesse_emittibili`): `p_competenza_mese`,
  `p_utility_id`, `p_fatturazione_immediata` (corsia: true/false/NULL), e opzionali
  `p_billing_account_id` / `p_emittente_soggetto_ruolo_id` (utili per il command con
  `--emittente-id`). `p_limit` normalizzato come la fn esistente (default 1000, max 10000).
- **STABLE / read-only**, nessun effetto collaterale.
- `vendite.fn_list_commesse_emittibili` resta **invariata** (A3).

### 2.1 Criteri di inclusione — punto critico: allineamento con la pull

La discovery delle corsie **deve riflettere ciò che la pull emetterà davvero**, cioè
righe **`stato_approvazione = 'APPROVATA'` AND `stato_emissione = 'NON_EMESSA'`** (la pull
gira con `p_only_approved = true`).

> ⚠️ Differenza rispetto alla fn esistente: `fn_list_commesse_emittibili` oggi conta le
> righe `NON_EMESSA` **senza** filtrare `stato_approvazione`. Se la nuova funzione delle
> corsie ereditasse quel criterio, produrrebbe coppie `(emittente, tipo_doc)` per le quali
> la pull poi emette **0 righe** → lotto vuoto creato inutilmente. La nuova funzione deve
> quindi aggiungere il filtro **APPROVATA** (oltre a `stato_commessa.emittibile = true` e
> al filtro competenza sulle righe, come la fn esistente).

Restano validi i criteri di testata della fn esistente: commessa in stato
`emittibile = true`; filtro competenza su `commesse_attivita.competenza_mese` quando
`p_competenza_mese` è fornito.

### 2.2 Gestione `tipo_doc_fiscale_id` NULL

`commesse_attivita.tipo_doc_fiscale_id` è **nullable**. Ma il lotto lo richiede
**NOT NULL**: una coppia con `tipo_doc = NULL` **non può** formare un lotto.

Decisione richiesta (vedi §4): le righe APPROVATE+NON_EMESSA con `tipo_doc_fiscale_id IS
NULL` devono essere **escluse** dalla discovery delle corsie (non fatturabili da qui,
analogamente a come il command già salta gli emittenti NULL) **oppure** la funzione deve
risolvere un default? La raccomandazione è **escluderle** (la risoluzione del default
appartiene al momento dell'upsert riga, non alla discovery — single source of truth), e
che il BE le **logghi come saltate** come fa già per gli emittenti NULL.

### 2.3 La competenza è un terzo asse (decisione presa)

Un lotto è identificato da `(emittente, tipo_doc, **competenza_mese**)`:
`fatturazione_lotti.competenza_mese` è **NOT NULL** e
`fn_select_attivita_fatturabili` filtra le AF con **`competenza_mese <= v_competenza`**
(cumulativo) `AND tipo_doc = …`. Due conseguenze:

1. **Il driver deve sapere quale competenza mettere sul lotto** (campo obbligatorio): la
   discovery deve quindi **restituirla**.
2. **Coerenza discovery↔select**: la fn esistente filtra la competenza con `=` (esatto),
   ma la select usa `<=` (cumulativo). Se la lane fn ereditasse `=`, una coppia con soli
   **arretrati** (righe `< mese`) non verrebbe scoperta, mentre la select li avrebbe
   catturati → **fatturato arretrato perso in silenzio**.

**Decisione**: la lane fn (a) filtra la competenza con **`<= p_competenza_mese`**
(cumulativo, allineato alla select; `NULL` = nessun limite superiore) e (b) **restituisce
`competenza_mese = max(ca.competenza_mese)`** fra le righe candidate della coppia — la
competenza con cui il driver crea il lotto (la select `<=` spazza poi tutti gli arretrati).
Funziona anche con `p_competenza_mese = NULL` (run-all), dove altrimenti la competenza del
lotto sarebbe indefinita.

---

## 3. Criteri di accettazione

Con, per uno stesso emittente E e competenza/perimetro:

- commessa A: 2 righe APPROVATA+NON_EMESSA tipo_doc = X;
- commessa B: 1 riga APPROVATA+NON_EMESSA tipo_doc = X, 1 riga APPROVATA+NON_EMESSA
  tipo_doc = Y;
- commessa C: 1 riga **NON approvata** NON_EMESSA tipo_doc = Z;
- commessa D: 1 riga APPROVATA+NON_EMESSA tipo_doc = **NULL**;

la discovery (corsia coerente con A/B/C/D) deve restituire **esattamente** le coppie:

- `(E, X)` e `(E, Y)`;
- **non** `(E, Z)` (riga non approvata);
- **non** `(E, NULL)` (tipo_doc assente → vedi §4).

Inoltre:

- filtro corsia `fatturazione_immediata` rispettato (true/false/NULL come la fn esistente);
- nessun effetto su `fn_list_commesse_emittibili` (resta com'è);
- copertura pgTAP nello stile dei test commesse/pipeline (incl. caso tipo_doc misto e
  caso tipo_doc NULL escluso).

---

## 4. Decisioni prese (2026-06-19)

1. **`tipo_doc_fiscale_id IS NULL`** → **escluse** dalla discovery (il lotto lo richiede
   NOT NULL; il default appartiene all'upsert, non alla discovery). Il BE le logga come saltate.
2. **Criterio inclusione** → **`stato_approvazione = 'APPROVATA'` AND `stato_emissione =
   'NON_EMESSA'`** (allineato alla pull `p_only_approved=true`).
3. **Competenza** (§2.3) → filtro **`<= p_competenza_mese`** (cumulativo) + output
   **`competenza_mese = max(...)`** per coppia.
4. **Conteggio** → `total_candidate` (righe candidate). `n_commesse` non incluso (non serve).
5. **Nome/firma**:
   `vendite.fn_list_emittibili_lane(p_competenza_mese, p_billing_account_id, p_utility_id,
   p_emittente_soggetto_ruolo_id, p_fatturazione_immediata, p_limit)`
   → `TABLE(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, **competenza_mese**, total_candidate)`.
   `STABLE`, `%TYPE`, `p_limit` norm. (default 1000, max 10000); `LIMIT` sulle **coppie**.

### Piano DB (deliverable)

| # | Deliverable | Path | Note |
| --- | --- | --- | --- |
| E1 | `vendite.fn_list_emittibili_lane` (§4.5) | `20_code/vendite/20260619-01-…` | `runOnChange:false` + `validCheckSum:[ANY]`; `fn_list_commesse_emittibili` **intatta** |
| E2 | Indice **parziale** `ix_commesse_attivita_lane_candidate` su `commesse_attivita (commessa_id, competenza_mese, tipo_doc_fiscale_id)` WHERE candidate | `00_schema/vendite/20260619-02-…` | **FATTO** (deciso: fatturazione accumula nel tempo). Parziale → resta compatto (indicizza solo le righe candidate) |
| E3 | pgTAP: tipo_doc misto, non-approvata esclusa, tipo_doc NULL esclusa, filtro corsia, **arretrati `<` mese inclusi via `<=`**, fn esistente non toccata | `db/pgtap/vendite/test-fn-list-emittibili-lane.sql` | criteri §3 + caso competenza |
| E4 | Manual companion doc (autogen via `gen_db_docs.py`) | `docs/it/dbzero/vendite/manual/fn_list_emittibili_lane.md` | — |

---

## 5. Fuori scope (BE — dopo questo brief)

Lato backend, a valle della funzione (solo BE, nessuna azione DB):

- `CommesseRepository`: nuovo metodo `list_emittibili_lane(...)` che wrappa la fn e
  ritorna le coppie `(emittente, tipo_doc)`.
- `run_fatturazione_batch`: il loop itera sulle **coppie** invece che sugli emittenti;
  passa `tipo_doc_fiscale_id` a `run_lotto_pipeline_until_done`; `--dry-run` conta per
  coppia; log "saltati" per tipo_doc NULL (come già per emittente NULL).
- `meta` di `job_run_log`: riepilogo per coppia (n. coppie, falliti, per_motivo).
- Nessuna modifica alla pull né a `fn_list_commesse_emittibili`.

> La pull resta tipo_doc-agnostica **per disegno**: è corretta finché il driver apre un
> lotto per **ogni** coppia `(emittente, tipo_doc)` della corsia (vedi §1).
