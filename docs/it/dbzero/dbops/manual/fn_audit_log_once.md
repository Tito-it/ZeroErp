## 📘 Documentazione Concettuale – Funzione `dbops.fn_audit_log_once`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — il registro in cui scrive
>
> Approfondimento viste:
>
> * [dbops.vw_audit_log_scrittori_fuori_perimetro](/dbzero/dbops/views/vw_audit_log_scrittori_fuori_perimetro) — il cancello su chi la chiama
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id) — un runner del framework che la usa per le simulazioni
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — apre la connessione di log, nel ramo fuori transazione
>
> Guide:
>
> * [Audit Logging](/guide/messaggi-audit) — le funzioni di audit e chi può scrivere

---

### 🎯 Scopo Principale

Scrive in `dbops.audit_log` **una riga intera in una volta** — stato, parametri, messaggio,
dettagli, eventuale errore, riepilogo — e ne restituisce l'id. Non apre una corsa da chiudere: è
la forma per gli eventi puntuali, come la simulazione di un'automazione o un salto motivato.

È l'**unica** funzione di audit: non esiste più una modalità che apra una corsa e la chiuda dopo.
Chi vuole la durata la misura da sé e la passa nella riga.

---

### Che cosa scrive

Tutto ciò che il chiamante passa, così com'è. Lo stato è obbligatorio e deve stare nel vocabolario
del registro (`START`, `OK`, `ERROR`, `WARN`, `DRYRUN`): un valore diverso fa fallire la scrittura.
`START` resta nel vocabolario per le righe della modalità sessione ritirata: una riga scritta qui
con quello stato non verrà chiusa da nessuno.
L'ora, il ruolo che scrive e il `tx_id` li mettono i default della tabella e il suo trigger; la
durata la passa il chiamante, se la conosce.

La usano le funzioni del framework delle automazioni (le simulazioni, i salti, i rifiuti di una
regola) e gli strumenti di amministrazione di `dbops` e `maintenance`.

---

### ⭐ La porta dell'applicazione

Il registro è append-only per l'applicazione: `zeroerp_app` legge e aggiunge, e questa funzione
aggiunge una riga senza bisogno di riscriverla dopo.

⛔ Che la porta sia aperta all'applicazione non vuol dire che il dominio ci scriva: una funzione
fuori da `dbops` e `maintenance` che la chiama compare nel cancello
`dbops.vw_audit_log_scrittori_fuori_perimetro`.

---

### ⚠️ Il ramo fuori transazione

Se il GUC `myapp.log_with_dblink` vale `on` e la connessione di log `logconn` si apre, la riga si
scrive su quella connessione e sopravvive all'annullamento della transazione del chiamante. Con il
GUC assente la scrittura è nella transazione di chi chiama. ⚠️ Qui un GUC assente vale «spento»,
mentre per tutti gli altri lettori del canale vale «acceso»: la loro regola comune sta in
[script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa), e questa funzione non
la segue ancora.

⛔ Il ramo fuori transazione, oggi, non scrive: il ruolo del canale di log non ha il diritto di
aggiungere a `dbops.audit_log`, e la chiamata fallisce insieme alla transazione del chiamante.
Inoltre il ramo non scrive i vuoti come l'altro: senza parametri scrive il JSON `null` invece di
un vuoto, e senza moduli costruisce un array non valido.

---

### Test

* `db/pgtap/dbops/test-registri-append-only-postura-v1.sql` — l'applicazione la può eseguire, e la
  riga che scrive esiste ed è firmata dal ruolo che l'ha scritta (con il canale fuori transazione
  spento per la durata del test); le due funzioni della modalità sessione non esistono più.
* `db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql` — una funzione costruita fuori
  perimetro che la chiama compare nel cancello, come scrittura attraverso la porta.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — il registro in cui scrive non ha il
  trigger di scadenza alla nascita, perché la scrittura può arrivare dal canale fuori transazione.

---

### Note di migrazione

* 2025-08-22 — nasce con `fn_audit_begin` e `fn_audit_end`.
* 2026-09-11 — resta la sola funzione di audit eseguibile dall'applicazione.
* 2026-11-04 — ritirate `fn_audit_begin` e `fn_audit_end`, la modalità sessione: la prima apriva
  una riga `START`, la seconda la chiudeva con un aggiornamento calcolando la durata. Erano
  riservate al proprietario del registro e non le chiamava nessuno; il loro ramo fuori transazione
  non poteva scrivere, come quello di questa funzione (`brief-db-revisione-dbops`).

---

{% include-markdown "signature-core.md" %}
