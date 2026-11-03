## 📘 Documentazione Concettuale – Vista `dbops.vw_run_senza_attore`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale delle corse che la vista legge
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il registro dei processi, l'attore che una corsa deve dichiarare
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, che la guarda ogni settimana
>
> Approfondimento funzioni:
>
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — deriva il processo dal nome del job
> * [script.fn_job_run_start](/dbzero/script/funzioni/fn_job_run_start) — apre la corsa dei comandi, col processo
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — che cosa la fa arrivare a zero

---

### 🎯 Scopo Principale

I job la cui **ultima corsa** non dice di quale processo è: una riga per job e origine, con
l'istante dell'ultima corsa, quante corse senza attore ha in tutto e se il nome corrisponde a un
processo registrato.

---

### ⭐ Si guarda l'ultima corsa, non tutte

Le corse scritte prima che il giornale registrasse il processo hanno l'attore vuoto per sempre: sono
il giornale di ieri, e non c'è niente da sanare. Una vista che le contasse non arriverebbe mai a
zero, e un registro del debito che non cala è rumore. Sull'ultima corsa, invece, un job esce dalla
vista appena si dichiara.

Il numero delle corse senza attore resta come **contesto** — quanto è vecchia l'omissione — non
come criterio. `processo_registrato` falso vuol dire che il nome del job non corrisponde a nessuna
riga di `dbops.processi`.

---

### Perché oggi contiene solo il passato

`maintenance.fn_run_and_log` deriva il processo dal nome del job, che è la stessa stringa del codice
del processo: i job pgAgent si sono dichiarati senza toccare lo scheduler. Da quando c'è il vincolo
`chk_job_run_log_processo_dichiarato`, nessuna corsa nuova può nascere senza processo: un nome che
non corrisponde a un processo, o un comando che non lo passa, fa fallire la corsa prima che parta.
Il vincolo è `NOT VALID` e non rivaluta il passato.

Quindi in vista restano solo i job la cui ultima corsa è precedente al vincolo. Escono alla prima
corsa nuova.

⚠️ Un job che non gira più — ritirato, rinominato, spento — non ha una corsa nuova: resta in vista
per sempre, e la vista non arriva a zero.

---

### Legge con gli occhi del proprietario

È una vista definer, e l'applicazione ha il diritto di leggerla: il giornale non ha un perimetro
d'azienda. Nel catalogo dei presidi è un registro di lavorazione con perimetro libero, guardato ogni
settimana da chi sviluppa.

---

### Test

* `db/pgtap/maintenance/test-job-run-attore.sql` — la vista guarda l'ultima corsa: un job che si è
  dichiarato esce anche con corse vecchie senza attore; la derivazione del processo dal nome del job
  e il rifiuto di un nome sconosciuto.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — ogni nome di job passato da un wrapper esiste
  in `dbops.processi`.

---

### Note di migrazione

* 2026-09-04 — nasce con la colonna dell'attore sul giornale
  (`brief-db-processi-automatici-identita-e-perimetro`); la prima versione contava tutte le corse
  storiche ed è stata riscritta sull'ultima.
* 2026-09-05 — il vincolo `chk_job_run_log_processo_dichiarato`: da qui le corse nuove hanno sempre
  un processo.

---

{% include-markdown "signature-core.md" %}
