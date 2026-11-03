## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_pipeline_task_implementation`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.pipeline_task_registry](/dbzero/dbops/tabelle/pipeline_task_registry) — il task
> * [dbops.pipeline_task_registry_impl](/dbzero/dbops/tabelle/pipeline_task_registry_impl) — le varianti fra cui sceglie
> * [dbops.domini_task](/dbzero/dbops/tabelle/domini_task) — il dominio
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_pipeline_task_registered](/dbzero/dbops/funzioni/fn_check_pipeline_task_registered) — la verifica che fa per prima
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la primitiva con cui rifiuta

---

### 🎯 Scopo Principale

Risolve l'implementazione di un task di pipeline: dato il dominio, il codice del task e, se c'è, la
variante chiesta, restituisce il codice dell'handler da eseguire, la variante scelta e il task. È la
funzione con cui il backend trova l'handler prima di eseguire ogni task di uno step.

---

### Come sceglie

1. Prima verifica che il task sia registrato e attivo in un dominio attivo
   (`dbops.fn_check_pipeline_task_registered`): se non lo è, si ferma con l'errore di quella.
2. Se è stata chiesta una variante, prova quella, purché attiva.
3. Altrimenti, **e anche quando la variante chiesta non esiste o è spenta**, usa la variante di
   default attiva.
4. Se non c'è un default attivo, rifiuta.

⚠️ Il ripiego del punto 3 è silenzioso: chi chiede una variante che non c'è riceve il default,
senza errore e senza traccia. Chi chiama sa quale variante è stata usata solo leggendo la colonna
della variante nel risultato.

⚠️ Il punto 2 e il punto 3 non ricontrollano il dominio: lo ha già fatto la verifica del punto 1.

---

### Codici errore

* `E_GENERICO` — dominio non indicato, codice del task vuoto, nessuna implementazione di default
  attiva; e, attraverso la verifica del punto 1, task non registrato o spento.

---

### Test

* `db/pgtap/dbops/test-pipeline-task-registry.sql`, test 5, 6 e 8 — la variante chiesta, il ripiego
  sul default, l'errore senza default.
* `db/pgtap/vendite/test-seed-pull-commessa-pipeline-v1.sql` e
  `test-pipeline-consuma-plafond-seed-v1.sql` — un task del dominio `FATTURAZIONE` si risolve dal
  suo seed come lo risolve il backend.

---

{% include-markdown "signature-core.md" %}
