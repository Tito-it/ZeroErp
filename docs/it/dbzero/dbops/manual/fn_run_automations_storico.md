## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_storico`

> 👀 **Vedi anche**
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db)   
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
>
> Approfondimento funzioni e trigger:
>
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)    
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope)   
> * [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col)   
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)   

---

### 🎯 Scopo Principale

(latest review 26-12-25)
La funzione **`dbops.fn_run_automations_storico(p_exec_mode, p_schemas, p_dry_run)`** automatizza la creazione (o la simulazione) del **trigger unico di storicizzazione** `BEFORE UPDATE OR DELETE` per le tabelle applicative, delegando la logica alla funzione `script.trgfn_storico_generic`. È uno dei moduli orchestrati da `fn_run_automations`.

---

### 🔍 Parametri di input

| Parametro     | Tipo    | Obbligatorio | Descrizione                                                               |
| ------------- | ------- | :----------: | ------------------------------------------------------------------------- |
| `p_exec_mode` | text    |      ✔️       | Modalità di esecuzione delle regole (`AUTO`, `FORCE`, `CHECK`).           |
| `p_schemas`   | text[]  |      ❌       | Schemi nell'ambito. Se `NULL`, risolti da `fn_resolve_scope`.             |
| `p_dry_run`   | boolean |      ✔️       | Se `true`, non crea trigger ma registra eventi **DRYRUN** in `audit_log`. |

---

### 📤 Valore di ritorno

`void` – non restituisce valori; crea i trigger richiesti o produce log di simulazione.

---

### ⚙️ Flusso logico

1. **Ambito**: determina gli schemi effettivi con `fn_resolve_scope`; esclude sempre lo schema `storico`.
2. **Scansione tabelle**: per ogni tabella nell'ambito e in `fn_table_in_scope`, verifica che esista la **tabella omologa** nello schema `storico`.
3. **Regole**: seleziona da `automation_rules_tbl` le regole abilitate con `rule_type='STORICO'`, rispettando `exec_mode`, priorità e target (schema/tabella).
4. **Risoluzione FK storico**: calcola il nome della FK verso lo storico con `fn_get_override_col(...,'STORICO_FK', '{table}_id')`.
5. **Naming trigger**: usa `name_template` (default: `trg_z90_{table}_storico_upd_dlt`) tramite `fn_name_from_template`.
6. **Strategia esistenza**: controlla esistenza **per nome** e/o **per funzione** secondo `existence_strategy` (`BY_NAME`, `BY_FUNCTION`, `BOTH`).
7. **Azione**:

   * `p_dry_run=true` → registra evento `DRYRUN_CREATE_TRIGGER_UD` con `fn_audit_log_once`.
   * `p_dry_run=false` → esegue `CREATE TRIGGER ... EXECUTE FUNCTION script.trgfn_storico_generic(fk_col)`; gestisce duplicate con log `SKIP_EXISTS`.
8. **Pulizia legacy (opz.)**: se `params->>'drop_legacy_ud' = true`, rimuove eventuali vecchi trigger separati `upd/dlt`.

---

### 🧩 Casi d’uso tipici

* **Uniformare la storicizzazione**: passare da due trigger separati (UPDATE/DELETE) a un **unico trigger** standard.
* **Post‑deploy**: applicare la regola a tutte le nuove tabelle con storico presente.
* **Simulazione**: validare impatto in `dry_run` prima di intervenire in produzione.

---

### 🛡️ Permessi e sicurezza

* Richiede privilegi DDL sulle tabelle target.
* In `dry_run` non modifica oggetti, utile per audit/analisi preventiva.

---

### 🚀 Esempi di utilizzo

* **Simulazione**: `SELECT dbops.fn_run_automations_storico('AUTO', ARRAY['anagrafiche'], true);`
* **Applicazione**: `SELECT dbops.fn_run_automations_storico('FORCE', NULL, false);`

---

### 📌 Considerazioni

* La presenza dell’omologo nello schema `storico` è prerequisito: in caso contrario, il trigger non viene creato.
* `name_template` e `existence_strategy` rendono la regola adattabile a naming legacy o transizioni graduali.
* È possibile abilitare una **pulizia “vecchi nomi”** per completare la migrazione allo standard unico `upd+dlt`.

---

### ✅ Benefici

* **Coerenza**: stessa semantica di storicizzazione su tutte le tabelle.
* **Manutenibilità**: un solo trigger da gestire, con logica centralizzata.
* **Sicurezza operativa**: supporto `dry_run` e gestione duplicati con log espliciti.

---

> 🧠 **In sintesi**: `fn_run_automations_storico` è il modulo che standardizza la **storicizzazione** in Zero ERP, creando in modo idempotente il trigger unico `UPDATE OR DELETE` basato su `trgfn_storico_generic`.
