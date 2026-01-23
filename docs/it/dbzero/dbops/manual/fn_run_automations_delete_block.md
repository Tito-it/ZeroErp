## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_delete_block`

> 👀 **Vedi anche**
>
> Guide:
> * [Automazione DB](/guide/automazione-db)
>
> Approfondimento tabelle:
> * [dbops.automation_delete_block](/dbzero/dbops/tabelle/automation_delete_block)
>
> Approfondimento funzioni:
> * [dbops.fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger)
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc)

---

### 🎯 Scopo Principale

(latest review 23-01-26)
La funzione **`dbops.fn_run_automations_delete_block(p_exec_mode, p_schemas, p_dry_run)`**
applica (o simula) i trigger **DELETE_BLOCK** sulle tabelle configurate in
`dbops.automation_delete_block`, con bypass via GUC.

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
2. Legge le righe **enabled** in `dbops.automation_delete_block` nello scope.
3. Se la tabella non esiste, registra un audit (dry‑run) e salta.
4. Se il trigger esiste già, non crea nulla.
5. Se `p_dry_run=true`, registra un audit; altrimenti richiama
   `dbops.fn_apply_delete_block_trigger`.

---

### 🧩 Trigger generato

* **Evento**: `DELETE` sulla tabella target.
* **Funzione**: `script.trgfn_delete_block_by_guc(guc_key)`.
* **Naming**: `trg_<tabella>_a10_delete_block_dlt` oppure `trigger_name` custom.

---

### ✅ Esempi di utilizzo

* **Simulazione**:
  `SELECT dbops.fn_run_automations_delete_block('AUTO', ARRAY['anagrafiche'], true);`

* **Esecuzione reale**:
  `SELECT dbops.fn_run_automations_delete_block('AUTO', NULL, false);`

---

### 🧠 Note

* In caso di errori DDL, la funzione usa `script.fn_log_and_raise_error`.
* Il bypass e' gestito dalla GUC configurata in `automation_delete_block`.

---

{% include-markdown "signature-core.md" %}
