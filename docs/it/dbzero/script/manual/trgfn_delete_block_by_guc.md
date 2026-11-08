## 📘 Documentazione Concettuale – Funzione `script.trgfn_delete_block_by_guc()`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_delete_block](/dbzero/dbops/tabelle/automation_delete_block) — il registro delle tabelle su cui il trigger si monta
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — il runner che porta i trigger allo stato del registro
> * [dbops.fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger) — il passo che monta il trigger
> * [dbops.fn_delete_block_divergenze](/dbzero/dbops/funzioni/fn_delete_block_divergenze) — riconosce i trigger vivi da questa funzione
>
> Guide:
>
> * [Framework di automazione DB, §4.4](/guide/automazione-db#44-delete_block-blocco-delete-con-guc) — la regola DELETE_BLOCK

---

### 🎯 Scopo Principale

La funzione trigger **generica** del blocco delle cancellazioni: rifiuta il `DELETE` di una riga,
salvo che la sessione abbia acceso un interruttore di manutenzione (una **GUC**). Il framework la
monta sulle tabelle di `dbops.automation_delete_block`, con un trigger `BEFORE DELETE` per riga.

---

### Regole applicate

* Il trigger riceve un argomento, la chiave della GUC (`guc_key`). Senza argomento la funzione
  solleva `E_TRIGGER_ARGOMENTI_INVALIDI`.
* Se la GUC vale `on` nella sessione, il `DELETE` passa.
* Altrimenti la funzione registra l'errore e rifiuta con `E_DELETE_NOT_ALLOWED`, con la tabella e
  l'`id` della riga.

⭐ Montata `BEFORE`, il rifiuto arriva prima delle cascate delle FK: i figli non vengono cancellati,
e nessun guard di un figlio parla al posto di `E_DELETE_NOT_ALLOWED`.

Dalla funzione, e dal suo argomento, il framework **riconosce** il blocco vivo, qualunque nome
abbia il trigger: un trigger su questa funzione che il registro non nomina ferma il runner.

---

### Codici errore

* `E_DELETE_NOT_ALLOWED` — cancellazione rifiutata, GUC spenta.
* `E_TRIGGER_ARGOMENTI_INVALIDI` — trigger montato senza la chiave della GUC.

---

### Note di migrazione

* 2026-01-23 — nasce, con il registro dei blocchi.
* 2026-11-08 — il framework la monta `BEFORE DELETE` invece di `AFTER DELETE`, e riconosce il
  blocco vivo da questa funzione e dal suo argomento (`brief-db-revisione-dbops`, giro 10c). La
  funzione non cambia.

---

{% include-markdown "signature-core.md" %}
