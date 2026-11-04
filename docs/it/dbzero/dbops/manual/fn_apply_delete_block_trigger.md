## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_delete_block_trigger`

> **Ultimo aggiornamento**: 4 novembre 2026
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
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — il runner che la chiama per ogni riga del registro
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni

---

### 🎯 Scopo Principale

Monta su una tabella il trigger che ne blocca la cancellazione: un trigger `AFTER DELETE` per riga
che chiama `script.trgfn_delete_block_by_guc` con la chiave della GUC che, accesa, lascia passare
il `DELETE`. È il passo del runner `DELETE_BLOCK`; se il trigger c'è già, non fa niente.

---

### Il nome del trigger

Il nome è quello passato dal chiamante o, se manca o è vuoto, `trg_<tabella>_a10_delete_block_dlt`.

⚠️ Il nome si compone senza il building block dei nomi generati, che tronca e aggiunge un hash: con
una tabella dal nome lungo il nome supera i 63 caratteri, PostgreSQL lo tronca alla creazione, e
il controllo di esistenza — fatto sul nome intero — non lo ritrova più.

---

### C'è già vuol dire «c'è un trigger con quel nome»

L'esistenza si controlla solo per nome, sulla tabella. Un trigger con lo stesso nome e un'altra
funzione basta a non montare niente; un trigger con la stessa funzione e un altro nome non basta, e
la tabella ne riceve un secondo.

La GUC del trigger è quella della prima creazione: cambiare la chiave nel registro non cambia un
trigger già montato.

---

### Codici errore

* `E_GENERICO` — schema, tabella o chiave della GUC mancanti.

Il `DELETE` rifiutato dal trigger montato solleva `E_DELETE_NOT_ALLOWED`: è il codice di
`script.trgfn_delete_block_by_guc`, non di questa funzione.

---

{% include-markdown "signature-core.md" %}
