## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_delete_block_trigger()`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**    
>
• [script.trgfn_delete_block_by_guc](/dbzero/script/manual/trgfn_delete_block_by_guc)    
> • [dbops.automation_delete_block](/dbzero/dbops/manual/automation_delete_block)    
>
### 🎯 Scopo Principale
(latest review 23-01-2026)
`dbops.fn_apply_delete_block_trigger()` crea in modo programmato un **trigger di blocco DELETE**
su una tabella target, utilizzando un nome standard e una GUC di bypass.

---

### Regole applicate

* Se il trigger esiste, non viene ricreato.
* Se `trigger_name` non e` passato, usa il template:
  `trg_<tabella>_a10_delete_block_dlt`
* Il trigger invoca `script.trgfn_delete_block_by_guc(guc_key)`.

---

{% include-markdown "signature-core.md" %}
