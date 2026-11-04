## 📘 Documentazione Concettuale – Funzione `dbops.fn_audit_end`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — il registro in cui chiude la riga
>
> Approfondimento funzioni:
>
> * [dbops.fn_audit_begin](/dbzero/dbops/funzioni/fn_audit_begin) — apre la riga che questa chiude
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la riga intera in una volta, la porta dell'applicazione
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — apre la connessione di log, nel ramo fuori transazione
>
> Guide:
>
> * [Audit Logging](/guide/messaggi-audit) — la modalità sessione e chi può scrivere

---

### 🎯 Scopo Principale

Chiude una **corsa** aperta con `dbops.fn_audit_begin`: aggiorna la riga del registro
`dbops.audit_log` con l'esito, il messaggio, l'eventuale errore, il conteggio, il riepilogo e la
durata.

---

### Che cosa scrive

La riga si cerca per id. Lo stato finale è `OK` se il chiamante non ne passa un altro; il vincolo
della tabella ammette `OK`, `ERROR`, `WARN`, `DRYRUN` e `START`.

* La **durata** è il tempo trascorso dall'apertura della riga, calcolato alla chiusura, se la riga
  non l'ha già.
* Nel ramo in transazione, i campi che il chiamante lascia vuoti **conservano** il valore che la
  riga ha già (stato, SQLSTATE, contesto dell'errore, conteggio, riepilogo); il messaggio invece si
  riscrive sempre, anche a vuoto.

⚠️ Un id che non corrisponde a nessuna riga non è un errore: l'aggiornamento non trova niente e la
funzione esce in silenzio.

---

### ⛔ Riservata al proprietario del registro

La chiusura è un aggiornamento del registro, e l'applicazione può solo aggiungere righe. Per questo
la funzione non è eseguibile né da `zeroerp_app` né da `PUBLIC`: la eseguono chi possiede la
tabella e i ruoli che il provisioning autorizza in modo esplicito. L'applicazione scrive con la
sola `fn_audit_log_once`.

Oggi nessuna funzione del progetto la chiama.

---

### ⚠️ Il ramo fuori transazione

Se il GUC `myapp.log_with_dblink` vale `on` e la connessione di log `logconn` è aperta,
l'aggiornamento passa da quella connessione. Con il GUC assente la chiusura resta nella
transazione del chiamante.

⛔ Il ramo fuori transazione non si comporta come l'altro: scrive **tutti** i campi così come
arrivano, quindi un campo lasciato vuoto cancella il valore della riga, e uno stato vuoto viola
l'obbligatorietà della colonna. E oggi non scrive comunque: il ruolo del canale di log non ha il
diritto di aggiornare `dbops.audit_log`, e la chiamata fallisce.

---

### Test

* `db/pgtap/dbops/test-registri-append-only-postura-v1.sql` — l'applicazione non la può eseguire.
* `db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql` — chi la chiama fuori da `dbops` e
  `maintenance` compare nel cancello.

---

### Note di migrazione

* 2025-08-22 — nasce con `fn_audit_begin` e `fn_audit_log_once`.
* 2026-09-11 — diventa riservata al proprietario del registro, insieme a `fn_audit_begin`.

---

{% include-markdown "signature-core.md" %}
