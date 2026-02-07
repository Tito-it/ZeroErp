## 📘 Documentazione Concettuale – Tabella `dbops.automation_lock_columns`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:  
> 
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)    
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)   
>
> Approfondimento funzioni:
> 
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns)   
>
> Approfondimento trigger:
> 
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)   

### 🎯 Scopo Principale

(latest review 10-01-26)
Centralizzare la configurazione delle **colonne extra** da bloccare con `script.trgfn_lock_columns`.

La colonna **`codice_interno` non si configura qui**: se presente nella tabella target,
il runner la include automaticamente nel trigger.

---

### 🔑 Campi chiave e semantica

* **`target_schema`** *(text)* – schema di destinazione.
* **`target_table`** *(text)* – tabella di destinazione.
* **`column_name`** *(text)* – colonna da bloccare.
* **`error_code`** *(text)* – codice errore (default `CODICE_NON_MODIFICABILE`).
* **`exec_mode`** *(text)* – `AUTO` | `CI` | `SCHEDULED`. Il runner applica la riga se `exec_mode='AUTO'`
  oppure `exec_mode = p_exec_mode`.
* **`enabled`** *(boolean)* – abilita/disabilita la riga.
* **`note`** *(text)* – note descrittive.
* **Audit** – `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### ⚙️ Comportamento del runner

`dbops.fn_run_automations_lock_columns`:

1. individua le tabelle in scope;
2. aggiunge `codice_interno` se presente;
3. aggiunge le colonne definite in `automation_lock_columns` (solo se esistono fisicamente);
4. crea **un unico trigger** per tabella con `UPDATE OF` sulle colonne effettive.

---

### ✍️ Esempi

**Bloccare una colonna extra con codice errore custom:**

```sql
INSERT INTO dbops.automation_lock_columns
  (target_schema, target_table, column_name, error_code, exec_mode, enabled, note)
VALUES
  ('config','utilities','categoria','CODICE_NON_MODIFICABILE','AUTO',true,'blocco categoria');
```

**Solo `codice_interno` (nessuna riga necessaria):**

> Se la tabella ha `codice_interno`, il trigger viene applicato automaticamente.

---

### 🧠 Best practice

* Inserisci qui solo le colonne **extra** non standard.
* Mantieni `exec_mode='AUTO'` salvo esigenze di rilascio controllato.
* Verifica che la colonna esista davvero, altrimenti il runner la ignora.

