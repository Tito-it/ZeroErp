## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_cleanup`

---

### 👀 Vedi anche

>**Guide**
>
[Automazione DB](/guide/automazione-db)
>
>**Approfondimento tabelle**
>
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
>* [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions)   
>* [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)   
>
>**Approfondimento funzioni**
>
[dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at)   
>* [dbops.fn_purge_cleanup_expired](/dbzero/dbops/funzioni/fn_purge_cleanup_expired)   
>
🎯 Scopo Principale

(latest review 07-02-26)
La funzione **`dbops.fn_run_automations_cleanup(p_exec_mode, p_schemas, p_dry_run)`** è l’orchestratore del framework di cleanup basato su `cleanup_at`.

Applica in modo coerente due regole dichiarative:

* **`CLEANUP_AT`**: calcolo di `cleanup_at` con TTL fisso.
* **`CLEANUP_PURGE`**: cancellazione dei record scaduti a batch.

---

### Parametri di input

| Parametro     | Tipo      | Descrizione                                              |
| ------------- | --------- | -------------------------------------------------------- |
| `p_exec_mode` | `text`    | Modalità di esecuzione (`AUTO`, `CI`, `SCHEDULED`).      |
| `p_schemas`   | `text[]`  | Schemi target. Se `NULL`, risolti da `fn_resolve_scope`. |
| `p_dry_run`   | `boolean` | Se `true`, non modifica i dati e registra audit DRYRUN.  |

---

### Flusso logico

1. Risolve l'**ambito** (`dbops.fn_resolve_scope`).
2. Scorre le tabelle nell'ambito (`dbops.fn_table_in_scope`).
3. Esclude le tabelle presenti in `dbops.automation_cleanup_exclusions`.
4. Applica le regole `CLEANUP_AT` e `CLEANUP_PURGE` compatibili con schema/tabella.
5. Registra l’esito in `dbops.audit_log` tramite `fn_audit_log_once`.

---

### 🧾 Parametri rule_type (JSON)

**CLEANUP_AT**

```json
{
  "ttl_days": 30,
  "cleanup_column": "cleanup_at",
  "base_ts_column": "data_insert",
  "apply_on_update": false
}
```

**CLEANUP_PURGE**

```json
{
  "cleanup_column": "cleanup_at",
  "batch_limit": 5000
}
```

---

### Note operative

* Se `cleanup_at` non esiste nella tabella target, la regola viene **ignorata**.
* `base_ts_column` è opzionale: se non indicata il runner tenta fallback su
  `data_insert`, `executed_at`, `occurred_at`, `created_at`.
* Le esclusioni con `enabled=true` hanno priorità su qualunque regola.
