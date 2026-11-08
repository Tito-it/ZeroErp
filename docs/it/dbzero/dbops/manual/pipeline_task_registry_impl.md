## 📘 Documentazione Concettuale – Tabella `dbops.pipeline_task_registry_impl`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.pipeline_task_registry](/dbzero/dbops/tabelle/pipeline_task_registry) — il task di cui la riga è un'implementazione
> * [dbops.domini_task](/dbzero/dbops/tabelle/domini_task) — il dominio del task
>
> Approfondimento funzioni:
>
> * [dbops.fn_get_pipeline_task_implementation](/dbzero/dbops/funzioni/fn_get_pipeline_task_implementation) — sceglie l'implementazione da usare

---

### 🎯 Scopo Principale

Le **implementazioni consentite** di ciascun task di pipeline: per ogni task una o più varianti,
ognuna col codice dell'handler applicativo che la esegue. Le varianti si scelgono da un elenco
chiuso, non con un dispatch libero.

---

### Variante, handler, default

* `implementation_key` è il nome della variante, unico dentro il task (oggi ogni task ha la sola
  variante `default`);
* `handler_code` è l'identificativo con cui il backend trova il codice da eseguire: il database
  non lo interpreta, il dispatch vero avviene in Python, su un registro statico di handler;
* `is_default` marca la variante che si usa quando nessuno ne chiede un'altra. Il database ammette
  **al più una** variante di default per task (indice unico parziale);
* `attivo` spegne la variante.

⚠️ Un task la cui variante di default è spenta non ha implementazione: la risoluzione fallisce
anche se il task è attivo. È la forma del task `close_lotto`, spento insieme alla sua
implementazione.

---

### Dove nascono le righe

Dal seed `pipeline_task_registry_impl.csv` in `80_data`, una riga per ogni task del registro.
Un task registrato senza la sua implementazione muore al primo giro dello step che lo contiene.

---

### Test

* `db/pgtap/dbops/test-pipeline-task-registry.sql` — la variante chiesta si risolve, una variante
  inesistente ricade sul default, e senza default la risoluzione fallisce.

---

### Note di migrazione

* 2026-02-08 — nasce con il registro multi-dominio dei task di pipeline.
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).

---

{% include-markdown "signature-core.md" %}
