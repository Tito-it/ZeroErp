## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_lock_columns`

> 👀 **Vedi anche**
>
> Guide:
> * [Automazione DB](/guide/automazione-db)
>
> Approfondimento tabelle:
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)
>
> Approfondimento funzioni:
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)
>
> Approfondimento trigger:
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)

---

### 🎯 Scopo Principale

(latest review 10-01-26)
La funzione **`dbops.fn_run_automations_lock_columns(p_exec_mode, p_schemas, p_dry_run)`**
automatizza la creazione (o la simulazione) dei trigger **LOCK_COLUMNS** sulle tabelle in scope,
bloccando la modifica delle colonne critiche tramite `script.trgfn_lock_columns`.

---

### 🔍 Parametri di input

| Parametro     | Tipo    | Descrizione                                  |
| ------------- | ------- | -------------------------------------------- |
| `p_exec_mode` | text    | Modalita' di esecuzione (AUTO/CI/SCHEDULED). |
| `p_schemas`   | text[]  | Schemi target (NULL = scope risolto).        |
| `p_dry_run`   | boolean | Se true non crea trigger ma registra audit.  |

---

### ⚙️ Logica operativa

1. Risolve lo scope con `dbops.fn_resolve_scope(p_schemas)`.
2. Per ogni tabella in scope:
   * aggiunge `codice_interno` se presente;
   * aggiunge colonne extra definite in `dbops.automation_lock_columns` (enabled e compatibili con `exec_mode`).
3. Applica la regola `LOCK_COLUMNS` da `dbops.automation_rules_tbl` per:
   * `name_template` (default `trg_{table}_a10_lock_columns_upd`);
   * `existence_strategy` (BY_NAME/BY_FUNCTION/BOTH).
4. Crea **un solo trigger** per tabella:
   * `BEFORE UPDATE OF <colonne>`
   * `EXECUTE FUNCTION script.trgfn_lock_columns(<col,msgcode...>)`

---

### 🧩 Trigger generato

* **Evento**: `BEFORE UPDATE OF col1, col2, ...`
* **Funzione**: `script.trgfn_lock_columns('col1','ERR', 'col2','ERR', ...)`
* **Naming**: derivato dal template di regola `LOCK_COLUMNS`

---

### ✅ Esempi di utilizzo

* **Simulazione**:
  `SELECT dbops.fn_run_automations_lock_columns('AUTO', ARRAY['config'], true);`

* **Esecuzione reale**:
  `SELECT dbops.fn_run_automations_lock_columns('AUTO', NULL, false);`

---

### 🧠 Note

* `codice_interno` e' implicito: se presente viene sempre incluso.
* Le colonne extra vengono usate **solo se esistono** nella tabella.
* In caso di errori DDL, la funzione usa `script.fn_log_and_raise_error`.

