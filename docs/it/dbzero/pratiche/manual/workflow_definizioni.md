## 📘 Documentazione Concettuale – Tabella `pratiche.workflow_definizioni`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)
> [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
>
Funzioni collegate:
>
[pratiche.fn_risolvi_definizione](fn_risolvi_definizione.md)
> [pratiche.trgfn_tipi_prestazione_bootstrap_definizione](trgfn_tipi_prestazione_bootstrap_definizione.md)
> [pratiche.trgfn_template_flussi_default_definizione](trgfn_template_flussi_default_definizione.md)
> [pratiche.trgfn_pratiche_default_definizione](trgfn_pratiche_default_definizione.md)

---
### 🎯 Scopo Principale

La tabella `pratiche.workflow_definizioni` contiene le **edizioni versionate delle
definizioni di workflow** (modello C «edizioni + fork»). Una riga = **una edizione** del
workflow di un `tipo_prestazione` per uno **scope**:

* `emittente_fiscale_id NULL` → **preset**: vale per ogni emittente che non ha
  un'edizione propria;
* `emittente_fiscale_id` valorizzato → edizione della singola società (**fork**, Fase 2).

Risolve i due buchi storici del motore: le definizioni erano **globali** (due società
non potevano avere workflow diversi senza clonare il tipo) e le pratiche **non
pinnavano nulla** (modificare un template cambiava retroattivamente la roadmap delle
pratiche aperte).

---

### Ruolo nel processo

* **Identità condivisa**: il `tipo_prestazione` resta l'identità di reporting; le
  edizioni sono varianti/versioni del suo workflow.
* **Ciclo di vita**: `BOZZA` (editabile) → `PUBBLICATA` (istanziabile, **unica per
  scope**, strutturalmente immutabile dal guard di Fase 1) → `RITIRATA` (non
  istanziabile; le pratiche in volo continuano sul pin).
* **Pin alla creazione**: ogni pratica risolve e pinna la propria edizione alla nascita
  (`pratiche.definizione_id`, [auto-pin](trgfn_pratiche_default_definizione.md)) e la
  tiene per sempre.
* **Bootstrap**: ogni nuovo tipo prestazione nasce con il suo **preset v1 PUBBLICATA**
  ([trigger di bootstrap](trgfn_tipi_prestazione_bootstrap_definizione.md)) —
  invariante: `fn_risolvi_definizione` risolve sempre per un tipo appena creato.
* **Fase 0** (attuale): una definizione preset v1 per tipo ≡ comportamento odierno,
  nessun effetto visibile. **Fase 1**: guard (flusso↔definizione, immutabilità
  PUBBLICATA, immutabilità del pin, generazione cross-pratica definizione-aware).
  **Fase 2**: fork/nuova versione/pubblica + drift (`preset_origine_id`/`versione_origine`).

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `emittente_fiscale_id` | BIGINT nullable, FK → `anagrafiche.emittenti_fiscali`. NULL = preset; valorizzato = edizione della società (fork, Fase 2). |
| `versione` | INTEGER NOT NULL DEFAULT 1, CHECK > 0. Progressivo **per scope** (tipo, emittente). |
| `stato` | VARCHAR(20) CHECK (BOZZA, PUBBLICATA, RITIRATA) DEFAULT 'BOZZA'. Transizioni ammesse (guard Fase 1): BOZZA→PUBBLICATA, PUBBLICATA→RITIRATA. |
| `preset_origine_id` | INTEGER nullable, FK self (ON DELETE SET NULL). **Provenance del fork**: da quale definizione è nata questa edizione. |
| `versione_origine` | INTEGER nullable. Versione del preset d'origine al momento del fork — con `preset_origine_id` alimenta il rilevamento **drift** ("preset aggiornato", pattern DEF-2). |

---

### Vincoli

* **`uq_workflow_definizioni_scope_versione`** `(tipo_prestazione_id,
  emittente_fiscale_id, versione)` **NULLS NOT DISTINCT** — il preset (emittente NULL)
  è uno scope come gli altri.
* **`uq_workflow_definizioni_pubblicata`** — indice unico **parziale**
  `(tipo_prestazione_id, emittente_fiscale_id) NULLS NOT DISTINCT WHERE stato =
  'PUBBLICATA'`: una sola pubblicata per scope. È anche l'arbitro dell'`ON CONFLICT`
  del trigger di bootstrap.
* **`uq_workflow_definizioni_id_tipo`** `(id, tipo_prestazione_id)` — target delle
  **FK composite** dei figli (`template_flussi`, `pratiche`): un figlio non può mai
  puntare a una definizione di un altro tipo, per costruzione e senza trigger.
* **FK tipo → ON DELETE CASCADE** (deliberata): la definizione è metadato del tipo e
  senza tipo non ha senso; inoltre i cleanup pgTAP cancellano tipi sintetici. La
  protezione reale resta **transitiva**: template e pratiche referenziano la
  definizione con NO ACTION, quindi un tipo con figli vivi non è comunque cancellabile.

---

### Convenzioni

* Trigger standard (audit, tx_id, lock) applicati automaticamente da
  `dbops.fn_run_automations()`.
* Brief: `brief-db-step-dominio-e-definizioni-versionate.md` (Parte 2) — design:
  `brief-design-workflow-definizioni-versionate.md` (modello C, decisione 2026-07-02).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase0.sql`.

---

{% include-markdown "signature-core.md" %}
