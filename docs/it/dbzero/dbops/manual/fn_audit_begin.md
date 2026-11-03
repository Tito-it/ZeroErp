## 📘 Documentazione Concettuale – Funzione `dbops.fn_audit_begin`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — il registro in cui apre la riga
>
> Approfondimento funzioni:
>
> * [dbops.fn_audit_end](/dbzero/dbops/funzioni/fn_audit_end) — la chiusura della stessa riga
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la riga intera in una volta, la porta dell'applicazione
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — apre la connessione di log, nel ramo fuori transazione
>
> Guide:
>
> * [Audit Logging](/guide/messaggi-audit) — la modalità sessione e chi può scrivere

---

### 🎯 Scopo Principale

Apre una **corsa** nel registro `dbops.audit_log`: scrive una riga con stato `START` e ne
restituisce l'id, che il chiamante passa a `dbops.fn_audit_end` per chiuderla con l'esito.

È la metà iniziale della modalità sessione, pensata per i lavori che hanno una durata: la riga
nasce all'inizio, e la durata la calcola la chiusura.

---

### Che cosa scrive

La riga porta il nome della funzione o del processo, i parametri d'ingresso (un oggetto vuoto se
non ce ne sono), e i campi di dettaglio che il chiamante passa: modalità di esecuzione, moduli,
tipo di regola, simulazione, host, versione applicativa. L'ora d'inizio, il ruolo che scrive e il
`tx_id` li mettono i default della tabella e il suo trigger.

Una corsa aperta e mai chiusa resta `START`: la funzione non ha modo di accorgersene.

---

### ⛔ Riservata al proprietario del registro

La chiusura della corsa è un aggiornamento della riga, e l'applicazione non può aggiornare il
registro. Per questo la coppia `fn_audit_begin` / `fn_audit_end` non è eseguibile né da
`zeroerp_app` né da `PUBLIC`: la eseguono chi possiede la tabella (il migratore, i job di
manutenzione) e i ruoli che il provisioning autorizza in modo esplicito. L'applicazione scrive con
la sola `fn_audit_log_once`.

La postura è dichiarata nel ciclo dei grant della convergenza del rilascio; il perimetro di chi ci
scrive lo tiene il cancello `dbops.vw_audit_log_scrittori_fuori_perimetro`.

Oggi nessuna funzione del progetto la chiama: la porta resta, per gli strumenti di
amministrazione che la usassero.

---

### ⚠️ Il ramo fuori transazione

Se il GUC `myapp.log_with_dblink` vale `on` e la connessione di log `logconn` si apre, la riga si
scrive su quella connessione, e sopravvive all'annullamento della transazione del chiamante. Se il
GUC non è impostato, o vale altro, la scrittura è nella transazione di chi chiama. ⚠️ Qui un GUC
assente vale «spento», mentre per `script.fn_ensure_logconn` vale «acceso».

⛔ Il ramo fuori transazione, oggi, non scrive: la connessione di log entra con il ruolo del
canale, che ha il solo diritto di aggiungere a `dbops.error_log` (e al giornale dei job), non a
`dbops.audit_log`. La chiamata fallisce, e con lei la transazione del chiamante. Inoltre, senza
moduli passati, il ramo costruisce un array non valido.

---

### Test

* `db/pgtap/dbops/test-registri-append-only-postura-v1.sql` — l'applicazione non la può eseguire
  (permesso negato, anche come comportamento).
* `db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql` — chi la chiama fuori da `dbops` e
  `maintenance` compare nel cancello.

---

### Note di migrazione

* 2025-08-22 — nasce con `fn_audit_end` e `fn_audit_log_once`.
* 2026-09-11 — diventa riservata al proprietario del registro, insieme a `fn_audit_end`.

---

{% include-markdown "signature-core.md" %}
