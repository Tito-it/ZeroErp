## 📘 Documentazione Concettuale – Funzione `pratiche.fn_check_definizione_congelata`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni del workflow
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_definizione_struttura_bloccata](/dbzero/pratiche/funzioni/fn_check_definizione_struttura_bloccata) — il predicato più ampio, per le modifiche
> * [pratiche.trgfn_template_flussi_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_immutabile) · [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — i guard che lo usano
> * [pratiche.fn_nuova_versione_definizione](/dbzero/pratiche/funzioni/fn_nuova_versione_definizione) — la strada per cambiare la struttura di un'edizione in uso
> * [pratiche.fn_pubblica_definizione](/dbzero/pratiche/funzioni/fn_pubblica_definizione) — la pubblicazione che congela un fork

---

### 🎯 Scopo Principale

`pratiche.fn_check_definizione_congelata` è un predicato puro che risponde a una domanda sola: questa
edizione del workflow è congelata, cioè in uso e non cancellabile?

È vero se e solo se l'edizione è un fork di un emittente (`emittente_fiscale_id` valorizzato) ed è in
stato `PUBBLICATA`.

---

### Che cosa governa

Nell'immutabilità «leggera» delle definizioni questo predicato governa la **cancellazione**: un'edizione
in uso non si smantella. Le **modifiche** della struttura le governa il predicato più ampio,
`pratiche.fn_check_definizione_struttura_bloccata` (pubblicata o ritirata).

| Edizione | Congelata? | Che cosa ne segue |
| --- | --- | --- |
| Preset di fabbrica (senza emittente), in qualsiasi stato | No | Resta modificabile da seed e migrazioni |
| Fork `BOZZA` | No | Modificabile e cancellabile |
| Fork `PUBBLICATA` | **Sì** | Né cancellabile né modificabile |
| Fork `RITIRATA` | No | Cancellabile, ma non modificabile: ha ancora pratiche legate |

Per smantellare un fork lo si porta a `RITIRATA`; per cambiarne la struttura si crea una nuova versione
in bozza con `pratiche.fn_nuova_versione_definizione`.

---

### Il predicato non decide

Non solleva mai: la decisione di bloccare è dei guard che lo chiamano, oggi i due guard di
immutabilità dei template di flusso e delle loro tabelle figlie. Lo possono chiamare anche viste e
backend, per dire «modificabile sì o no» senza riscrivere la regola.

Un'edizione assente o inesistente dà `false`: la coerenza referenziale la garantiscono già le FK.

---

### Test

* `pratiche/test-workflow-definizioni-fase2b` — il fork pubblicato congelato, il preset e le bozze no.
* `pratiche/test-definizione-ritirata-edit-freeze` — l'edizione ritirata: cancellabile, ma non
  modificabile.

---

### Note di migrazione

* 2026-07-03 — nasce con l'immutabilità «leggera» delle definizioni di workflow.

---

{% include-markdown "signature-core.md" %}
