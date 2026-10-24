## 📘 Documentazione Concettuale – Funzione `maintenance.fn_job_run_log_failure()`

> **Collegamenti utili**
>
Approfondimenti tabelle:
>
[`maintenance.job_run_log`](/dbzero/maintenance/manual/job_run_log)
>
Approfondimenti funzioni:
>
[`maintenance.fn_run_and_log`](/dbzero/maintenance/manual/fn_run_and_log) ·
[`script.fn_log_error_only`](/dbzero/script/manual/fn_log_error_only)
>
Presidio:
> [`maintenance.vw_job_run_da_guardare`](/dbzero/maintenance/manual/vw_job_run_da_guardare)

---
### 🎯 Scopo Principale
(latest review 05-09-2026)

Scrive il verbale di un lavoro **fallito** in un posto dove l'annullamento non
arriva: una **connessione separata**.

---

### ⛔ Il problema che risolve, ed è più grave di come sembra

Quando un lavoro notturno va male, `maintenance.fn_run_and_log` fa la cosa
giusta: cattura l'errore e scrive nel giornale *«fallito, ecco il motivo»*.

Poi rilancia l'errore verso l'alto — e rilanciare un errore **annulla tutto
quello che è stato fatto**, compresa la riga appena scritta.

> ⭐ È un usciere che scrive *«il visitatore è caduto dalle scale»* e poi, vedendo
> la caduta, **strappa la pagina** — la sua nota compresa.

⇒ Non è che le corse fallite mancassero: **non potevano esistere**. Misurato il
2026-09-05, in tutta la storia del giornale: **zero** fallimenti dei job pgAgent,
contro 31 dei comandi (che passano da un'altra strada, dove è il codice
applicativo a governare l'annullamento).

⛔ Ed è così che un lavoro settimanale è morto ogni settimana **per sei mesi** con
l'ultimo verdetto agli atti a *«fatto»*.

---

### ⭐ La soluzione era già in casa

`script.fn_log_error_only` scrive gli errori su una connessione separata **dal
febbraio 2026**. Le sue 143.000 righe — fra cui 262 di un controllo che esiste
*solo* per rifiutare — sono la prova che quel canale sopravvive
all'annullamento.

⇒ Qui si riusa lo stesso canale. Non se ne inventa un altro.

---

### ⛔ Non è un «esegui quello che vuoi fuori transazione»

Una funzione generica che eseguisse istruzioni arbitrarie con privilegi elevati
sarebbe la cosa più pericolosa da lasciare in giro.

⇒ Questa prende **valori tipizzati** e costruisce da sola la propria scrittura.
Non esiste un parametro che permetta di farle scrivere altro.

---

### ⚠️ Non rompe mai chi la chiama, e questo ha un rovescio

La chiama un gestore d'errore: qualcuno che sta **già** andando male. Ogni via
d'uscita è un avviso nel registro del server, mai un'eccezione — non si fa
fallire due volte un lavoro già fallito.

> ⛔ **Il rovescio**: quando il canale non funziona, **tace**. Un controllo che
> guardasse solo *«la chiamata non è esplosa»* sarebbe verde anche mentre non
> scrive niente.
>
> ⇒ **È successo due volte** il giorno in cui è nata: prima perché la funzione
> apparteneva a un utente senza i privilegi per aprire la connessione, poi
> perché l'utente del canale non poteva entrare nello schema.

⭐ La regola che ne resta: **un canale che tace quando non funziona non si
collauda guardando chi lo chiama, si collauda guardando dove dovrebbe arrivare.**

---

### Che cosa serve perché funzioni

* la funzione deve appartenere a un utente con privilegi amministrativi —
  l'allineamento è automatico (`dbops.sec_functions_owner`);
* l'utente del canale deve poter **entrare** nello schema e **scrivere** il
  giornale. ⚠️ Non leggerlo: chi redige un verbale non ha bisogno di rileggerlo.

---

### Verifica

`db/pgtap/maintenance/test-job-run-log-failure-out-of-tx.sql` — controlla i
**presupposti**, non la scrittura: una riga scritta fuori transazione
sopravvivrebbe alla pulizia del test, e sporcherebbe il giornale a ogni giro.
⇒ La prova completa si fa a mano, una volta: far fallire un lavoro e guardare il
presidio.

---

### ⭐ Rev 2026-10-16 — `p_sqlstate`

Parametro nuovo **in coda**, con default `NULL`: lo SQLSTATE dell'errore, scritto in
`job_run_log.sqlstate`. `p_error_code` resta «il codice più preciso che si ha». La firma
è cambiata con `DROP` + `CREATE` nel provision-post (la funzione è di un superuser), e
la riga del registro `dbops.sec_functions_owner` porta la firma nuova.
*Brief: `brief-db-presidio-job-run-a-chi-tocca.md`.*

---

{% include-markdown "signature-core.md" %}
