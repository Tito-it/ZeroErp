## 📘 Documentazione Concettuale – Tabella `dbops.domini_task`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.pipeline_task_registry](/dbzero/dbops/tabelle/pipeline_task_registry) — i task ammessi in ciascun dominio
> * [dbops.pipeline_task_registry_impl](/dbzero/dbops/tabelle/pipeline_task_registry_impl) — le implementazioni di ogni task
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_pipeline_task_registered](/dbzero/dbops/funzioni/fn_check_pipeline_task_registered) — pretende anche il dominio attivo
> * [dbops.fn_get_pipeline_task_implementation](/dbzero/dbops/funzioni/fn_get_pipeline_task_implementation) — risolve l'handler di un task del dominio

---

### 🎯 Scopo Principale

I **domini** del registro dei task di pipeline: il perimetro dentro cui un codice di task è unico.
Lo stesso codice può esistere in due domini diversi, e dentro un dominio una volta sola.

Oggi i domini sono due: `FATTURAZIONE` (i task degli step del lotto di fatturazione) e
`ATTIVITA_FATTURABILI` (i task che acquisiscono e normalizzano le attività da fatturare).

---

### Il dominio si spegne con `attivo`

Un dominio spento spegne tutti i suoi task: la verifica del registro pretende **sia** il task
**sia** il dominio attivi, e un task di un dominio spento risulta non registrato.

Il backend risolve il dominio per `codice` e lavora poi con il suo `id`; `meta` è un'estensione
libera, oggi vuota.

---

### Dove nascono le righe

Dal seed `domini_task.csv` in `80_data`. Un dominio nuovo è una riga lì, più i suoi task e le loro
implementazioni negli altri due seed del registro.

---

### Test

* `db/pgtap/dbops/test-pipeline-task-registry.sql` — costruisce un dominio di prova con il suo task
  e le sue implementazioni, e prova la verifica e la risoluzione.
* `db/pgtap/vendite/test-seed-pull-commessa-pipeline-v1.sql` — il task del pull da commessa si
  risolve nel dominio `FATTURAZIONE`.

---

### Note di migrazione

* 2026-02-08 — nasce con il registro multi-dominio dei task di pipeline.

---

{% include-markdown "signature-core.md" %}
