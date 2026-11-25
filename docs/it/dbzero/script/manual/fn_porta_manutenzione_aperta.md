## 📘 Documentazione Concettuale – Funzione `script.fn_porta_manutenzione_aperta`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.porte_manutenzione_passaggi](/dbzero/dbops/tabelle/porte_manutenzione_passaggi) — il diario che la porta scrive quando si apre
>
> Approfondimento funzioni:
>
> * [dbops.fn_sessione_del_migratore](/dbzero/dbops/funzioni/fn_sessione_del_migratore) — chi può aprire: la sessione del migratore
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — chiamante: le colonne protette
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — chiamante: le cancellazioni vietate
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — chiamante: le righe del seed di primo impianto
> * [vendite.trgfn_event_log_append_only](/dbzero/vendite/funzioni/trgfn_event_log_append_only) — chiamante: lo stream degli eventi
> * [vendite.trgfn_logs_guard_delete](/dbzero/vendite/funzioni/trgfn_logs_guard_delete) — chiamante: i log dei processi
> * [vendite.trgfn_attivita_fatturabili_guard_commessa](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_commessa) — chiamante: le attività fatturabili
>
> Guide:
>
> * [Framework di automazione DB — Le porte di manutenzione](/guide/automazione-db#le-porte-di-manutenzione) — quali porte ci sono e come si usano

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **la porta di manutenzione `p_chiave` è aperta per questa sessione?**
Una porta di manutenzione è una GUC che un trigger di protezione riconosce, per lasciar passare a
mano una correzione che il dominio rifiuta: una bonifica, un refuso, una cancellazione
forward-only. La funzione è il punto unico in cui si decide chi la può aprire e in cui resta la
traccia di ciò che ha forzato.

---

### La regola

La porta è aperta solo se valgono **tutte e due** le condizioni:

* la GUC `p_chiave` è accesa nella sessione: `on`, `true` o `1`, senza distinguere maiuscole e
  minuscole. Assente, vuota o con qualunque altro valore, è spenta;
* la sessione è del migratore, cioè
  [fn_sessione_del_migratore](/dbzero/dbops/funzioni/fn_sessione_del_migratore) risponde sì.

⭐ **Per l'applicazione la porta resta chiusa anche con la GUC accesa.** Il guard che la chiede decide
come se la GUC non ci fosse. È la differenza con com'era prima: ogni guard leggeva la GUC da sé, e
l'app che la accendeva con `SET LOCAL` saltava la protezione.

Quando la porta si apre, la funzione scrive una riga nel diario
[porte_manutenzione_passaggi](/dbzero/dbops/tabelle/porte_manutenzione_passaggi): chiave, tabella,
id della riga, operazione, ruolo di login.

---

### Dove si chiama

Nel punto in cui il controllo **rifiuterebbe**, non in testa al trigger. Così il diario registra le
righe che la porta ha davvero forzato, e non ogni scrittura fatta a GUC accesa: un `UPDATE` che non
tocca colonne protette non lascia traccia.

⚠️ **Le porte di verbo non passano di qui.** Una porta di verbo è una GUC che una funzione accende
per sé, dentro la propria transazione, per una scrittura che il dominio prevede (per esempio
`zeroerp.maintenance_reset_lotto_draft`, che `vendite.fn_cleanup_fatture_by_ids` accende per il
reset del lotto). Quella la legge il suo guard, con la sua regola: per il reset del lotto, la GUC
accesa e il proprietario della tabella, cioè la pulizia dentro i verbi del reset
([vendite.fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta)).
Chiuderla al migratore spegnerebbe una funzione dell'app.

---

### Perché `SECURITY DEFINER`

Scrive il diario, che l'applicazione legge soltanto. La domanda su chi scrive resta corretta lo
stesso: si legge `session_user`, che una `SECURITY DEFINER` non cambia. `search_path` è bloccato su
`pg_catalog, pg_temp`.

---

### Codici errore

* `E_GENERICO` — parametri obbligatori mancanti (chiave, tabella o operazione `NULL`).

---

### Test

* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql` — dalla sessione del migratore la porta
  si apre e lascia la riga nel diario.
* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql` — come applicazione, con la GUC
  accesa, la porta resta chiusa.
* `db/pgtap/vendite/test-righe-natura-vendita-legacy-v1.sql` — la natura di una riga scritta dalla
  porta del lucchetto, e il passaggio nel diario.
* `db/pgtap/dbops/test-seed-primo-impianto-postura-v1.sql` — `SECURITY DEFINER`, `search_path`
  bloccato, stesso proprietario del diario.

---

### Note di migrazione

* 2026-11-17 — nasce, e i cinque guard delle porte di manutenzione passano da qui
  (`brief-db-seed-primo-impianto-non-si-riscrive`). Prima ogni guard leggeva la GUC da sé, e solo
  quello delle attività fatturabili la limitava a un superuser.

---

{% include-markdown "signature-core.md" %}
