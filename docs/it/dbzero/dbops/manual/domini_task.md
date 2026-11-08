## 📘 Documentazione Concettuale – Tabella `dbops.domini_task`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.pipeline_task_registry](/dbzero/dbops/tabelle/pipeline_task_registry) — i task ammessi in ciascun dominio
> * [dbops.pipeline_task_registry_impl](/dbzero/dbops/tabelle/pipeline_task_registry_impl) — le implementazioni di ogni task
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — dove il lock del `codice` è dichiarato
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_pipeline_task_registered](/dbzero/dbops/funzioni/fn_check_pipeline_task_registered) — pretende anche il dominio attivo
> * [dbops.fn_get_pipeline_task_implementation](/dbzero/dbops/funzioni/fn_get_pipeline_task_implementation) — risolve l'handler di un task del dominio
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il lock che rende il `codice` non modificabile
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — §4.1, il lock di colonna e l'eccezione delle tabelle fuori dall'ambito

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

### ⛔ Il `codice` non si cambia

Il `codice` di un dominio è una chiave di sistema: il backend risolve il dominio per codice.
Una modifica la rifiuta il trigger `trg_domini_task_a10_lock_columns_upd`, su
`script.trgfn_lock_columns`, con `E_CODICE_NON_MODIFICABILE`.

⚠️ Il lock **lo monta una migrazione**, non il giro delle automazioni. La tabella è fuori
dall'ambito delle automazioni, e il runner dei lock non ci arriva; farla entrare le porterebbe
anche tutte le altre automazioni. Il lock resta comunque dichiarato in
`dbops.automation_lock_columns`, e il trigger ha il nome e gli argomenti che monterebbe il runner.
Che dichiarazione e lock vivo restino uguali lo controlla il presidio dei lock fuori dall'ambito
(vedi sotto).

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
* `db/pgtap/dbops/test-lock-columns-convergenza.sql` — fuori dall'ambito ogni lock è dichiarato
  nel registro con lo stesso codice (test 23), e ogni riga attiva del registro ha il suo lock vivo,
  abilitato, con la colonna nell'`UPDATE OF` (test 30): è il caso di questa tabella.

---

### Note di migrazione

* 2026-02-08 — nasce con il registro multi-dominio dei task di pipeline.
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).
* 2026-11-08 — il lock del `codice` lo monta una migrazione (`20261109-94`,
  brief-db-revisione-dbops, giro 10b). Prima la riga di `dbops.automation_lock_columns` lo
  dichiarava, ma il runner non arrivava sulla tabella e il codice restava modificabile.

---

{% include-markdown "signature-core.md" %}
