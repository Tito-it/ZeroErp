## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_drop_lock_trg`

> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)
>
Approfondimento tabelle:  
> [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)
> [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)
>
Approfondimento funzioni:  
> [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns)
> [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)

---
### 🎯 Scopo Principale
La funzione **`dbops.fn_run_automations_drop_lock_trg(p_exec_mode, p_schemas, p_dry_run)`**
elimina i trigger **LOCK_COLUMNS** obsoleti, quando **non esistono colonne da bloccare**
(`codice_interno` assente e nessuna colonna extra attiva in `automation_lock_columns`).

---

### Parametri di input

| Parametro     | Tipo    | Descrizione                                  |
| ------------- | ------- | -------------------------------------------- |
| `p_exec_mode` | text    | Modalita' di esecuzione (AUTO/CI/SCHEDULED). |
| `p_schemas`   | text[]  | Schemi target (NULL = ambito risolto).       |
| `p_dry_run`   | boolean | Se true non esegue DDL ma registra audit.    |

---

### Logica operativa

1. Risolve l'ambito con `dbops.fn_resolve_scope(p_schemas)`.
2. Per ogni tabella nell'ambito:
   * verifica `codice_interno` (se presente => lock implicito);
   * verifica colonne extra attive in `dbops.automation_lock_columns`.
3. Se **non** esistono colonne da bloccare, rimuove i trigger
   che eseguono `script.trgfn_lock_columns` secondo le regole
   `LOCK_COLUMNS` di `dbops.automation_rules_tbl`.
4. In `p_dry_run = true` registra solo audit.

---

### Esempi di utilizzo

* **Simulazione**:
  `SELECT dbops.fn_run_automations_drop_lock_trg('AUTO', ARRAY['vendite'], true);`

* **Esecuzione reale**:
  `SELECT dbops.fn_run_automations_drop_lock_trg('AUTO', ARRAY['vendite'], false);`

---

### Note

* La funzione **non** sostituisce `fn_run_automations_lock_columns`:
  serve solo a rimuovere trigger non piu' necessari.
* Evita di mantenere trigger LOCK_COLUMNS su tabelle senza colonne
  da bloccare.

