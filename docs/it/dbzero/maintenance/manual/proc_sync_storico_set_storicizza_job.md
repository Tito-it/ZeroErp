## 📘 Documentazione Concettuale – Procedura `maintenance.proc_sync_storico_set_storicizza_job`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `sync_storico_set_storicizza` e il suo posto nella convergenza di CI
> * [config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza) — l'insieme che il lavoro tiene allineato
>
> Approfondimento funzioni:
>
> * [maintenance.proc_sync_storico_set_storicizza](/dbzero/maintenance/funzioni/proc_sync_storico_set_storicizza) — il lavoro vero
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale e il lock da cui passa la chiamata
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent

---

### 🎯 Scopo Principale

Il wrapper del job `sync_storico_set_storicizza`: esegue
`maintenance.proc_sync_storico_set_storicizza` passando dal giornale delle esecuzioni, con un
lock che impedisce due corse sovrapposte.

La procedura non aggiunge logica: delega tutto a `maintenance.fn_run_and_log`, che registra la
corsa in `maintenance.job_run_log`, esegue il lavoro e chiude la riga con l'esito. Non apre né
chiude transazioni: segue quella del chiamante.

---

### Due strade, la stessa procedura

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni | il job pgAgent `sync_storico_set_storicizza` | ogni sabato alle 07:05, cinque minuti dopo l'apply |
| CI e scratch | la convergenza dei job strutturali (passata `ci_apply`) | in ordine `ci_ordine` 100, prima dell'apply (110) |

Lo step pgAgent chiama la procedura solo se
`maintenance.fn_sveglia_accesa('sync_storico_set_storicizza')` è vero: a sveglia spenta il
lavoro non parte, e il giornale non scrive niente.

---

### ⚠️ Lo step ha due nomi

Lo step del job pgAgent si chiama `run_apply_storicizza`, lo stesso nome dello step del job
dell'apply. Nel giornale, invece, lo step registrato è `run_sync_storico_set_storicizza`. Le
corse di questo lavoro si riconoscono dal nome del job, `sync_storico_set_storicizza`, che è
anche il codice del processo in `dbops.processi`: è così che il giornale risale al processo.

---

### Che cosa resta nel giornale

* **Corsa riuscita** — la riga si chiude con esito positivo e messaggio «done». Il numero di
  righe registrato è quello dell'istruzione eseguita, cioè della chiamata alla procedura: non è
  il numero di righe aggiunte o potate, che la procedura dice solo nel suo riepilogo al client.
* **Corsa fallita** — il verbale è scritto **fuori transazione** (con
  `maintenance.fn_job_run_log_failure`) e l'errore viene **rilanciato**: lo step pgAgent
  fallisce. Il lavoro si annulla, il verbale resta.
* **Lock occupato** — se un'altra corsa tiene il lock, il lavoro non parte e resta una riga
  **saltata**, chiusa e senza esito.

Il dettaglio del meccanismo è nella scheda di `fn_run_and_log`.

---

### Gira come il proprietario

La procedura è `SECURITY DEFINER`, con `search_path` fissato, e appartiene a `zeroerp_owner`,
come tutte le `maintenance.proc_*_job`. Chiunque la chiami — `zeroerp_job` dallo step pgAgent,
la convergenza in CI — la sincronizzazione legge il catalogo e scrive l'insieme come
`zeroerp_owner`. Il giornale registra come ruolo della sessione chi si è collegato.

---

### Test

* `db/pgtap/maintenance/test-storicizza-set-potatura.sql` — la procedura sottostante: che cosa
  si aggiunge, che cosa si pota e che cosa no.
* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome passato dal wrapper esiste in
  `dbops.processi`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la procedura dichiarata esiste, ha girato
  sul database con esito positivo, e nella convergenza viene prima dell'apply.

---

### Note di migrazione

* 2026-01-07 — nasce nello schema `maintenance`.
* 2026-09-05 — `fn_run_and_log` scrive il verbale di un fallimento fuori transazione: prima lo
  annullava insieme al lavoro, e un job fallito risultava «done»
  (`brief-db-storicizzazione-bersagli-spariti`, R-12).
* 2026-10-14 — diventa `SECURITY DEFINER` con `search_path` fissato, come tutte le
  `maintenance.proc_*_job` (`brief-db-ruoli-di-sistema`).

---

{% include-markdown "signature-core.md" %}
