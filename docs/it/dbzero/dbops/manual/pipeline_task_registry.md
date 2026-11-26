## 📘 Documentazione Concettuale – Tabella `dbops.pipeline_task_registry`

> **Ultimo aggiornamento**: 24 novembre 2026
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

### Il task distruttivo non parte mai da solo

`distruttivo` dice che il task cancella o annulla dati che un rilancio non ricostruisce. È la
natura del task, la stessa in ogni pipeline che lo nomina; come il task gira in una corsia lo
dice invece `vendite.fatturazione_pipeline_task_policy`. Un task distruttivo messo nel `rollback`
di uno step non gira mai in automatico al rilancio di un lotto: `vendite.fn_check_rollback_step_automatico`
risponde false, e il rollback resta eseguibile solo su richiesta esplicita. Lo stesso vale per un task
spento o non registrato. Il default è false: chi registra un task che cancella dati lo dichiara.

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
* `db/pgtap/vendite/test-pipeline-processi-invariante-v1.sql`, test 6-7 e 8-9 — ogni task nominato nei
  processi e nel rollback delle pipeline esiste ed è attivo qui, e ha la sua policy attiva. È il file da lanciare
  dopo aver toccato le pipeline.
* `db/pgtap/vendite/test-rollback-step-automatico-v1.sql` — la colonna `distruttivo` e la decisione
  del rollback automatico, coi casi costruiti (distruttivo, spento, sconosciuto).
* `db/pgtap/vendite/test-pipeline-consuma-plafond-seed-v1.sql` — il task del consumo del plafond si
  risolve con la funzione che usa il backend.
* `db/pgtap/vendite/test-snapshot-indirizzi-fattura-v1.sql`, `test-stampa-coda-fondamenta-v1.sql` —
  il task dello snapshot indirizzi e quello della stampa sono registrati, con la loro implementazione.

---

### Note di migrazione

* 2026-02-08 — nasce con il registro multi-dominio. Il task `close_lotto` è spento dal 2026-02-18.
* 2026-11-24 — il task `reset_lotto_draft` è **cancellato**, con la sua implementazione e la sua
  policy (`80_data/changelog/20261123-67`): nessun percorso lo eseguiva, e il backend ne toglie
  l'handler. Non è spento come `close_lotto`, perché una riga spenta nominerebbe un handler che
  non esiste più.
* 2026-11-24 — nasce `distruttivo` (`00_schema/dbops/20261123-95`): il task che cancella dati
  lo dichiara il registro, e non più il runner per nome.
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).

---

{% include-markdown "signature-core.md" %}
