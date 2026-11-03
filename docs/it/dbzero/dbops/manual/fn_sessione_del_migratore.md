## 📘 Documentazione Concettuale – Funzione `dbops.fn_sessione_del_migratore`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_sync_functions_owner](/dbzero/dbops/funzioni/fn_sync_functions_owner) — chiamante: la guardia della sync dei proprietari
> * [script.fn_totp_disabilita_device](/dbzero/script/funzioni/fn_totp_disabilita_device) — chiamante: lo spegnimento del secondo fattore dal server
> * [script.fn_blocca_credenziale](/dbzero/script/funzioni/fn_blocca_credenziale) — chiamante: il blocco di una credenziale di sistema, l'uscita d'emergenza
>
> Guide:
>
> * [Linee guida SQL — 11.8 La postura più stretta di zeroerp_app](/linee-guida-sql#118-una-postura-piu-stretta-per-zeroerp_app-si-dichiara-nel-loop-dei-grant-non-in-un-revoke) — perché una guardia nel corpo legge `session_user`

---

### 🎯 Scopo Principale

Dice se la connessione è di chi amministra il database — il migratore, in qualunque ambiente, o un
superuser — e non dell'applicazione. Serve alle operazioni che solo lui può fare: allineare i
proprietari delle funzioni sensibili, spegnere dal server il secondo fattore di una persona,
bloccare una credenziale di sistema.

---

### La regola

Vero se il ruolo con cui la connessione è entrata è **membro** del proprietario dello schema
`dbops`, oppure è un superuser. Si guarda l'appartenenza e non il nome: il migratore ha nomi diversi
fra sviluppo, CI e produzione, ma possiede sempre lo schema.

* Si legge `session_user`, non il ruolo corrente: dentro una `SECURITY DEFINER` il ruolo corrente
  è il proprietario della funzione, e la risposta sarebbe sempre sì.
* ⚠️ Limite dichiarato: una connessione aperta dal migratore che cambia ruolo con `SET ROLE` resta
  del migratore. PostgreSQL non offre un modo di leggere chi ha chiamato una `SECURITY DEFINER`
  senza questo limite.
* Fail-closed: un'informazione mancante vale «no».
* Risponde sì o no e non solleva: il rifiuto, e la sua forma, sono del chiamante.

---

### Test

* `db/pgtap/dbops/test-sec-functions-owner-riservato-v1.sql` — come applicazione la sync è
  rifiutata, e la domanda legge `session_user`.
* `db/pgtap/config/test-totp-disabilita-migratore-v1.sql` — dalla sessione del migratore lo
  spegnimento del secondo fattore passa e la sync pure.
* `db/pgtap/config/test-totp-porta-v1.sql` — come applicazione la risposta è «no».
* `db/pgtap/config/test-credenziale-di-sistema-migratore-v1.sql` — il runner è la sessione del
  migratore, e da lì una credenziale di sistema si blocca.

---

### Note di migrazione

* 2026-09-29 — estratta dal corpo di `dbops.fn_sync_functions_owner` alla seconda occorrenza della
  domanda, lo spegnimento del secondo fattore (`brief-db-secondo-fattore-totp`).
* 2026-10-03 — la usa anche il blocco di una credenziale di sistema dal server.

---

{% include-markdown "signature-core.md" %}
