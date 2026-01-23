## 📘 Documentazione Concettuale – Tabella `dbops.automation_delete_block`

> 👀 **Vedi anche**
>
> **Approfondimento funzioni:**    
>
> • [script.trgfn_delete_block_by_guc](/dbzero/script/manual/trgfn_delete_block_by_guc)    
> • [dbops.fn_apply_delete_block_trigger](/dbzero/dbops/manual/fn_apply_delete_block_trigger)    
>

---

### 🎯 Scopo Principale

(latest review 23-01-2026)
`dbops.automation_delete_block` centralizza la configurazione dei trigger che **bloccano**
le DELETE sulle tabelle sensibili (es. ruoli), con possibilità di bypass tramite **GUC**.

---

### 🔑 Campi chiave

* `schema_name`, `table_name`: tabella target.
* `guc_key`: chiave GUC che abilita il bypass (es. `zeroerp.maintenance_ruoli_delete`).
* `enabled`: abilita/disabilita la regola.
* `trigger_name`: nome trigger personalizzato (se NULL usa template standard).
* `meta`: estensioni e note operative.

---

### ✅ Ruolo operativo

1. Si inserisce una riga per ogni tabella da proteggere.
2. Un processo di automazione applica i trigger (vedi funzione dedicata).
3. In manutenzione o test, la GUC consente il bypass.

---

{% include-markdown "signature-core.md" %}
