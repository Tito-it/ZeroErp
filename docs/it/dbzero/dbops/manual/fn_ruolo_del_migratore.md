## 📘 Documentazione Concettuale – Funzione `dbops.fn_ruolo_del_migratore`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_sessione_del_migratore](/dbzero/dbops/funzioni/fn_sessione_del_migratore) — chiamante: la stessa domanda su `session_user`
> * [dbops.fn_run_automations_seed_primo_impianto](/dbzero/dbops/funzioni/fn_run_automations_seed_primo_impianto) — chiamante: riconosce le righe di seed già presenti da `user_insert`
>
> Guide:
>
> * [Linee guida SQL — 11.8 La postura più stretta di zeroerp_app](/linee-guida-sql#118-una-postura-piu-stretta-per-zeroerp_app-si-dichiara-nel-loop-dei-grant-non-in-un-revoke) — perché una guardia nel corpo legge `session_user`

---

### 🎯 Scopo Principale

Dice se un **nome** è un ruolo di chi amministra il database: il migratore, in qualunque ambiente,
o un superuser. È la regola di
[fn_sessione_del_migratore](/dbzero/dbops/funzioni/fn_sessione_del_migratore) separata dalla
sessione: quella la chiede su `session_user`, il runner del seed di primo impianto sul `user_insert`
di una riga già scritta.

---

### La regola

* Il nome si cerca in `pg_roles`. Vero se il ruolo è **membro** del proprietario dello schema
  `dbops`, oppure è un superuser. Si guarda l'appartenenza e non il nome: il migratore ha nomi
  diversi fra sviluppo, CI e produzione, ma possiede sempre lo schema.
* Uno username dell'applicazione, `NULL` o un ruolo che non esiste valgono `false`, senza errore.
  Su `user_insert` capita spesso: lì c'è anche chi ha scritto dall'app.
* ⚠️ Un utente dell'applicazione che si chiama come un ruolo del database verrebbe preso per il
  migratore. Il presidio delle credenziali lo segnala
  ([vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare), motivo
  `NOME_DI_RUOLO_DB`).

---

### Test

* `db/pgtap/dbops/test-sec-functions-owner-riservato-v1.sql` — la domanda arriva fin qui da
  `fn_sessione_del_migratore`, e legge `session_user`.
* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql` — all'iscrizione di una tabella, una
  riga col `user_insert` del migratore entra nel registro come nata dal seed.

---

### Note di migrazione

* 2026-11-17 — nasce, estratta da `fn_sessione_del_migratore` alla seconda domanda sullo stesso
  criterio, l'iscrizione delle righe di seed (`brief-db-seed-primo-impianto-non-si-riscrive`).

---

{% include-markdown "signature-core.md" %}
