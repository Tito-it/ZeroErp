## 📘 Documentazione Concettuale – Funzione `dbops.fn_audit_log_once`

> **Ultimo aggiornamento**: 7 novembre 2026
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
Chi vuole la durata la misura da sé e la passa nella riga, con `p_duration_ms`: la durata ha una
sede sola, la colonna `duration_ms`.

---

### Che cosa scrive

Tutto ciò che il chiamante passa, così com'è. Lo stato è obbligatorio e deve stare nel vocabolario
del registro (`OK`, `ERROR`, `WARN`, `DRYRUN`): un valore diverso fa fallire la scrittura.
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

### ⭐ La riga vive e muore con la transazione di chi chiama

La riga si scrive sempre nella transazione del chiamante, qualunque cosa dica il canale di log
(`myapp.log_with_dblink`): se la transazione si annulla, si annulla anche la riga. Un esito che
deve sopravvivere a un errore non sta in questo registro: lo scrive `dbops.error_log`, che ha il
suo canale fuori transazione. Per questo una funzione che fallisce non scrive qui una riga
`ERROR`: la riga sparirebbe con l'errore.

---

### Test

* `db/pgtap/dbops/test-registri-append-only-postura-v1.sql` — l'applicazione la può eseguire, e la
  riga che scrive esiste ed è firmata dal ruolo che l'ha scritta (con il canale fuori transazione
  spento per la durata del test); le due funzioni della modalità sessione non esistono più.
* `db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql` — una funzione costruita fuori
  perimetro che la chiama compare nel cancello, come scrittura attraverso la porta.
* `db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql`, test 1-2 — la durata nella sua colonna;
  con il canale di log acceso la riga nasce comunque nella transazione del chiamante.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — il registro in cui scrive non ha il
  trigger di scadenza alla nascita.

---

### Note di migrazione

* 2025-08-22 — nasce con `fn_audit_begin` e `fn_audit_end`.
* 2026-09-11 — resta la sola funzione di audit eseguibile dall'applicazione.
* 2026-11-04 — ritirate `fn_audit_begin` e `fn_audit_end`, la modalità sessione: la prima apriva
  una riga `START`, la seconda la chiudeva con un aggiornamento calcolando la durata. Erano
  riservate al proprietario del registro e non le chiamava nessuno; il loro ramo fuori transazione
  non poteva scrivere, come quello di questa funzione (`brief-db-revisione-dbops`).
* 2026-11-07 — esce il ramo fuori transazione, che non poteva scrivere e faceva fallire la
  transazione del chiamante; nasce `p_duration_ms`, in coda e facoltativo (`brief-db-revisione-dbops`,
  giro 2).

---

{% include-markdown "signature-core.md" %}
