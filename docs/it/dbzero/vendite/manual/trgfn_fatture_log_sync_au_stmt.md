## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatture_log_sync_au_stmt`
### 🎯 Scopo Principale
Sincronizza stato `critical` e `stato_esecuzione` delle fatture coinvolte
dopo UPDATE su `vendite.fatture_log` (trigger statement-level).

---

### Regole principali

* costruisce l'insieme `fattura_id` unendo `new_table` e `old_table`;
* deduplica gli id fattura;
* invoca `vendite.fn_sync_fatture_log_critical_lotto(v_ids)`.

---

### Effetto trigger

* trigger `AFTER UPDATE ... FOR EACH STATEMENT`;
* ritorna `NULL` (comportamento standard statement trigger).

---

{% include-markdown "signature-core.md" %}

