## 📘 Documentazione Concettuale – Tabella `dbops.porte_manutenzione_passaggi`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_porta_manutenzione_aperta](/dbzero/script/funzioni/fn_porta_manutenzione_aperta) — l'unica che la scrive, quando una porta si apre
>
> Guide:
>
> * [Framework di automazione DB — Le porte di manutenzione](/guide/automazione-db#le-porte-di-manutenzione) — quali porte ci sono e come si usano

---

### 🎯 Scopo Principale

Il **diario** delle porte di manutenzione: una riga per ogni riga che una porta ha lasciato passare.
Risponde alla domanda «chi ha forzato questa protezione, su quale riga, quando», che un trigger
saltato a GUC accesa non lascerebbe da nessuna parte.

---

### Una riga per passaggio

* `chiave` — la GUC della porta (per esempio `zeroerp.allow_lock_columns_override`).
* `schema_name`, `table_name`, `riga_id` — la riga forzata. `riga_id` è testo: le tabelle non hanno
  tutte la stessa chiave.
* `operazione` — `UPDATE` o `DELETE`, l'operazione del trigger.
* `utente_sessione` — il ruolo di login (`session_user`), cioè chi ha aperto la porta.
* `data_insert`, `user_insert`, `tx_id` — quando, e in quale transazione.

---

### Chi la scrive

Solo [fn_porta_manutenzione_aperta](/dbzero/script/funzioni/fn_porta_manutenzione_aperta), nel
momento in cui la porta si apre: GUC accesa e sessione del migratore. L'applicazione la legge
soltanto. La porta si chiede dove il controllo rifiuterebbe, quindi qui ci sono le righe davvero
forzate, non ogni scrittura fatta a GUC accesa.

⚠️ Le porte di verbo, che una funzione apre per sé dentro un suo processo, non lasciano righe qui.

---

### Test

* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql` — il passaggio dalla porta del seed.
* `db/pgtap/vendite/test-righe-natura-vendita-legacy-v1.sql` — il passaggio dalla porta del
  lucchetto.
* `db/pgtap/dbops/test-seed-primo-impianto-postura-v1.sql` — all'applicazione solo `SELECT`.

---

### Note di migrazione

* 2026-11-17 — nasce con la porta stretta al migratore
  (`brief-db-seed-primo-impianto-non-si-riscrive`).

---

{% include-markdown "signature-core.md" %}
