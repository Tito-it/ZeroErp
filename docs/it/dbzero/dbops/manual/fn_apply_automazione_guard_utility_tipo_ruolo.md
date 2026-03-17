## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_automazione_guard_utility_tipo_ruolo`

### 🎯 Scopo Principale

La funzione **`dbops.fn_apply_automazione_guard_utility_tipo_ruolo(p_exec_mode, p_dry_run)`**
crea in modo idempotente i trigger di guardia utility/ruolo sulle tabelle
configurate in `dbops.automazione_guard_utility_tipo_ruolo`.

---

### Regole principali

* Applica solo righe `enabled=true`.
* Rispetta `exec_mode` (`AUTO` sempre ammesso).
* Valida che le colonne configurate esistano nella tabella.
* In `p_dry_run=true` non crea trigger.
* In `p_dry_run=false` esegue:
  * `DROP TRIGGER IF EXISTS ...`
  * `CREATE TRIGGER ... BEFORE INSERT OR UPDATE OF ...`

---

### Esempio d’uso

```sql
SELECT dbops.fn_apply_automazione_guard_utility_tipo_ruolo('CI', false);
```
