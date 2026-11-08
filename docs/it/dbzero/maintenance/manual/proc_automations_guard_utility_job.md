## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_guard_utility_job`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `automations_guard_utility`: job pgAgent, procedura e posto nella convergenza del rilascio
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
> * [dbops.automazione_guard_utility_tipo_ruolo](/dbzero/dbops/tabelle/automazione_guard_utility_tipo_ruolo) — il registro: le tabelle da proteggere e le loro due colonne
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il calendario vivo e lo stato del processo
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove una corsa fallita diventa una cosa da guardare
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_guard_utility](/dbzero/dbops/funzioni/fn_run_automations_guard_utility) — il lavoro vero: il guard portato allo stato del registro
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa la chiamata, col lock e il verbale del fallimento
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
>
> Guide:
>
> * [Framework di Automazione DB](/guide/automazione-db) — la regola GUARD utility/tipo ruolo
> * [Framework di Automazione DB, §9](/guide/automazione-db#9-quando-girano-le-automazioni) — quando girano le automazioni

---

### 🎯 Scopo Principale

Il wrapper del processo `automations_guard_utility`: esegue
`dbops.fn_run_automations_guard_utility` su tutto l'ambito, e così porta il guard utility/tipo
ruolo allo stato che dichiara `dbops.automazione_guard_utility_tipo_ruolo`, passando dal giornale
delle esecuzioni sotto il codice del processo.

La procedura non aggiunge logica: delega a `maintenance.fn_run_and_log`, che apre la riga della
corsa in `maintenance.job_run_log`, esegue il runner e chiude la riga con l'esito. Che cosa fa il
runner, e quando si ferma, sta nella sua pagina.

---

### ⭐ Un processo come le altre automazioni

Prima il guard girava solo nel primo giro di `ci_apply`: non compariva nel panorama dei processi,
e una tabella aggiunta al registro fra due migrazioni restava senza guard fino alla migrazione
dopo. Ora è un processo del catalogo, con la sua sveglia notturna e il suo posto nella
convergenza.

---

### Due strade, la stessa procedura

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni con pgAgent | il job `automations_guard_utility`, step `run_automations_guard_utility` | ogni giorno alle 21:10, con il blocco delle cancellazioni |
| CI, database ricostruito da zero, ogni migrazione di sviluppo | la convergenza del rilascio (passata `ci_apply`) | `ci_ordine` 75: dopo `automations_delete_block`, prima di `automations_overlap` |

Lo step pgAgent chiama la procedura solo se `maintenance.fn_sveglia_accesa('automations_guard_utility')`
è vero: a processo spento il giro programmato non parte e il giornale non scrive niente. La
convergenza invece gira sempre, e dopo la chiamata pretende nel giornale una riga riuscita di quel
giro, che non sia un salto; altrimenti la migrazione si ferma nominando il processo.

⚠️ In CI il job non esiste (`85_pgagent` finisce `MARK_RAN`): lì il lavoro lo fa solo la
convergenza.

---

### Una corsa, una riga nel giornale

Il meccanismo è quello di `maintenance.fn_run_and_log`, e la sua scheda lo racconta per intero:

* **Il nome della corsa è il codice del processo**, `automations_guard_utility`: così il giornale
  risale alla riga di `dbops.processi`. Il job pgAgent ha lo stesso nome.
* **Una corsa alla volta**, con un advisory lock sull'hash del codice: una seconda corsa
  concorrente lascia una riga saltata.
* **Un fallimento si propaga, e il verbale resta**, scritto fuori transazione; la riga rossa porta
  il codice del runner (`E_GUARD_UTILITY`) o, per un guasto dell'ambiente, lo SQLSTATE.
* **Gira come il proprietario.** La procedura è `SECURITY DEFINER`, con `search_path` fissato,
  senza `EXECUTE` a `PUBLIC`: l'`EXECUTE` a `zeroerp_job` lo dà il provisioning, come alle altre
  procedure dei job.

---

### `SCHEDULED`, tutto l'ambito, mai in simulazione

La procedura chiama il runner in modo `SCHEDULED`, senza schemi (l'ambito lo risolve
`dbops.fn_resolve_scope`) e senza simulazione. Una riga del registro gira se il suo `exec_mode` è
`AUTO` o `SCHEDULED`. Per sapere che cosa farebbe un giro si chiama il runner con la simulazione
accesa.

---

### Codici errore

La procedura non ne solleva di suoi: l'errore è del runner, e arriva com'è.

* `E_GUARD_UTILITY` — un guard su una tabella che il registro non nomina, o un DDL fallito.

---

### Test

* `db/pgtap/dbops/test-guard-utility-convergenza-v1.sql` — il processo è nella catena della
  convergenza, fra `automations_delete_block` e `automations_overlap`.
* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la procedura dichiarata esiste e ha girato
  con esito positivo sul database.

---

### Note di migrazione

* 2026-11-08 — nasce, con il processo `automations_guard_utility` in `dbops.processi` e il job
  pgAgent delle 21:10 (`20261110-04`, `20261110-05`, `brief-db-revisione-dbops`, giro 10c).

---

{% include-markdown "signature-core.md" %}
