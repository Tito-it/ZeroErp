## 📘 Documentazione Concettuale – Funzione `script.trgfn_delete_block_by_guc()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [dbops.automation_delete_block](/dbzero/dbops/manual/automation_delete_block)    
>

🎯 Scopo Principale

(latest review 23-01-2026)
La funzione `script.trgfn_delete_block_by_guc()` e` una **trigger function generica**
che blocca le DELETE, consentendo il bypass tramite una **GUC** di manutenzione.

---

### Regole applicate

* Il trigger riceve un argomento: `guc_key`.
* Se `current_setting(guc_key) = 'on'`, la DELETE e` permessa.
* In caso contrario, la funzione logga e blocca con `script.fn_log_and_raise_error(...)`.

---

{% include-markdown "signature-core.md" %}
