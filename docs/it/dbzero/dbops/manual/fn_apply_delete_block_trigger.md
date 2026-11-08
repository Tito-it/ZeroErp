## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_delete_block_trigger`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_delete_block](/dbzero/dbops/tabelle/automation_delete_block) — il registro delle tabelle che non si cancellano
>
> Approfondimento funzioni:
>
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — la funzione che il trigger monta: blocca il `DELETE` salvo la GUC
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — il runner che la chiama per `CREA` e `RIGENERA`
> * [dbops.fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato) — il nome del trigger
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni

---

### 🎯 Scopo Principale

Monta su una tabella il trigger che ne blocca la cancellazione: un trigger `BEFORE DELETE` per riga
che chiama `script.trgfn_delete_block_by_guc` con la chiave della GUC che, accesa, lascia passare
il `DELETE`. È il passo che il runner `DELETE_BLOCK` esegue per le azioni `CREA` e `RIGENERA`.

---

### ⭐ `BEFORE`, non `AFTER`

Il rifiuto deve arrivare prima di ogni altra cosa: con un trigger `AFTER`, le FK con
`ON DELETE CASCADE` cancellavano i figli prima del rifiuto, e un guard di un figlio poteva
sollevare il suo errore al posto di `E_DELETE_NOT_ALLOWED`. Con `BEFORE` la riga del padre è
rifiutata prima che la cascata parta.

---

### Il nome del trigger

Il nome è quello passato dal chiamante o, se manca o è vuoto, il template
`trg_<tabella>_a10_delete_block_dlt`, risolti da
[fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato): oltre i 63
caratteri il nome si accorcia con un hash, ed è lo stesso nome che il confronto si aspetta.

---

### Ricrea sempre il trigger con quel nome

Un trigger con lo stesso nome sulla tabella si toglie e si crea di nuovo: la forma è sempre quella
di oggi, compresa la GUC. Gli altri trigger della stessa funzione sulla tabella, con altri nomi,
non li tocca: li toglie il runner, che sa dal confronto quali sono.

---

### Codici errore

* `E_GENERICO` — schema, tabella o chiave della GUC mancanti.

Il `DELETE` rifiutato dal trigger montato solleva `E_DELETE_NOT_ALLOWED`: è il codice di
`script.trgfn_delete_block_by_guc`, non di questa funzione.

---

### Test

* `db/pgtap/dbops/test-delete-block-convergenza-v1.sql` — dopo il giro c'è un trigger solo,
  `BEFORE DELETE` per riga, con la `guc_key` come argomento; un padre con un figlio in cascata è
  rifiutato con `E_DELETE_NOT_ALLOWED` e il figlio resta intatto; con la GUC accesa il `DELETE`
  passa.

---

### Note di migrazione

* 2026-01-23 — nasce, con il registro.
* 2026-11-08 — il trigger diventa `BEFORE DELETE` (era `AFTER`); il nome viene da
  `fn_nome_oggetto_dichiarato` invece di comporsi senza accorciarlo; un trigger con lo stesso nome
  si ricrea, invece di bastare a non fare niente (`20261109-97`, `brief-db-revisione-dbops`,
  giro 10c).

---

{% include-markdown "signature-core.md" %}
