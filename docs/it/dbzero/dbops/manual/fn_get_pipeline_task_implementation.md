## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_pipeline_task_implementation`

> **Ultimo aggiornamento**: 7 novembre 2026
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
2. Se è stata chiesta una variante, restituisce quella, purché attiva; se non c'è, **nessuna
   riga**. Non ripiega sul default: chi chiede «la variante X» non riceve un'altra cosa senza
   saperlo. Che cosa fare di un risultato vuoto lo decide chi chiama (il backend solleva
   `E_PIPELINE_TASK_HANDLER_NOT_FOUND`).
3. Se la variante non è chiesta, usa la variante di default attiva.
4. Se non c'è un default attivo, rifiuta.

⚠️ Il punto 2 e il punto 3 non ricontrollano il dominio: lo ha già fatto la verifica del punto 1.

---

### Codici errore

* `E_PIPELINE_TASK_HANDLER_NOT_FOUND` — nessuna implementazione di default attiva, quando la
  variante non è chiesta; e, attraverso la verifica del punto 1, task non registrato o spento.
  Dominio e task sono nel dettaglio.
* `E_DBOPS_CHIAMATA_NON_VALIDA` — dominio non indicato o codice del task vuoto: lo produce solo un
  chiamante rotto.

---

### Test

* `db/pgtap/dbops/test-pipeline-task-registry.sql`, test 5, 6, 8, 9 e 10 — la variante chiesta,
  la variante assente che non restituisce righe, l'errore senza default, il default senza
  variante, il dominio mancante.
* `db/pgtap/vendite/test-seed-pull-commessa-pipeline-v1.sql` e
  `test-pipeline-consuma-plafond-seed-v1.sql` — un task del dominio `FATTURAZIONE` si risolve dal
  suo seed come lo risolve il backend.

---

### Note di migrazione

* 2026-11-07 — una variante chiesta e assente non ripiega più sul default; i rifiuti hanno un
  codice al posto di `E_GENERICO` (`brief-db-revisione-dbops`, giro 2).

---

{% include-markdown "signature-core.md" %}
