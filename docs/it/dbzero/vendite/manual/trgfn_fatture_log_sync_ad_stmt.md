## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatture_log_sync_ad_stmt`

### 🎯 Scopo Principale

Sincronizza stato `critical` e `stato_esecuzione` delle fatture coinvolte
dopo DELETE su `vendite.fatture_log` (trigger statement-level).

---

### ✅ Regole principali

* raccoglie gli `fattura_id` distinti dalla transition table `old_table`;
* invoca `vendite.fn_sync_fatture_log_critical_lotto(v_ids)`;
* riallinea in batch le fatture impattate dalla cancellazione log.

---

### 🔄 Effetto trigger

* trigger `AFTER DELETE ... FOR EACH STATEMENT`;
* ritorna `NULL` (comportamento standard statement trigger).

---

{% include-markdown "signature-core.md" %}

