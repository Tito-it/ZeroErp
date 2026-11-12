## 📘 Documentazione Concettuale – Tabella `dbops.automation_delete_block`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito: una riga fuori ambito non monta niente
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — il giro che porta i blocchi allo stato del registro
> * [dbops.fn_delete_block_divergenze](/dbzero/dbops/funzioni/fn_delete_block_divergenze) — il confronto fra il blocco atteso e quello vivo
> * [dbops.fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger) — monta il trigger su una tabella
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — la funzione del trigger, che rifiuta la cancellazione
> * [maintenance.proc_automations_delete_block_job](/dbzero/maintenance/funzioni/proc_automations_delete_block_job) — il wrapper del processo
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Il registro delle tabelle su cui una cancellazione è **vietata**, salvo che la sessione abbia
acceso un interruttore (`guc_key`). Il giro delle automazioni legge il registro e monta su ogni
tabella il trigger che rifiuta la `DELETE` con `E_DELETE_NOT_ALLOWED`.

Il seed lo usa per le tabelle dei **ruoli** dei soggetti (clienti, fornitori, gestori, vettori…):
un ruolo non si cancella, si chiude. L'interruttore, per tutte, è
`zeroerp.maintenance_ruoli_delete`, ed è una porta di manutenzione, non una strada del dominio.

---

### Una riga per tabella

La chiave naturale è (`schema_name`, `table_name`): una tabella ha una sola regola di blocco.

* `guc_key` — il nome del parametro di sessione che, se vale `on`, lascia passare la
  cancellazione. Finisce come argomento del trigger.
* `trigger_name` — il nome del trigger, se non si vuole quello del template
  (`trg_<tabella>_a10_delete_block_dlt`). `NULL` vuol dire template, e la stringa vuota la rifiuta
  il `CHECK` `chk_automation_delete_block_trigger_name_non_vuoto`; il nome lo risolve
  [fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato), che lo
  accorcia con un hash oltre i 63 caratteri.
* `enabled` — acceso, la tabella ha il blocco; spento, il giro lo toglie.
* `meta` — note libere. Il seed vi scrive il codice del ruolo che la tabella rappresenta; nessuna
  funzione lo legge.

---

### ⭐ Il registro è lo stato: il giro converge

Il giro porta i blocchi vivi a quelli che il registro dichiara, con il confronto di
[fn_delete_block_divergenze](/dbzero/dbops/funzioni/fn_delete_block_divergenze). Un blocco si
riconosce dalla funzione che esegue e dal suo argomento, non dal nome:

* una riga accesa senza blocco → il blocco si **crea**, `BEFORE DELETE` per riga;
* una riga accesa con un blocco diverso (nome, momento, `guc_key`, abilitazione, più di un
  trigger) → il blocco si **rigenera**. Cambiare `guc_key` o `trigger_name` arriva quindi sul
  trigger al giro dopo;
* una riga **spenta** (`enabled` falso) → il blocco si **toglie**.

⛔ **Per togliere un blocco si spegne la riga, non la si cancella.** Un blocco vivo su una tabella
che il registro non nomina ferma il giro con `E_DELETE_BLOCK`, che lo nomina: toglierlo
cancellerebbe in silenzio una protezione nata fuori dal registro.

Una tabella che non esiste più si salta, con un `WARN TABLE_NOT_FOUND` in audit nel dry run come
nella corsa vera. Ogni azione della corsa vera lascia una riga `OK`.

---

### ⭐ `BEFORE`, prima delle cascate

Il blocco scatta **prima** della cancellazione: il rifiuto (`E_DELETE_NOT_ALLOWED`) arriva prima
che le FK con `ON DELETE CASCADE` cancellino i figli e prima che un guard di un figlio possa
parlare al posto suo.

---

### Note di migrazione

* 2026-01-23 — nasce, con il seed delle otto tabelle dei ruoli dei soggetti.
* 2026-11-04 — la corsa vera scrive l'audit: `OK` per ogni trigger montato, `WARN TABLE_NOT_FOUND`
  per ogni tabella sparita (D41 di `brief-db-revisione-dbops`).
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).
* 2026-11-08 — il giro converge: crea, rigenera, toglie, e si ferma su un blocco che il registro
  non nomina. Il trigger diventa `BEFORE DELETE`: con `AFTER` le cascate delle FK cancellavano i
  figli prima del rifiuto. Al primo giro dopo l'aggiornamento i blocchi esistenti si rigenerano
  `BEFORE`. Prima `enabled` falso lasciava il trigger montato, e cambiare `trigger_name` ne
  montava un secondo (`brief-db-revisione-dbops`, giro 10c).

---

{% include-markdown "signature-core.md" %}
