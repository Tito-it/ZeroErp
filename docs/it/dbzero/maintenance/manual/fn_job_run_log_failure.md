## 📘 Documentazione Concettuale – Funzione `maintenance.fn_job_run_log_failure`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale su cui scrive
> * [dbops.sec_functions_owner](/dbzero/dbops/tabelle/sec_functions_owner) — il registro che le assegna il proprietario
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove il verbale diventa visibile
>
> Approfondimento funzioni:
>
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — chi la chiama, prima di rilanciare l'errore
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — il canale fuori transazione che riusa
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — la connessione nominata del canale
> * [dbops.fn_sync_functions_owner](/dbzero/dbops/funzioni/fn_sync_functions_owner) — l'allineamento del proprietario

---

### 🎯 Scopo Principale

Scrive nel giornale dei job il verbale di una corsa **fallita** su una connessione
separata, così che sopravviva all'annullamento della transazione in cui il lavoro è morto.

---

### ⛔ Il problema che risolve: un verbale scritto e strappato nello stesso istante

Quando un lavoro va male, `maintenance.fn_run_and_log` cattura l'errore, aggiorna la riga
della corsa a «fallita» e poi rilancia. Rilanciare annulla tutto quello che la transazione ha
fatto, **compresa quella riga**.

> ⭐ È un usciere che scrive *«il visitatore è caduto dalle scale»* e poi, vedendo la caduta,
> strappa la pagina — la sua nota compresa.

Senza un'altra strada, una corsa fallita di un job del database non potrebbe esistere nel
giornale: l'ultimo verdetto agli atti resterebbe quello dell'ultima corsa riuscita, e un
lavoro morto ogni settimana sembrerebbe sano.

---

### ⭐ Riusa un canale che c'è già

`script.fn_log_error_only` scrive gli errori su una connessione `dblink` separata, e quel
canale sopravvive agli annullamenti. Questa funzione usa lo stesso: prima la connessione
nominata `logconn` (aperta da `script.fn_ensure_logconn`), poi, se non c'è, l'indirizzo
diretto delle impostazioni del canale. Non se ne inventa un altro.

La riga scritta porta lo stesso `run_uuid`, la stessa partenza, la stessa origine, lo stesso
processo e lo stesso utente tecnico della corsa annullata, con `ok` falso, messaggio, codice,
dettaglio e SQLSTATE dell'errore. Il `meta` dice di lei che è stata **scritta fuori
transazione**, e perché: senza, sembrerebbe una riga normale di un giro che invece è stato
annullato.

⚠️ `ruolo_sessione` si legge **qui**, nella sessione del job, e si passa alla scrittura: dentro
la connessione separata il ruolo collegato sarebbe quello del canale di log, non quello della
corsa. `agent_host` porta il nome del cluster.

---

### ⛔ Non è un «esegui quello che vuoi fuori transazione»

Una funzione che eseguisse istruzioni arbitrarie con i privilegi di un superuser sarebbe la
cosa più pericolosa da lasciare in giro. Questa prende **valori tipizzati** e costruisce da sola
la propria scrittura, con ogni valore quotato: non esiste un parametro che le faccia scrivere
altro, né altrove.

---

### ⚠️ Non rompe mai chi la chiama, e questo ha un rovescio

La chiama un gestore d'errore: qualcuno che sta **già** andando male. Ogni via d'uscita è un
avviso nel log del server, mai un'eccezione — non si fa fallire due volte un lavoro già fallito.
Senza canale configurato lo dice con un avviso, e il fallimento resta senza riga.

> ⛔ **Il rovescio**: quando il canale non funziona, **tace**. Un controllo che guardasse solo
> «la chiamata non è esplosa» sarebbe verde anche mentre non scrive niente.

⭐ La regola che ne resta: **un canale che tace quando non funziona non si collauda guardando
chi lo chiama, si collauda guardando dove dovrebbe arrivare.**

Anche il giornale ha le sue regole, e il verbale non le aggira: una corsa senza processo
dichiarato è respinta dal CHECK `chk_job_run_log_processo_dichiarato` anche qui, e finisce in
un avviso.

---

### Che cosa serve perché funzioni

* **Un proprietario superuser.** `dblink` rifiuta a chi non è superuser una connessione senza
  password, quindi la funzione è `SECURITY DEFINER` di `postgres`. Il changeSet non mette il
  proprietario: lo allinea `dbops.fn_sync_functions_owner` dalla riga di
  `dbops.sec_functions_owner`, a ogni migrate, e la riga porta la firma in vigore.
* **Un utente del canale che possa entrare e scrivere.** `zeroerp_log` ha l'accesso allo schema
  e il solo `INSERT` sul giornale. ⚠️ Non lo legge: chi redige un verbale non ha bisogno di
  rileggerlo.

---

### Test

`db/pgtap/maintenance/test-job-run-log-failure-out-of-tx.sql` — controlla i **presupposti**,
non la scrittura: la funzione è `SECURITY DEFINER` di un superuser, l'utente del canale entra
nello schema e scrive il giornale senza poterlo leggere, e `fn_run_and_log` la chiama e continua
a rilanciare. La scrittura non si prova qui perché una riga fuori transazione sopravvive al
ROLLBACK del test e sporcherebbe il giornale a ogni giro: la prova completa si fa a mano, dopo
ogni cambio del canale, facendo fallire un lavoro e guardando
`maintenance.vw_job_run_da_guardare`.

`db/pgtap/maintenance/test-job-run-sqlstate-e-codice-v1.sql` — una sola firma, con lo SQLSTATE
in coda, e la scrittura della colonna (presidio sul testo).

---

### Note di migrazione

* 2026-09-05 — nasce. Fino a quel giorno nessuna corsa fallita di un job pgAgent compariva nel
  giornale, e `apply_storicizza_weekly` risultava `done` mentre falliva ogni settimana. Lo
  stesso giorno il canale è rimasto muto due volte, e solo l'avviso lo diceva: prima la
  funzione era di un utente senza i privilegi per aprire la connessione, poi l'utente del canale
  non poteva entrare nello schema.
* 2026-10-15 — scrive anche `ruolo_sessione` (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — parametro `p_sqlstate` in coda, con default vuoto; `p_error_code` resta «il
  codice più preciso che si ha». La firma è cambiata con `DROP` e `CREATE` nel provision-post,
  perché la funzione è di un superuser (`brief-db-presidio-job-run-a-chi-tocca`).

---

{% include-markdown "signature-core.md" %}
