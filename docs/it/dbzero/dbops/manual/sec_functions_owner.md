## 📘 Documentazione Concettuale – Tabella `dbops.sec_functions_owner`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_sync_functions_owner](/dbzero/dbops/funzioni/fn_sync_functions_owner) — applica il registro: allinea il proprietario di ogni funzione
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — nel registro: il log fuori transazione via dblink
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — nel registro: la connessione dblink del log
> * [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id) — nel registro: il `tx_id` di sessione
> * [dbops.fn_generate_tx_id](/dbzero/dbops/funzioni/fn_generate_tx_id) — nel registro: la generazione del `tx_id`
> * [maintenance.fn_job_run_log_failure](/dbzero/maintenance/funzioni/fn_job_run_log_failure) — nel registro: il verbale di una corsa fallita, fuori transazione
>
> Guide:
>
> * [Linee guida SQL — 11.8 La postura più stretta di zeroerp_app](/linee-guida-sql#118-una-postura-piu-stretta-per-zeroerp_app-si-dichiara-nel-loop-dei-grant-non-in-un-revoke) — la sola lettura del registro e la difesa nel corpo della sync

---

### 🎯 Scopo Principale

Il registro delle funzioni che devono appartenere a un proprietario preciso, di solito `postgres`:
una riga per funzione, con schema, nome, tipi degli argomenti e proprietario richiesto.
`dbops.fn_sync_functions_owner` lo legge e allinea il catalogo.

---

### Perché alcune funzioni sono di `postgres`

Sono le funzioni `SECURITY DEFINER` che aprono una connessione `dblink` senza password — il log
degli errori fuori transazione, la sua connessione, il `tx_id` di sessione, il verbale di una corsa
fallita — o che per altre ragioni hanno bisogno dei diritti di un superuser. `dblink` rifiuta una
connessione senza password a chi non è superuser: se una di queste funzioni passasse al
migratore, il canale di log tacerebbe. Un restore, un clone o un `CREATE OR REPLACE` fatto dal
migratore possono cambiare il proprietario: il registro dice qual è quello giusto, e la sync lo
rimette.

---

### Una riga per funzione, riconosciuta anche dai tipi degli argomenti

La chiave naturale è schema, nome e tipi degli argomenti: due funzioni con lo stesso nome e firme
diverse sono due righe. I tipi si scrivono come li accetta `to_regprocedure` (separati da virgola,
vuoti per una funzione senza argomenti). Una riga che non risolve a una funzione viva non ferma
niente: la sync la segnala con un avviso e passa oltre.

---

### ⭐ Il prestito della proprietà

Il migratore non può sostituire una funzione di `postgres`. Un changeSet che deve ridefinirne una
la prende **in prestito**: scrive se stesso come proprietario richiesto, lancia la sync, sostituisce
la funzione, rimette `postgres` e rilancia la sync, verificando che il proprietario sia tornato. È
l'unica scrittura ammessa fuori dal seed.

⚠️ La sync non solleva: un prestito non riuscito si manifesterebbe più avanti come «bisogna essere
proprietari», lontano dalla causa. Subito dopo il prestito, quindi, il changeSet confronta il
proprietario della funzione con l'utente che sta migrando, e si ferma se differiscono.

---

### ⛔ La scrive solo il migratore

Chi scrive questa tabella sceglie il proprietario delle funzioni sensibili, perché la sync applica
ciò che vi trova. Per questo:

* la scrivono solo il seed (`80_data/sql/dbops/sec_functions_owner.csv`) e i changeSet che
  prendono una funzione in prestito;
* l'applicazione la legge e basta: niente `INSERT`, `UPDATE`, `DELETE`. Leggere il registro senza
  poterlo scrivere né eseguire la sync non dà nessuna leva.

La postura sta nelle tre sedi delle tabelle in sola lettura (il changeSet che revoca, il loop dei
grant, il provisioning); la sync, a sua volta, rifiuta chiunque non sia il migratore o un
superuser.

---

### Test

* `db/pgtap/dbops/test-sec-functions-owner-riservato-v1.sql` — come applicazione: il registro si
  legge ma non si scrive (ogni scrittura è 42501, anche a zero righe), e la sync rifiuta.
* `db/pgtap/dbops/test-postura-proprietario-rls-v1.sql` — ogni `SECURITY DEFINER` è del
  proprietario delle tabelle, o di un superuser per le funzioni di questo registro.

---

### Note di migrazione

* 2025-11-23 — nasce con la sync, dopo i fallimenti delle funzioni del canale di log rimaste senza
  i diritti per aprire `dblink`.
* 2026-09-05 — entra `maintenance.fn_job_run_log_failure`, il verbale fuori transazione.
* 2026-09-26 — diventa in sola lettura per l'applicazione
  (`brief-db-registro-owner-e-sync-riservati-al-migratore`).

---

{% include-markdown "signature-core.md" %}
