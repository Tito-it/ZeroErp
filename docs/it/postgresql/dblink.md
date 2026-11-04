# Estensione PostgreSQL: `dblink`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> **Destinatari**: chi installa un server, chi scrive una funzione che deve lasciare una traccia anche se la transazione fallisce
>
> **Vedi anche**:
>
> * [Parametri personalizzati (GUC)](/postgresql/parametri-personalizzati-(GUC)) — `myapp.dblink_log_connection`, `myapp.logconn`, `myapp.log_with_dblink`: chi li imposta e chi li legge
> * [Installazione](/installazione) — passo 9, il canale dei registri
> * [Provisioning ruoli DB](/dev/backend/provisioning-db-roles) — il ruolo `zeroerp_log`
> * [script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa) — la regola unica: se il canale è acceso, e con quale stringa
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) · [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) · [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id) · [maintenance.fn_job_run_log_failure](/dbzero/maintenance/funzioni/fn_job_run_log_failure)

`dblink` apre, da dentro una funzione, una **seconda connessione** al database. In Zero ERP serve a una
cosa sola: scrivere un registro **fuori dalla transazione corrente**, così che la riga resti anche
quando la transazione viene annullata. Senza, il log di un errore verrebbe scritto e cancellato insieme
all'errore che racconta.

---

## Chi lo usa

| Funzione | Che cosa scrive fuori transazione |
| --- | --- |
| `script.fn_log_error_only` | la riga di `dbops.error_log` di un errore (la chiama anche `fn_log_and_raise_error` prima del `RAISE`) |
| `maintenance.fn_job_run_log_failure` | il verbale di un job **fallito** in `maintenance.job_run_log` |
| `dbops.fn_get_or_create_session_tx_id` | il `tx_id` di sessione |
| `dbops.fn_audit_log_once` | l'audit delle automazioni, **solo** con `myapp.log_with_dblink = on`; altrimenti in transazione |

La connessione si chiama `logconn` e la apre `script.fn_ensure_logconn`: una per sessione, riusata
finché la sessione vive. Le prime tre funzioni **non sollevano** se il canale è spento o non
risponde: emettono un `WARNING` (il `tx_id` prende la sentinella) e il chiamante prosegue. L'audit,
con il canale che non si apre, ripiega sulla scrittura in transazione.

---

## Come è fatto il canale

1. **Il ruolo**: `zeroerp_log`, ruolo di sistema creato dalla fase `ruoli` di
   `scripts/sql/provision_zeroerp.sql`. Può solo inserire in `dbops.error_log` e in
   `maintenance.job_run_log`.
2. **Il service**: la connessione si fa con un nome di service, mai con la password nella stringa. Il file
   è dell'utente di **sistema** `postgres`, perché `dblink` si collega dal processo del server:

   ```ini
   # /var/lib/postgresql/.pg_service.conf  (chown postgres:postgres, chmod 600)
   [zeroerp_log]
   dbname=zeroerp
   host=127.0.0.1
   user=zeroerp_log
   ```

   La password sta in `/var/lib/postgresql/.pgpass`, riga `127.0.0.1:5432:zeroerp:zeroerp_log:<password>`.
3. **Il parametro**: `myapp.dblink_log_connection = 'service=zeroerp_log'`, impostato **per ruolo**
   (`ALTER ROLE … IN DATABASE`) per `zeroerp_owner`, `zeroerp_app` e `zeroerp_job` da
   `scripts/sql/provision_dblink_log_channel.sql` (passo 9 dell'installazione). Lo script dà anche a
   `zeroerp_log` i diritti di scrittura.

### ⚠️ Perché le funzioni del canale sono di `postgres`

PostgreSQL permette a un utente **non superuser** di aprire una connessione `dblink` solo se quella
connessione usa davvero una password. Altrimenti risponde *«password or GSSAPI delegated credentials
required»*. Per questo il canale si apre sempre **come `postgres`**: `fn_ensure_logconn` è di
`postgres`, e la chiamano funzioni `SECURITY DEFINER` di `postgres` (`fn_log_error_only`,
`fn_job_run_log_failure`, `fn_get_or_create_session_tx_id`). Il registro degli owner
`dbops.sec_functions_owner` le elenca, e `dbops.fn_sync_functions_owner()` le riallinea. Un `SELECT dblink_connect(…)` scritto a mano da
`zeroerp_app` fallisce con quel messaggio: è atteso.

---

## Verifica dopo un'installazione o un restore

Dopo un restore o una clonazione il file di service e il `.pgpass` di `postgres` vanno ricreati, e lo
script del passo 9 rilanciato.

La prova che conta è **guardare dove la riga deve arrivare**, non che la chiamata «non esploda»: il
canale è fatto per tacere quando non funziona. Si provoca un errore registrato in una transazione che
poi si annulla, e si controlla che la riga sia in `dbops.error_log`.

---

## Spegnerlo

Il canale è acceso quando c'è una stringa di connessione e l'interruttore non dice `off`. La regola è
una sola, in [script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa), e la
seguono `fn_ensure_logconn` e le prime tre funzioni della tabella in *Chi lo usa*.

* `myapp.log_with_dblink = off` nella sessione spegne il canale (maiuscole e spazi non contano): le
  migrazioni, il makefile e le connessioni di CI lo passano così. ⚠️ Togliere il parametro non basta:
  assente vale acceso.
* Una stringa di connessione vuota fa lo stesso: in CI e sullo scratch è vuota per costruzione.

Con il canale spento `fn_get_or_create_session_tx_id` restituisce la sentinella, e le scritture sulle
tabelle tracciate la prendono come `tx_id`; `fn_log_error_only` e `fn_job_run_log_failure` non scrivono
e lo dicono con un `WARNING`. ⚠️ L'audit (`fn_audit_log_once`) non segue ancora la regola comune: per
lui l'interruttore assente vale spento, e solo `on` accende il ramo fuori transazione.

Il dettaglio dei tre parametri sta nella pagina [Parametri personalizzati (GUC)](/postgresql/parametri-personalizzati-(GUC)).

---
{% include-markdown "signature-core.md" %}
