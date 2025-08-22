## 📘 Documentazione Concettuale – Tabella `dbops.automation_fk_exclusions`

> 👀 **Vedi anche**
>
> * `dbops.run_automations` (orchestratore)
> * Regola **ATTIVO / soft-delete** (funzioni: `trgfn_soft_delete_cascade`, `trgfn_child_requires_active_parent`, `trgfn_prevent_deactivate_if_children`)

### 🎯 Scopo

`dbops.automation_fk_exclusions` elenca le **coppie Padre/Figlio** (schema/tabella) da **escludere** dalla regola automatica **ATTIVO** (soft-delete):

* niente trigger di **cascade** sul padre,
* niente trigger di **require** sul figlio,
* niente trigger di **block** sul padre quando il figlio non ha `attivo`.

Serve per gestire **eccezioni** (integrazioni, tabelle legacy, esigenze di performance, rollout graduali).

---

### 🔧 Come funziona nell’orchestratore

Durante l’esecuzione di `fn_run_automations_attivo`, per ogni FK **NO ACTION/RESTRICT** tra *parent* e *child*, se esiste una riga in `automation_fk_exclusions` che combacia con:

```
(parent_schema, parent_table, child_schema, child_table)
```

allora la relazione è **saltata**: non vengono creati/aggiornati i trigger ATTIVO su quel legame.

> Match esatto dei nomi (in lowercase/non quoted lato DB).

---

### ✅ Quando usarla

* **Eccezioni funzionali**: il figlio deve restare indipendente dallo stato `attivo` del padre.
* **Performance**: relazioni molto dense dove i trigger di soft-delete non sono desiderati.
* **Rollout graduale**: esclusione temporanea durante migrazioni/refactoring.

---

### ✍️ Esempio di esclusione

```sql
INSERT INTO dbops.automation_fk_exclusions(
  parent_schema, parent_table,
  child_schema,  child_table,
  note
) VALUES (
  'anagrafiche','soggetti',
  'anagrafiche','soggetti_ruoli',
  'Esclusione temporanea: gestione attivo demandata al servizio X'
);
```

> Dopo l’inserimento, riesegui l’automazione con `p_parts=>ARRAY['ATTIVO']` (prima **dry-run**, poi **apply**).

---

### 🧩 Convenzioni

* Chiave primaria **composita**: `(parent_schema, parent_table, child_schema, child_table)`.
* Campi audit: `user_insert/data_insert`, `user_update/data_update`.
* Trigger audit consigliato: `script.trgfn_upd_audit_data_user_generic()` sul **BEFORE UPDATE**.

---

### 🔍 Note operative

* Il match è esatto su `(schema,tabella)`; per esclusioni massive per schema valuta tabelle di comodo o popolamento batch.
* L’inserimento di una riga **non** rimuove trigger già creati: riesegui l’orchestratore `ATTIVO` per applicare l’esclusione.
* Usa `dbops.audit_log` per tracciare le esecuzioni (`status=DRYRUN/OK/ERROR`, `rule_type='ATTIVO'`).
