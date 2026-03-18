## 📘 Documentazione Concettuale – Tabella `dbops.automation_cleanup_exclusions`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
> [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)    
>
Approfondimento funzioni:
>
[dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup)    

La tabella **`dbops.automation_cleanup_exclusions`** contiene l’elenco delle **tabelle escluse** dal framework di cleanup basato su `cleanup_at`.

---
### 🎯 Scopo Principale
(latest review 07-02-26)
* Consentire esclusioni esplicite dal **calcolo `cleanup_at`** e dalla **purge**.
* Fornire tracciabilità e motivazione (`reason`) delle eccezioni.

---

### Campi chiave

* **`schema_name`**: schema della tabella esclusa.
* **`table_name`**: tabella esclusa.
* **`enabled`**: se `true` l’esclusione è attiva.
* **`reason`**: motivazione dell’esclusione.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Effetto sul runner

`dbops.fn_run_automations_cleanup`:

1. Risolve le tabelle nell'ambito.
2. **Salta** quelle presenti in `automation_cleanup_exclusions` con `enabled=true`.
3. Logga su `dbops.audit_log` con stato `SKIP_EXCLUDED`.

---

### Esempio

```sql
INSERT INTO dbops.automation_cleanup_exclusions
  (schema_name, table_name, enabled, reason)
VALUES
  ('dbops', 'audit_log', true, 'Conservazione estesa per audit legale');
```
