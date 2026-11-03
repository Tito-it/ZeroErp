## 📘 Documentazione Concettuale – Funzione `maintenance.fn_run_and_log`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui scrive la corsa
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il registro da cui deriva il processo della corsa
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove si guardano le corse fallite e appese
> * [maintenance.vw_job_run_da_superuser](/dbzero/maintenance/views/vw_job_run_da_superuser) — il presidio sul ruolo che si è collegato
>
> Approfondimento funzioni:
>
> * [maintenance.fn_job_run_log_failure](/dbzero/maintenance/funzioni/fn_job_run_log_failure) — il verbale del fallimento, scritto fuori transazione
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il contratto da cui si legge il codice di dominio
> * [script.fn_job_run_start](/dbzero/script/funzioni/fn_job_run_start) — la porta gemella, per i lavori del backend
> * [maintenance.proc_analyze_statistiche_job](/dbzero/maintenance/funzioni/proc_analyze_statistiche_job) — un esempio dei wrapper `proc_*_job` che la chiamano
>
> Guide:
>
> * [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — i lavori a orario e dove si tracciano

---

### 🎯 Scopo Principale

Esegue il lavoro di un job del database e ne registra la corsa nel giornale
`maintenance.job_run_log`: apre la riga, esegue l'istruzione, la chiude con l'esito. Se il
lavoro fallisce, scrive il verbale del fallimento in un posto che l'annullamento non
raggiunge, e poi rilancia l'errore.

La chiamano i wrapper `maintenance.proc_*_job`, che sono ciò che pgAgent, la convergenza
del rilascio e chi lavora a mano lanciano. È una delle porte di scrittura del giornale: i
lavori del backend passano invece da `script.fn_job_run_start` e `script.fn_job_run_end`.

---

### Chi sta girando: il processo si dichiara, o si deriva dal nome

Ogni corsa dice **di quale processo** è (`processo_codice`, verso `dbops.processi`). Il
parametro `p_processo_codice` lo dichiara in modo esplicito, e se c'è vince. Se manca, la
funzione cerca in `dbops.processi` un processo con lo stesso codice del `jobname`: per
convenzione il nome che il wrapper passa e il codice del processo sono la stessa stringa.
Così i wrapper si dichiarano senza passare il parametro, e senza toccare la configurazione
dello scheduler.

⚠️ Il nome che conta è quello che il **wrapper passa** a questa funzione, non il nome del
job pgAgent: i due possono differire (il job `automations_cleanup_weekly` chiama un wrapper
che si registra come `automations_cleanup`). Lo presidia
`db/pgtap/dbops/test-processi-jobname-wrapper.sql`, che guarda ogni `proc_*_job`.

⛔ **La funzione non inventa un processo.** Un `jobname` che non corrisponde a nessun
processo, senza il parametro esplicito, lascia il codice vuoto, e il CHECK
`chk_job_run_log_processo_dichiarato` respinge la riga nuova: la corsa non parte, e l'errore
torna al chiamante. Un processo che non sa dire chi è non gira.

`p_auth_user_id` è l'**utente tecnico** della corsa, per i soli processi che ne hanno uno;
finisce in `auth_user_id`. Non è l'operatore che ha chiesto un singolo lavoro di una coda:
quello sta nello scope del lavoro in `dbops.coda_lavori`. I wrapper dei job pgAgent non lo
passano.

La riga porta anche `ruolo_sessione`, il ruolo che si è **collegato** (`session_user`):
dentro una procedura `SECURITY DEFINER` l'utente corrente sarebbe sempre il proprietario,
e non direbbe chi ha lanciato la corsa.

---

### ⭐ Una corsia occupata non fa partire il lavoro, e lo dice

Il parametro `p_lock_key` è facoltativo. Se c'è, la funzione prova a prendere un advisory
lock di sessione su quella chiave. Se un'altra corsa lo tiene, il lavoro **non parte**: la
funzione scrive una riga **saltata** (`saltata` vera, già chiusa, `ok` vuoto, con processo,
utente tecnico e ruolo come una corsa vera) ed esce.

Una riga saltata non è una corsa riuscita: non ha fatto lavoro, quindi non ha esito. Chi
chiede «qual è l'ultima corsa vera?» la scarta; chi chiede «la sveglia è viva?» la conta.
Il dettaglio sta nella scheda di `maintenance.job_run_log`.

⚠️ Il lock è nella forma a **un** argomento, e di proposito: è uno spazio distinto da quello
di `script.fn_job_run_start`, che usa la forma a due. Le corsie dei job del database e
quelle dei lavori del backend non si bloccano a vicenda.

---

### La corsa riuscita

La riga si apre prima del lavoro. Poi l'istruzione gira con il suo conteggio di righe, e la
riga si chiude con la fine, `ok` vero, le righe toccate e il messaggio `done`. Il lock, se
preso, si rilascia.

La funzione non apre né chiude transazioni: il lavoro e la sua riga stanno nella
transazione di chi chiama. In CI, dentro la convergenza del rilascio, sono la transazione
del changeSet.

---

### ⛔ Il fallimento: il lavoro si annulla, il verbale no

Quando l'istruzione fallisce, la funzione raccoglie messaggio, dettaglio, suggerimento,
contesto e SQLSTATE dell'errore, e ne fa due cose:

* **`sqlstate`** riceve lo SQLSTATE;
* **`error_code`** riceve il **codice di dominio** (`E_…`) quando l'errore rispetta il
  contratto di `script.fn_log_and_raise_error` — SQLSTATE `P0001` con il canale del vincolo
  valorizzato — e altrimenti lo SQLSTATE. ⚠️ Il canale del vincolo da solo non basta: per
  una violazione di unicità porta il nome del vincolo, non un codice d'errore.

Poi la funzione **rilancia** l'errore, ed è voluto: smettere di propagarlo farebbe risultare
riuscito a chi l'ha chiesto un lavoro che non lo è. Il RAISE non si toglie.

Rilanciare annulla la transazione, e con lei l'aggiornamento della riga a «fallita». Per
questo, prima del RAISE, la funzione passa gli stessi dati a
`maintenance.fn_job_run_log_failure`, che scrive il verbale su una **connessione separata**,
dove l'annullamento non arriva. **È quella la riga del fallimento che resta nel giornale.**

L'aggiornamento in transazione non è un doppione inutile: resta solo se il chiamante cattura
l'eccezione senza propagarla, e allora la transazione sopravvive. ⚠️ In quel caso nel giornale
le righe rosse diventano due, con lo stesso `run_uuid`: quella in transazione e il verbale
già scritto fuori.

Il verbale fuori transazione non solleva mai: se il canale manca emette un avviso nel log del
server, e il fallimento resta senza riga. Il lock, se preso, si rilascia anche qui.

---

### Codici errore

La funzione non solleva codici suoi: rilancia l'errore del lavoro così com'è. Sulla riga
nuova, un processo non dichiarato o inesistente fa fallire la scrittura con il CHECK
`chk_job_run_log_processo_dichiarato` o con la FK `fk_job_run_log_processi`.

---

### Test

* `db/pgtap/maintenance/test-job-run-attore.sql` — la derivazione del processo dal
  `jobname`, il rifiuto di un `jobname` sconosciuto, una sola firma.
* `db/pgtap/maintenance/test-job-run-saltata-v1.sql` — la corsa senza lock è una corsa vera,
  e il ramo del lock occupato, con il lock tenuto da una seconda sessione (in skip dove la
  sessione non si apre).
* `db/pgtap/maintenance/test-job-run-ruolo-sessione-v1.sql` — la corsa e la riga saltata
  portano il ruolo che si è collegato.
* `db/pgtap/maintenance/test-job-run-sqlstate-e-codice-v1.sql` — la lettura del codice di
  dominio solo col contratto `P0001` e il passaggio dello SQLSTATE al verbale: presidi sul
  testo, perché il ramo di fallimento lascerebbe una riga vera nel giornale.
* `db/pgtap/maintenance/test-job-run-log-failure-out-of-tx.sql` — la funzione chiama il
  verbale fuori transazione, e continua a rilanciare.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — ogni nome passato da un wrapper esiste
  in `dbops.processi`.

---

### Note di migrazione

* 2026-09-04 — due parametri in coda, `p_processo_codice` e `p_auth_user_id`, con la
  derivazione del processo dal `jobname`.
* 2026-09-05 — il verbale del fallimento si scrive anche fuori transazione. Prima la riga
  `ok = false` moriva col RAISE, e nessun job che passa di qui poteva lasciare una riga rossa:
  `apply_storicizza_weekly` falliva ogni settimana da mesi con l'ultimo verdetto a `done`. Dallo
  stesso giorno il CHECK `chk_job_run_log_processo_dichiarato` respinge le corse senza
  processo.
* 2026-10-10 — col lock occupato la riga nasce saltata, chiusa e senza esito. Prima nasceva
  `ok = true` e aperta, e ogni lettore la contava come corsa vera
  (`brief-db-corsa-saltata-non-e-una-corsa`).
* 2026-10-15 — le due scritture portano `ruolo_sessione` (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo SQLSTATE va nella sua colonna e `error_code` riceve il codice di dominio;
  prima un errore di dominio lasciava solo `P0001` (`brief-db-presidio-job-run-a-chi-tocca`).

---

{% include-markdown "signature-core.md" %}
