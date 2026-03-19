## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatture_log_sync_ai_stmt`
### 🎯 Scopo Principale
Sincronizza stato `critical` e `stato_esecuzione` delle fatture coinvolte
dopo INSERT su `vendite.fatture_log` (trigger statement-level).

---

### Regole principali

* raccoglie gli `fattura_id` distinti dalla transition table `new_table`;
* invoca `vendite.fn_sync_fatture_log_critical_lotto(v_ids)`;
* gestisce in batch tutte le fatture toccate nello statement.

---

### Effetto trigger

* trigger `AFTER INSERT ... FOR EACH STATEMENT`;
* ritorna `NULL` (comportamento standard statement trigger).

---

{% include-markdown "signature-core.md" %}

