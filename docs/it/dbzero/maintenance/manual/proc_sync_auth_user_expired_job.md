## 📘 Documentazione Concettuale – Procedura `maintenance.proc_sync_auth_user_expired_job`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui resta la corsa
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `sync_auth_user_expired_daily`, attore della corsa
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti di una credenziale, da cui dipende se è attiva
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama che confronta pgAgent col giornale
>
> Approfondimento funzioni:
>
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — esegue il lavoro e scrive la corsa
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
> * [anagrafiche.fn_sync_auth_user_expired](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_expired) — il lavoro: riallinea le credenziali alla data di oggi
> * [anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active) — la decisione su una credenziale
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — la regola di «veste utilizzabile oggi»

---

### 🎯 Scopo Principale

Il wrapper del job pgAgent `sync_auth_user_expired_daily`: esegue
`anagrafiche.fn_sync_auth_user_expired`, che riallinea alla data di oggi lo stato attivo delle
credenziali di accesso, attraverso il giornale dei job.

---

### Una data che arriva non scrive niente

Una credenziale è attiva se ha almeno una veste utilizzabile oggi. Quando una veste o il rapporto
di lavoro scadono, o quando una veste diventa valida, nessuno scrive una riga: cambia solo la
data. I trigger che tengono allineato lo stato attivo della credenziale scattano a ogni modifica
delle vesti, ma non vedono il tempo che passa. Questo job copre quel caso: ogni ora spegne le
credenziali che non hanno più una veste utilizzabile e accende quelle che ne hanno una diventata
valida. Le regole stanno nella scheda di
[anagrafiche.fn_sync_auth_user_expired](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_expired).

È un processo non spegnibile: spento, gli utenti scaduti resterebbero attivi senza che nessuno se
ne accorga. Lo step chiama la procedura solo se
`maintenance.fn_sveglia_accesa('sync_auth_user_expired_daily')` è vero.

---

### ⭐ Senza il giornale il job non esisteva per i presidi

Il job è nato con lo step che chiamava la funzione direttamente: non falliva, ma non scriveva mai
una corsa, e per il panorama dei processi era un job che gira senza registrare. Questa procedura
lo fa passare da `maintenance.fn_run_and_log`, con il codice del processo come `p_jobname` (coincide
col nome del job pgAgent), il nome dello step e la chiamata, senza chiave di lock. Il
comportamento della corsa — la riga nel giornale, il verbale del fallimento scritto fuori
transazione, l'errore rilanciato — lo descrive la scheda di
[fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log).

La funzione restituisce quante credenziali ha riallineato, ma `fn_run_and_log` non conserva il
risultato: nel giornale resta che la corsa è riuscita, non quante credenziali ha cambiato.

---

### Lo schema `django` è dell'applicazione

Lo stato attivo di una credenziale sta in `django.auth_user`, una tabella che crea il migratore di
Django dopo Liquibase. La funzione la raggiunge con istruzioni dinamiche, risolte solo quando
girano, e se la tabella non esiste — in CI, su un database senza le migrazioni di Django — non fa
niente e restituisce zero.

La procedura è `SECURITY DEFINER` con `search_path` fisso, come tutte le `maintenance.proc_*_job`:
chiunque la chiami, il lavoro gira con i diritti del
proprietario. I privilegi sullo schema `django` non li dà un changeSet: stanno nel provisioning
(linee guida SQL, §11.9). L'EXECUTE è tolto a `PUBLIC`.

---

### Ogni ora, anche se il nome dice «daily»

Il job suona ogni ora, al minuto 10. La funzione è idempotente — riallinea solo le credenziali il
cui stato non corrisponde più alla regola — quindi una sveglia frequente la rende solo più
tempestiva. Il giorno lo decide la regola della veste utilizzabile, che legge la data operativa
dell'azienda e non l'orologio del server.

La convergenza dei job in CI non la chiama: il processo è operativo, agisce su dati e orologio.

---

### Test

* `db/pgtap/dbops/test-vw-processi-programmazione.sql` — la regola del panorama che ha trovato il
  difetto: un job pgAgent senza corse nel giornale è nominato come uno che gira e non registra.
* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — la procedura è `SECURITY DEFINER`, col
  `search_path` fisso, del proprietario dello schema, senza EXECUTE a `PUBLIC` né all'applicazione.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il codice passato come `p_jobname` esiste
  in `dbops.processi`.
* `db/pgtap/script/test-fn-veste-utilizzabile-v1.sql` e
  `db/pgtap/anagrafiche/test-super-admin-senza-scadenza-v1.sql` — il lavoro che la procedura
  esegue: la credenziale senza vesti utilizzabili spenta, il riallineamento nei due versi.

---

### Note di migrazione

* 2026-09-06 — nasce questa procedura, e lo step del job, che dalla nascita chiamava la funzione
  senza passare dal giornale, comincia a registrare.
* 2026-09-07 — il processo prende il posto di `sync_auth_user_active`, il comando del backend che
  faceva lo stesso lavoro e che il panorama non vedeva (`brief-db-sveglia-dei-processi`).
* 2026-10-09 — la sveglia diventa oraria; prima girava ogni giorno alle 06:00
  (`brief-be-db-fe-un-solo-fuso-aziendale`).
* 2026-10-14 — diventa `SECURITY DEFINER` con le altre procedure dei job
  (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo step chiama la procedura solo a sveglia accesa
  (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "signature-core.md" %}
