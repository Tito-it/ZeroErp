## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_audit_update`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Guide:
>
[Automazione DB](/guide/automazione-db)
>
Approfondimento tabelle:
>
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
>
Approfondimento funzioni:
>
[dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)   
> [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope)  
> [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col)   
> [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)  

---
### 🎯 Scopo Principale
La funzione **`dbops.fn_run_automations_audit_update(p_exec_mode, p_schemas, p_dry_run)`** applica in modo automatico (o simula) la **regola di aggiornamento audit** sulle tabelle nell'ambito, creando – dove mancante secondo le policy – un **trigger BEFORE INSERT OR UPDATE** che aggiorna `data_update` e `user_update` tramite la funzione `script.trgfn_audit_data_user_generic()`.

---

### Parametri di input

| Parametro     | Tipo    | Obbligatorio | Descrizione                                                                    |
| ------------- | ------- | :----------: | ------------------------------------------------------------------------------ |
| `p_exec_mode` | text    |      ✔️       | Modalità di esecuzione (es. `AUTO`, `FORCE`, `CHECK`).                         |
| `p_schemas`   | text[]  |      ❌       | Ambito di schemi. Se `NULL`, determinato da `fn_resolve_scope`.                |
| `p_dry_run`   | boolean |      ✔️       | Se `true`, non crea i trigger ma registra un evento **DRYRUN** in `audit_log`. |

---

### Valore di ritorno

`void` – non ritorna valori; crea i trigger richiesti o produce log di simulazione.

---

### Flusso logico

1. **Ambito**: calcola gli schemi effettivi con `fn_resolve_scope` (se `p_schemas` è `NULL`).
2. **Scansione tabelle**: cicla tutte le tabelle nell'ambito (escluse quelle fuori `fn_table_in_scope`).
3. **Selezione regole**: per ciascuna tabella, filtra le regole abilitate in `automation_rules_tbl` con `rule_type='AUDIT_UPDATE'`, priorità e `exec_mode` coerenti.
4. **Risoluzione colonne**:

   * `col_ts`  = `fn_get_override_col(...,'AUDIT_TS',   COALESCE(params->>'audit_ts','data_update'))`
   * `col_user`= `fn_get_override_col(...,'AUDIT_USER', COALESCE(params->>'audit_user','user_update'))`
   * Verifica presenza colonne con `fn_col_exists`.
5. **Esistenza trigger**: valuta l’esistenza per **nome** e/o **funzione** secondo `existence_strategy` (`BY_NAME`, `BY_FUNCTION`, `BOTH`).
6. **Azione**:

   * **`p_dry_run = true`** → scrive evento `DRYRUN` via `fn_audit_log_once` (dettagliando tabella, nome trigger, azione prevista).
   * **`p_dry_run = false`** → esegue `CREATE TRIGGER ... EXECUTE FUNCTION script.trgfn_audit_data_user_generic()`.
7. **Error handling**: in caso di errore, invoca `script.fn_log_and_raise_error` con contesto `E_AUDIT_UPDATE`.

---

### Casi d’uso tipici

* **Allineamento post-deploy**: assicurarsi che tutte le tabelle operative abbiano il trigger di aggiornamento audit.
* **Refactoring**: dopo rinomini colonne audit (`AUDIT_TS`, `AUDIT_USER`) tramite override, ricreare i trigger coerenti.
* **Simulazione sicura**: validare in `dry_run` le azioni che verrebbero eseguite in produzione.

---

### Permessi e sicurezza

* Necessari privilegi DDL per creare trigger sulle tabelle target.
* In `dry_run` non sono richiesti privilegi di modifica dello schema.

---

### Esempi di utilizzo

* **Simulazione**: `SELECT dbops.fn_run_automations_audit_update('AUTO', ARRAY['anagrafiche'], true);`
* **Applicazione reale**: `SELECT dbops.fn_run_automations_audit_update('FORCE', NULL, false);`

---

### Considerazioni

* Il nome del trigger è derivato da `name_template` (es. `trg_{table}_audit_data_user_upd`), risolto con `fn_name_from_template`.
* Gli override consentono di supportare schemi legacy dove le colonne non si chiamano `data_update`/`user_update`.
* Integrare con policy di **retention** su `audit_log` per non accumulare eccessivi log di `DRYRUN`.

---

### Benefici

* **Coerenza**: applica in modo uniforme la politica di aggiornamento audit.
* **Automazione**: evita definizioni manuali e riduce errori umani.
* **Flessibilità**: supporta override di naming e modalità di esecuzione differenziate.

---

> **In sintesi**: `fn_run_automations_audit_update` è il modulo che garantisce l’aggiornamento affidabile dei metadati di audit (`data_update`, `user_update`) su tutte le tabelle nell'ambito, con possibilità di simulazione e gestione degli override.
