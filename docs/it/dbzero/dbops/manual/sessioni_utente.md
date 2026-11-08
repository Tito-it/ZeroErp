## 📘 Documentazione Concettuale – Tabella `dbops.sessioni_utente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.request_log](/dbzero/dbops/tabelle/request_log) — la richiesta HTTP di ogni evento, legata da `request_id`
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola di retention della tabella
>
> Approfondimento funzioni:
>
> * [script.fn_totp_disabilita_device](/dbzero/script/funzioni/fn_totp_disabilita_device) — lo scrittore a database: il secondo fattore spento dal server
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — la pulizia che scrive la scadenza e cancella
>
> Guide:
>
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — gli strati dell'audit e la retention
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — login, sessioni e secondo fattore

---

### 🎯 Scopo Principale

Il registro degli eventi di sessione di una persona: il ciclo di vita dei token di accesso (login,
rinnovo, logout, revoca) e lo spegnimento del secondo fattore dal server. Risponde a «quando è
entrato, da dove, quante volte ha rinnovato, quando e perché un token è stato revocato».

---

### Gli eventi

* `LOGIN`, `REFRESH`, `LOGOUT`, `REVOCA`: li scrive il backend, a ogni accesso e rinnovo riuscito,
  all'uscita e alla revoca di un token. Portano il `jti`, l'identificativo del token coinvolto.
* `TOTP_DISABILITATO`: il secondo fattore della persona spento. Quando lo spegne l'applicazione la
  traccia la scrive il backend; quando lo spegne **dal server** chi amministra il database, la scrive
  `script.fn_totp_disabilita_device`, senza `jti`, con da dove, chi e perché nel `dettaglio`.
Un evento fuori da questo elenco è respinto dal vincolo `chk_sessioni_utente_evento`.

⭐ **La scadenza di un token non è un evento**: non la compie nessuno, e scriverla vorrebbe dire
inventare un gesto da un'assenza. Le sessioni scadute si leggono dalla scadenza del token.

---

### Le colonne che si leggono male

* `auth_user_id`: l'utente Django, senza chiave esterna: le tabelle di Django non sono di Liquibase.
* `request_id`: l'identificativo della richiesta, lo stesso di `dbops.request_log`: lega l'evento
  alla richiesta HTTP che l'ha prodotto.
* `ip_address`, `user_agent`: da dove arrivava la richiesta.
* `dettaglio`: i dati in più dell'evento (il motivo di una revoca, chi ha spento il secondo fattore).

---

### Un registro: si scrive, non si corregge

Gli eventi si inseriscono e non si modificano. L'unico aggiornamento è quello della pulizia, che
scrive `cleanup_at` dove manca; per questo la tabella ha comunque i trigger di audit
(`data_update`, `user_update`) e del `tx_id`. Non si storicizza: è già un registro.

---

### 🧹 Retention: centottanta giorni

Non c'è un trigger alla nascita che scriva la scadenza. La scrive la pulizia settimanale, dalla
regola di cleanup della tabella (centottanta giorni invece dei trenta di default), sulle righe che
non l'hanno ancora; la stessa pulizia cancella le righe scadute.

---

### Test

* `db/pgtap/config/test-totp-disabilita-migratore-v1.sql` — lo spegnimento del secondo fattore dal
  server lascia il suo evento `TOTP_DISABILITATO`.
* `db/pgtap/config/test-totp-device-verbi-v1.sql` — dall'applicazione il verbo del database non
  scrive la traccia: la scrive il backend.

---

### Note di migrazione

* 2026-03-05 — nasce, per gli eventi dei token.
* 2026-04-09 — riceve le colonne di aggiornamento dell'audit.
* 2026-09-29 — il vincolo ammette `TOTP_DISABILITATO` (`brief-db-secondo-fattore-totp`).
* 2026-11-08 — il vincolo non ammette più `SCADENZA`, che nessuno scriveva.

---

{% include-markdown "signature-core.md" %}
