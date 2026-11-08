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
| dbdev e installazioni | il job pgAgent `sync_storico_set_storicizza`, step `run_sync_storico_set_storicizza` | ogni sabato alle 07:00, cinque minuti prima dell'apply |
| CI e scratch | la convergenza dei job strutturali (passata `ci_apply`) | in ordine `ci_ordine` 100, prima dell'apply (110) |

Lo step pgAgent chiama la procedura solo se
`maintenance.fn_sveglia_accesa('sync_storico_set_storicizza')` è vero: a sveglia spenta il
lavoro non parte, e il giornale non scrive niente.

⭐ L'ordine è lo stesso nelle due strade: prima il sync allinea l'insieme, poi l'apply lo consuma.
Così una tabella nuova riceve il default nello stesso giro in cui entra nell'insieme.

---

### Un nome solo per lo step

Lo step del job pgAgent e lo step registrato nel giornale si chiamano tutti e due
`run_sync_storico_set_storicizza`. Le corse di questo lavoro si riconoscono dal nome del job,
`sync_storico_set_storicizza`, che è anche il codice del processo in `dbops.processi`: è così che
il giornale risale al processo.

---

### Che cosa resta nel giornale

* **Corsa riuscita** — la riga si chiude con esito positivo e messaggio «done». Il lavoro è una
  `CALL`, che non restituisce un risultato: la corsa non ha esito in `meta`, e il numero di righe
  registrato è quello dell'istruzione eseguita, non il numero di righe aggiunte o potate, che la
  procedura dice solo nel suo riepilogo al client.
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
* `db/pgtap/dbops/test-pgagent-storicizza-ordine-v1.sql` — su pgAgent la sveglia del sync viene
  prima di quella dell'apply, nello stesso ordine della convergenza (in skip dove pgAgent non è
  installato).

---

### Note di migrazione

* 2026-01-07 — nasce nello schema `maintenance`.
* 2026-09-05 — `fn_run_and_log` scrive il verbale di un fallimento fuori transazione: prima lo
  annullava insieme al lavoro, e un job fallito risultava «done»
  (`brief-db-storicizzazione-bersagli-spariti`, R-12).
* 2026-10-14 — diventa `SECURITY DEFINER` con `search_path` fissato, come tutte le
  `maintenance.proc_*_job` (`brief-db-ruoli-di-sistema`).
* 2026-11-03 — il job pgAgent passa alle 07:00 del sabato, prima dell'apply delle 07:05: prima
  girava cinque minuti dopo, e l'apply consumava l'insieme della settimana precedente. Lo step
  pgAgent prende il nome che il giornale registra, `run_sync_storico_set_storicizza` (prima
  `run_apply_storicizza`, copiato dall'apply), e la descrizione del job dice che cosa fa il sync
  invece di ripetere quella dell'apply (`brief-db-revisione-maintenance` D7, M1, M2).

---

{% include-markdown "signature-core.md" %}
