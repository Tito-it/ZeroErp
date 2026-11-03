## 📘 Documentazione Concettuale – Procedura `maintenance.proc_apply_storicizza_defaults_job`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `apply_storicizza_weekly` e il suo posto nella convergenza di CI
>
> Approfondimento funzioni:
>
> * [maintenance.proc_apply_storicizza_defaults](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults) — il lavoro vero
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale e il lock da cui passa la chiamata
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la colonna `storicizza` e il registro delle tabelle a storicizzazione permanente

---

### 🎯 Scopo Principale

Il wrapper del job `apply_storicizza_weekly`: esegue `maintenance.proc_apply_storicizza_defaults`
passando dal giornale delle esecuzioni, con un lock che impedisce due corse sovrapposte.

La procedura non aggiunge logica: delega tutto a `maintenance.fn_run_and_log`, che registra la
corsa in `maintenance.job_run_log`, esegue il lavoro e chiude la riga con l'esito.

---

### Due strade, la stessa procedura

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni | il job pgAgent `apply_storicizza_weekly`, step `run_apply_storicizza` | ogni sabato alle 07:00 |
| CI e scratch | la convergenza dei job strutturali (passata `ci_apply`) | in ordine `ci_ordine` 110, dopo il sync dell'insieme (100) |

Lo step pgAgent chiama la procedura solo se
`maintenance.fn_sveglia_accesa('apply_storicizza_weekly')` è vero: a sveglia spenta il lavoro
non parte, e il giornale non scrive niente.

⚠️ Su pgAgent l'ordine con il sync è l'opposto di quello della CI: l'apply gira cinque minuti
**prima** del sync settimanale. Perché la procedura regge lo stesso, lo spiega la sua scheda.

---

### Che cosa resta nel giornale

Il nome del job registrato è `apply_storicizza_weekly`, che è anche il codice del processo in
`dbops.processi`: così il giornale risale al processo. Lo step registrato si chiama invece
`run_proc_apply_storicizza`, diverso dal nome dello step pgAgent: le corse si cercano per nome
del job.

* **Corsa riuscita** — la riga si chiude con esito positivo e messaggio «done». Le righe
  dell'insieme saltate o fallite non la rendono rossa: le racconta la procedura con un `WARNING`
  nel log del server.
* **Corsa fallita** — il verbale è scritto **fuori transazione** (con
  `maintenance.fn_job_run_log_failure`) e l'errore viene **rilanciato**: lo step pgAgent
  fallisce. Il lavoro si annulla, il verbale resta.
* **Lock occupato** — se un'altra corsa tiene il lock, il lavoro non parte e resta una riga
  **saltata**, chiusa e senza esito.

Il registro centrale degli errori è un'altra cosa: `dbops.error_log` raccoglie gli errori di
dominio sollevati con `script.fn_log_and_raise_error`. Il dettaglio di tutto il meccanismo è
nella scheda di `fn_run_and_log`.

---

### Gira come il proprietario

La procedura è `SECURITY DEFINER`, con `search_path` fissato, e appartiene a `zeroerp_owner`,
come tutte le `maintenance.proc_*_job`. Chiunque la chiami — `zeroerp_job` di notte, la
convergenza in CI — il cambio di default sulle tabelle gira come il loro proprietario. Il
giornale registra come ruolo della sessione chi si è collegato.

---

### Test

* `db/pgtap/maintenance/test-storicizza-set-potatura.sql` — la procedura sottostante non muore su
  una riga stantia.
* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome passato dal wrapper esiste in
  `dbops.processi`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la procedura dichiarata esiste, ha girato
  sul database con esito positivo, e nella convergenza viene dopo il sync dell'insieme.

---

### Note di migrazione

* 2026-01-05 — nasce nello schema `maintenance`, spostata insieme alla procedura che chiama.
* 2026-09-05 — `fn_run_and_log` scrive il verbale di un fallimento fuori transazione. Prima lo
  annullava insieme al lavoro, e questo job è risultato «done» per sei mesi mentre falliva ogni
  settimana (`brief-db-storicizzazione-bersagli-spariti`, R-12).
* 2026-10-14 — diventa `SECURITY DEFINER` con `search_path` fissato, come tutte le
  `maintenance.proc_*_job` (`brief-db-ruoli-di-sistema`).

---

{% include-markdown "signature-core.md" %}
