## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_tx_id`

> 👀 **Vedi anche**
>
Guide:
>
[Gestione Transaction ID](/guide/tx_id_implementation_guide)  
> [Automazione DB](/guide/automazione-db)  
>
Approfonsimento tabelle:
>
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
>
Approfondimento funzioni:
>
[dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)   
> [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope)    
> [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template)   
> [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name)   
> [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function)   
> [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)    
>

🎯 Scopo Principale

(latest review 26-12-25)
La funzione **`dbops.fn_run_automations_tx_id(p_exec_mode, p_schemas, p_dry_run)`** automatizza la creazione (o la simulazione) del **trigger di gestione `tx_id`** (`BEFORE INSERT OR UPDATE`) sulle tabelle applicative che possiedono una colonna `tx_id uuid`. Il trigger invoca `dbops.trgfn_tx_id_managed()` per generare/propagare l’ID di transazione.

---

### Parametri di input

| Parametro     | Tipo    | Obbligatorio | Descrizione                                                                  |
| ------------- | ------- | :----------: | ---------------------------------------------------------------------------- |
| `p_exec_mode` | text    |      ✔️       | Modalità di esecuzione (`AUTO`, `FORCE`, `CHECK`).                           |
| `p_schemas`   | text[]  |      ❌       | Ambito di schemi. Se `NULL`, determinato da `fn_resolve_scope`.              |
| `p_dry_run`   | boolean |      ✔️       | Se `true`, non crea trigger ma registra un evento **DRYRUN** in `audit_log`. |

---

### Valore di ritorno

`void` – non restituisce valori; crea i trigger necessari o produce log di simulazione.

---

### Flusso logico

1. **Ambito**: calcola gli schemi effettivi con `fn_resolve_scope` (se `p_schemas` è `NULL`).
2. **Scansione tabelle**: itera tutte le tabelle “user” nell'ambito (`fn_table_in_scope`).
3. **Selezione regole**: per ciascuna tabella, filtra le regole abilitate in `automation_rules_tbl` con `rule_type='TX_ID'`, rispettando `exec_mode`, priorità e target (schema/tabella).
4. **Presenza colonna**: verifica che esista la colonna `tx_id uuid`.
5. **Naming trigger**: risolve il nome con `fn_name_from_template` (default `trg_{table}_ins_upd_gen_tx_id`).
6. **Strategia esistenza**:

   * `BY_NAME`: usa `fn_trigger_exists_by_name`.
   * `BY_FUNCTION`: usa `fn_trigger_exists_by_function(...,'dbops','trgfn_tx_id_managed')`.
   * `BOTH`: richiede che almeno uno dei due controlli sia vero.
7. **Azione**:

   * `p_dry_run=true` → registra evento `DRYRUN_CREATE_TRIGGER` via `fn_audit_log_once` (con dettagli di tabella e trigger).
   * `p_dry_run=false` → crea il trigger `BEFORE INSERT OR UPDATE ... EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` con `EXECUTE format`.
8. **Error handling**: intercetta eccezioni ed invoca `script.fn_log_and_raise_error('E_TX_ID', ...)` con contesto.

---

### Casi d’uso tipici

* **Allineamento post‑deploy**: garantire che tutte le tabelle con `tx_id` abbiano il trigger di gestione coerente.
* **Refactoring**: dopo l’introduzione della colonna `tx_id` in nuove tabelle, applicare automaticamente la policy.
* **Simulazione**: in `dry_run` validare l’impatto senza eseguire DDL.

---

### Permessi e sicurezza

* Richiede privilegi DDL per creare trigger.
* In `dry_run` non modifica oggetti (utile per pipeline CI o analisi su ambienti restrittivi).

---

### Esempi di utilizzo

* **Simulazione**: `SELECT dbops.fn_run_automations_tx_id('AUTO', ARRAY['anagrafiche'], true);`
* **Applicazione reale**: `SELECT dbops.fn_run_automations_tx_id('FORCE', NULL, false);`

---

### Considerazioni

* Il controllo di esistenza è flessibile grazie a `existence_strategy` (compatibile con ambienti legati a naming legacy).
* Il template del nome trigger può essere personalizzato via `name_template` in `automation_rules_tbl`.
* Si integra con il framework di **audit** (`fn_audit_log_once`) per tracciare simulazioni e azioni reali.

---

### Benefici

* **Coerenza**: applica in modo uniforme la gestione di `tx_id` su tutto l'ambito.
* **Automazione**: riduce al minimo gli interventi manuali.
* **Flessibilità**: supporta nomi e strategie di esistenza personalizzabili.

---

> **In sintesi**: `fn_run_automations_tx_id` è il modulo che garantisce la **presenza e la corretta gestione del `tx_id`** in tutte le tabelle interessate, con supporto a simulazione, naming template e strategie di idempotenza.
