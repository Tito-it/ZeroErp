## 📘 Documentazione Concettuale – Tabella `dbops.automazione_guard_utility_tipo_ruolo`
### 🎯 Scopo Principale
La tabella **`dbops.automazione_guard_utility_tipo_ruolo`** configura le tabelle
su cui applicare automaticamente il trigger di guardia
**utility -> tipo_ruolo**.

---

### Regole principali

* Una riga per tabella target (`schema_name`, `table_name`).
* `utility_column` indica la colonna utility (default `utility_id`).
* `soggetto_ruolo_column` indica la colonna ruolo (`soggetto_ruolo_id` o variante).
* Se `enabled=true`, la riga viene considerata da `fn_apply`.
* `exec_mode` consente di filtrare le applicazioni per contesto (`AUTO`, `CI`, ecc.).

---

### Flusso operativo

1. `dbops.fn_seed_automazione_guard_utility_tipo_ruolo(...)` popola/aggiorna la configurazione.
2. `dbops.fn_apply_automazione_guard_utility_tipo_ruolo(...)` crea i trigger.
3. Il trigger invoca `script.trgfn_guard_utility_tipo_ruolo_by_cols()`.
4. La trigger function delega a `script.fn_guard_utility_tipo_ruolo(...)`.

---

### Esempio d’uso

```sql
SELECT dbops.fn_seed_automazione_guard_utility_tipo_ruolo(ARRAY['anagrafiche']);
SELECT dbops.fn_apply_automazione_guard_utility_tipo_ruolo('AUTO', false);
```
