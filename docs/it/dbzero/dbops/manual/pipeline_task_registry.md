## 📘 Documentazione Concettuale – Tabella `dbops.pipeline_task_registry`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.domini_task](/dbzero/dbops/tabelle/domini_task) — il dominio di ogni task
> * [dbops.pipeline_task_registry_impl](/dbzero/dbops/tabelle/pipeline_task_registry_impl) — le implementazioni di ogni task
> * [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline) — le pipeline che nominano i task nei loro processi
> * [vendite.fatturazione_pipeline_task_policy](/dbzero/vendite/tabelle/fatturazione_pipeline_task_policy) — come gira un task dentro una pipeline
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_pipeline_task_registered](/dbzero/dbops/funzioni/fn_check_pipeline_task_registered) — la verifica «registrato e attivo»
> * [dbops.fn_get_pipeline_task_implementation](/dbzero/dbops/funzioni/fn_get_pipeline_task_implementation) — la risoluzione dell'handler

---

### 🎯 Scopo Principale

Il catalogo dei **task ammessi** per ciascun dominio di pipeline: un task che non è qui, o che è
spento, non si esegue. Il motore applicativo risolve ogni task da qui prima di eseguirlo, e
l'implementazione concreta la prende da `dbops.pipeline_task_registry_impl`.

---

### La chiave è (dominio, codice del task)

`task_code` è il nome con cui una pipeline nomina il task nei suoi processi; è unico dentro il
dominio. `attivo` spegne il task: la verifica del registro lo dà per non registrato, e lo step che
lo contiene si ferma lì.

---

### ⛔ Nessun vincolo lega le pipeline al registro

Le pipeline di fatturazione nominano i task per nome, dentro un campo JSON: non c'è una chiave
esterna verso questa tabella. Un task nominato in una pipeline e assente qui passa la migrazione
senza errori, e il difetto arriva **a runtime**, al primo giro: l'executor non trova l'handler.

Armare un task in una pipeline vuol dire quindi scrivere **tre** seed: il task nei processi della
pipeline, la sua riga qui con l'implementazione, e la sua policy di esecuzione. Il presidio che li
tiene insieme è un test, non un vincolo (sotto).

---

### Test

* `db/pgtap/dbops/test-pipeline-task-registry.sql` — la verifica e la risoluzione su un dominio di
  prova.
* `db/pgtap/vendite/test-pipeline-processi-invariante-v1.sql`, test 6 e 7 — ogni task nominato nei
  processi delle pipeline esiste ed è attivo qui, e ha la sua policy attiva. È il file da lanciare
  dopo aver toccato le pipeline.
* `db/pgtap/vendite/test-pipeline-consuma-plafond-seed-v1.sql` — il task del consumo del plafond si
  risolve con la funzione che usa il backend.
* `db/pgtap/vendite/test-snapshot-indirizzi-fattura-v1.sql`, `test-stampa-coda-fondamenta-v1.sql` —
  il task dello snapshot indirizzi e quello della stampa sono registrati, con la loro implementazione.

---

### Note di migrazione

* 2026-02-08 — nasce con il registro multi-dominio. Il task `close_lotto` è spento dal 2026-02-18.

---

{% include-markdown "signature-core.md" %}
