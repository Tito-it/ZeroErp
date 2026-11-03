## 📘 Documentazione Concettuale – Funzione `dbops.fn_check_pipeline_task_registered`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.pipeline_task_registry](/dbzero/dbops/tabelle/pipeline_task_registry) — dove cerca il task
> * [dbops.domini_task](/dbzero/dbops/tabelle/domini_task) — il dominio, che deve essere attivo anche lui
>
> Approfondimento funzioni:
>
> * [dbops.fn_get_pipeline_task_implementation](/dbzero/dbops/funzioni/fn_get_pipeline_task_implementation) — la chiama prima di risolvere l'handler
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la primitiva con cui rifiuta

---

### 🎯 Scopo Principale

Verifica che un task sia registrato **e attivo** in un dominio **attivo**. Risponde vero, oppure
solleva un errore: non risponde mai falso.

---

### La regola

Per passare servono, insieme:

* un dominio indicato (identificativo positivo) e un codice di task non vuoto;
* una riga del registro per quel dominio e quel codice, con `attivo` acceso;
* il dominio stesso con `attivo` acceso.

Manca una delle tre cose → errore. Un task spento e un task mai registrato danno lo stesso esito.

Il suo chiamante è `dbops.fn_get_pipeline_task_implementation`, cioè la risoluzione che il backend
fa prima di eseguire ogni task.

---

### Codici errore

* `E_GENERICO` — per tutti e tre i rifiuti: dominio non indicato, codice del task vuoto, task non
  registrato o spento (o dominio spento). Il dettaglio del log distingue i casi; il codice no.

---

### Test

* `db/pgtap/dbops/test-pipeline-task-registry.sql`, test 4 e 7 — un task registrato passa, un
  task assente solleva.

---

{% include-markdown "signature-core.md" %}
