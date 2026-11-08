## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_template_flussi_guard_immutabile`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — la tabella sorvegliata
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — l'edizione a cui il template appartiene
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_definizione_struttura_bloccata](/dbzero/pratiche/funzioni/fn_check_definizione_struttura_bloccata) — il predicato per inserimento e modifica
> * [pratiche.fn_check_definizione_congelata](/dbzero/pratiche/funzioni/fn_check_definizione_congelata) — il predicato per la cancellazione
> * [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — la stessa regola sui figli del template
> * [pratiche.trgfn_workflow_definizioni_guard](/dbzero/pratiche/funzioni/trgfn_workflow_definizioni_guard) — l'intestazione e le transizioni dell'edizione
> * [pratiche.fn_nuova_versione_definizione](/dbzero/pratiche/funzioni/fn_nuova_versione_definizione) — la strada per cambiare un'edizione emessa

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_template_flussi_guard_immutabile` congela la struttura dei template
di un'edizione forkata già emessa: modificarla vuol dire fare una nuova versione.

Si bloccano solo i fork di un emittente: il preset (senza emittente) e le bozze restano modificabili.

---

### ⭐ Congelare la modifica non è congelare la cancellazione

| Operazione | Bloccata quando | Predicato |
| --- | --- | --- |
| Inserimento | l'edizione è emessa, pubblicata o ritirata | `pratiche.fn_check_definizione_struttura_bloccata` |
| Modifica | l'edizione è emessa e cambia qualcosa oltre a `descrizione` | `pratiche.fn_check_definizione_struttura_bloccata` |
| Cancellazione | l'edizione è pubblicata, cioè in uso | `pratiche.fn_check_definizione_congelata` |

Un'edizione ritirata non si modifica, perché ha ancora pratiche fissate alla sua versione, ma si
cancella: è pulizia. `descrizione` è l'unico campo display correggibile a caldo, su pubblicata e
ritirata. Le due verità stanno nei predicati: questo guard non ripete le regole su stato ed emittente.

---

### Le regole

* Scatta `BEFORE INSERT OR UPDATE OR DELETE`, riga per riga, su `pratiche.template_flussi`, nella fase
  dei guard, dopo il trigger che risolve l'edizione di default su un inserimento.
* ⭐ **La modifica si confronta per esclusione.** Si confronta la riga intera meno `descrizione` e le
  colonne tecniche di audit e transazione: una colonna strutturale aggiunta domani è congelata di
  default, e una futura colonna display va esclusa esplicitamente.
* **Spostare un template d'edizione** è bloccato se è emessa l'edizione di partenza o quella di arrivo:
  uno step non entra né esce da un'edizione emessa.
* Per cambiare un fork emesso si crea una nuova versione in bozza, la si modifica e la si pubblica,
  ritirando la precedente; le pratiche in corso restano sulla loro edizione.
* Per smantellare un fork pubblicato lo si ritira prima: da ritirato, template e figli si cancellano.

---

### Codici errore

* `E_TEMPLATE_DEFINIZIONE_CONGELATA` — scrittura vietata su un template di un'edizione emessa, o
  cancellazione da un'edizione pubblicata.

---

### Test

* `pratiche/test-workflow-definizioni-fase2b` — inserimento, modifica, correzione della descrizione,
  spostamento e cancellazione su un'edizione pubblicata.
* `pratiche/test-definizione-ritirata-edit-freeze` — su un'edizione ritirata la modifica è bloccata e la
  cancellazione consentita.

---

### Note di migrazione

* 2026-07-03 — nasce l'immutabilità «leggera» della struttura: si congelano solo le edizioni forkate,
  il preset resta modificabile dai seed.
* 2026-07-04 — modifica e cancellazione si separano: un'edizione ritirata non si modifica ma si
  cancella.

---

{% include-markdown "signature-core.md" %}
