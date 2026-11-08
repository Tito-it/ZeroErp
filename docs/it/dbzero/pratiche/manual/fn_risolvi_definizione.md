## 📘 Documentazione Concettuale – Funzione `pratiche.fn_risolvi_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni del workflow, per tipo di prestazione e scope
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_pratiche_default_definizione](/dbzero/pratiche/funzioni/trgfn_pratiche_default_definizione) — l'aggancio automatico della pratica alla sua edizione
> * [pratiche.trgfn_template_flussi_default_definizione](/dbzero/pratiche/funzioni/trgfn_template_flussi_default_definizione) — l'edizione predefinita di un template
> * [pratiche.trgfn_tipi_prestazione_bootstrap_definizione](/dbzero/pratiche/funzioni/trgfn_tipi_prestazione_bootstrap_definizione) — il preset che nasce con il tipo di prestazione
> * [pratiche.fn_fork_definizione](/dbzero/pratiche/funzioni/fn_fork_definizione) — l'edizione di un emittente

---

### 🎯 Scopo Principale

`pratiche.fn_risolvi_definizione` è il punto unico che decide quale edizione di workflow vale per un
tipo di prestazione e uno scope di emittente, e ne ritorna l'id.

---

### La catena di risoluzione

1. L'edizione `PUBBLICATA` dell'emittente, se l'emittente è indicato e ne ha una (un fork).
2. Altrimenti il preset `PUBBLICATA`, quello senza emittente.
3. Altrimenti l'errore `E_DEFINIZIONE_NON_TROVATA`.

Senza emittente la funzione risolve solo il preset.

---

### Chi la usa

* L'aggancio automatico delle pratiche (`pratiche.trgfn_pratiche_default_definizione`), con l'emittente
  della pratica.
* L'edizione predefinita dei template (`pratiche.trgfn_template_flussi_default_definizione`), senza
  emittente: il preset.

Per un tipo di prestazione reale l'errore non dovrebbe scattare: il preset nasce col tipo, attraverso
`pratiche.trgfn_tipi_prestazione_bootstrap_definizione`.

---

### ⚠️ È `VOLATILE`, non `STABLE`

Il ramo d'errore scrive il registro attraverso `script.fn_log_and_raise_error`, e una funzione non
volatile non può scrivere.

---

### Codici errore

* `E_DEFINIZIONE_NON_TROVATA` — sia per un tipo di prestazione assente o non positivo, sia quando non
  c'è nessuna edizione pubblicata. Il contesto dell'errore distingue i due motivi.

---

### Test

* `pratiche/test-workflow-definizioni-fase0` — la risoluzione sul preset e l'errore senza edizioni
  pubblicate.

---

{% include-markdown "signature-core.md" %}
