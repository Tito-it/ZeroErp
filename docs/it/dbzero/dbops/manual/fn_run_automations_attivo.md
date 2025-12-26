## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_attivo`

> 👀 **Vedi anche**
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db)
>
> Approdondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)
> * [dbops.automation_fk_exclusions](/dbzero/dbops/tabelle/automation_fk_exclusions)
>
> Approfondimento funzioni e trigger:
>
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)
> * [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col)
> * [dbops.fn_get_child_fk_col](/dbzero/dbops/funzioni/fn_get_child_fk_col)
> * [dbops.trgfn_soft_delete_cascade](/dbzero/dbops/funzioni/trgfn_soft_delete_cascade)
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)

---

### 🎯 Scopo Principale

(latest review 26-12-25)
La funzione **`dbops.fn_run_automations_attivo(p_exec_mode, p_schemas, p_dry_run)`** applica in modo automatico le regole di gestione della colonna **`attivo`** (soft-delete / stato di validità) sulle tabelle e relazioni con vincoli di chiave esterna. È uno dei moduli eseguiti da `fn_run_automations`.

---

### 🔍 Parametri di input

| Parametro     | Tipo    | Obbligatorio | Descrizione                                                                     |
| ------------- | ------- | :----------: | ------------------------------------------------------------------------------- |
| `p_exec_mode` | text    |      ✔️       | Modalità di esecuzione (AUTO, FORCE, CHECK).                                    |
| `p_schemas`   | text\[] |      ❌       | Schemi su cui applicare le regole. Se NULL, risolti tramite `fn_resolve_scope`. |
| `p_dry_run`   | boolean |      ✔️       | Se true, non applica modifiche ma registra solo azioni simulate.                |

---

### 📤 Valore di ritorno

`void` – non restituisce valori ma applica trigger o logga le azioni previste.

---

### ⚙️ Flusso logico

1. Determina lo **scope degli schemi** tramite `fn_resolve_scope`.
2. Recupera da `automation_rules_tbl` le regole di tipo `ATTIVO` abilitate per lo scope.
3. Per ogni vincolo FK con `ON DELETE RESTRICT` o `NO ACTION`:

   * Verifica la presenza della colonna `attivo` sul padre e/o sul figlio (anche tramite override configurato).
   * Costruisce i nomi dei trigger usando i template configurati.
   * Applica le strategie di creazione (`BY_NAME`, `BY_FUNCTION`, `BOTH`).

### Casi gestiti

* **CASO A**: Padre e Figlio hanno la colonna `attivo` →

  * Padre: trigger `AFTER UPDATE OF attivo` → `trgfn_soft_delete_cascade`.
  * Figlio: constraint trigger deferrable → `trgfn_child_requires_active_parent`.
* **CASO B**: Solo il Padre ha la colonna `attivo` →

  * Trigger `BEFORE UPDATE OF attivo` → `trgfn_prevent_deactivate_if_children`.

4. Se `p_dry_run = true`, non crea i trigger ma registra un evento `DRYRUN` in `audit_log` tramite `fn_audit_log_once`.

---

### 🧩 Casi d’uso tipici

* **Soft-delete controllato**: impedire la disattivazione di record padre con figli attivi.
* **Allineamento automatico**: garantire che tutte le tabelle rispettino la policy sul campo `attivo`.
* **Simulazione**: in ambiente di test è possibile verificare le azioni senza applicarle.

---

### 🛡️ Permessi e sicurezza

* Richiede privilegi DDL per creare trigger sugli schemi target.
* In modalità `dry_run` può essere eseguita con permessi ridotti, in quanto non modifica oggetti.

---

### 🚀 Esempi di utilizzo

* `SELECT dbops.fn_run_automations_attivo('AUTO', ARRAY['catalogo'], true);` → Simula le regole ATTIVO sullo schema `catalogo` senza creare trigger.
* `SELECT dbops.fn_run_automations_attivo('FORCE', NULL, false);` → Applica realmente le regole ATTIVO su tutti gli schemi in scope.

---

### 📌 Considerazioni

* Gli **override di colonna** permettono di gestire casi in cui la colonna non si chiama `attivo` ma ha nomi alternativi (es. `enabled`, `is_active`).
* Le regole possono essere escluse con `automation_fk_exclusions`.
* La generazione dei nomi trigger è parametrizzabile tramite JSON di `name_template`.

---

### ✅ Benefici

* **Coerenza**: uniforma la gestione del campo `attivo` in tutte le relazioni.
* **Automazione**: elimina la necessità di definire manualmente trigger di protezione.
* **Flessibilità**: supporta configurazioni personalizzate e modalità di simulazione.

---

> 🧠 **In sintesi**: `fn_run_automations_attivo` automatizza la creazione dei trigger legati al campo `attivo`, assicurando che le politiche di soft-delete e validità dei dati siano applicate in modo consistente e controllato.
