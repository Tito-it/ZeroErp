## 📘 Documentazione Concettuale – Tabella `dbops.automation_rules_tbl`

> 👀 **Vedi anche**
>
> Approfondimento tabelle
> 
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)      
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols)
>       
>
> Approfondimento funzioni:  
> 
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)      
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)      
> 
> * Orchestratori: 
> 
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations), 
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id),   
> * [dbops.run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update),   
> * [dbops.run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico),   
>  * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo)
>  * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup)

### 🎯 Scopo Principale

**(latest review 13-01-26)**
Configurare **regole di automazione** per generare/applicare trigger e vincoli in modo dichiarativo. Ogni riga descrive **cosa** applicare (*rule_type*), **dove** (*target_schema/target_table*), **quando** (*exec_mode*), **come chiamarlo** (*name_template*), **come verificare l'esistenza** (*existence_strategy*), e **con quali parametri** (*params*).

Gli orchestratori leggono questa tabella e applicano le regole nell'ordine di **priority** (poi per `id`).

---

### 🔑 Campi chiave e semantica

* **enabled** *(boolean)* – abilita la regola.
* **rule_type** *(text)* – tipo di automatismo:

  * `TX_ID` → trigger `BEFORE INSERT/UPDATE` con `dbops.trgfn_tx_id_managed()` su tabelle che hanno `tx_id uuid`.
  * `AUDIT_UPDATE` → trigger `BEFORE UPDATE` con `script.trgfn_upd_audit_data_user_generic()`.
  * `STORICO` → trigger su `BEFORE UPDATE` e `BEFORE DELETE` verso `storico.<table>_storico` con `script.trgfn_upd_dlt_storico_generic(...)`.
  * `LOCK_COLUMNS` → trigger `BEFORE UPDATE OF ...` con `script.trgfn_lock_columns(...)` su colonne critiche.
  * `CLEANUP_AT` → calcolo `cleanup_at` con TTL fisso per tabella.
  * `CLEANUP_PURGE` → cancellazione record scaduti (batch) su `cleanup_at`.
* `ATTIVO` → set di trigger basati su FK: **block** sul padre + **require** sul figlio (no cascade).
* **target_schema** *(text)* – schema di destinazione.
* **target_table** *(text, opzionale)* – nome tabella **o pattern LIKE** (`%`) per filtrare. Se **NULL**, tutte le tabelle dello schema per quel *rule_type*.
* **exec_mode** *(text)* – `AUTO` | `CI` | `SCHEDULED`. L'orchestratore applica le regole con `exec_mode=p_exec_mode` **o** `AUTO`.
* **name_template** *(text)* – template del **nome trigger**. Placeholders disponibili:

  * `{schema}` `{table}` `{parent}` `{child}` `{fk}` `{op}` (`op` ∈ `upd|dlt`).
  * Per `ATTIVO` è un **JSON** con le chiavi operative `block` e `require` (la chiave `cascade` resta legacy/non operativa).
  * Default consigliati:

    * `TX_ID`: `trg_{table}_ins_upd_gen_tx_id`
    * `AUDIT_UPDATE`: `trg_upd_{table}_audit_data_user`
    * `STORICO`: `trg_{table}_{op}_storico`
    * `ATTIVO/block`: `trg_{parent}_a10_{child}_block_deact_upd`
    * `ATTIVO/require`: `trg_{child}_a10_{parent}_require_attivo_ins_upd`
* **existence_strategy** *(text)* – come determinare se il trigger esiste già:

  * `BY_NAME` → cerca per nome (derivato dal template);
  * `BY_FUNCTION` → cerca per funzione invocata (schema.nome);
  * `BOTH` → vero se almeno uno dei due è trovato.
* **params** *(jsonb)* – parametri specifici del *rule_type* (vedi sotto).
* **priority** *(int)* – ordine di applicazione (più basso = prima). A parità, ordinamento per `id`.
* **note** *(text)* – libero.
* **Audit** – `user_insert/data_insert`, `user_update/data_update` gestiti da trigger di audit.

> ℹ️ **Lunghezza nome trigger**: PostgreSQL limita a **63** caratteri. Se usi template lunghi, prevedi abbreviazioni o hashing nel naming helper (`fn_name_from_template`).

---

### 🧩 Parametri `params` per *rule_type*

* **TX_ID**: *(tipicamente vuoto)*
* **AUDIT_UPDATE**: `{ "audit_ts": "data_update", "audit_user": "user_update" }`
  (Sovrascrivibile anche via `automation_overrides_cols`)
* **STORICO**: *(tipicamente vuoto)*
  La FK dello storico può essere data da override `STORICO_FK` in `automation_overrides_cols`.
* **LOCK_COLUMNS**: *(tipicamente vuoto)*
  Usa `name_template` ed `existence_strategy` per il naming e l'idempotenza dei trigger di lock.
* **ATTIVO**:

  * `include_no_action` *(boolean, default true)* → considera anche FK `NO ACTION` oltre a `RESTRICT`.
  * (eventuali flag boolean: `cascade_children`, `require_active_parent`, `block_if_child_no_attivo` – default `true`).
  * **Nota**: nella policy ATTIVO corrente, questi flag non vengono letti dall’orchestratore; sono mantenuti per retro‑compatibilità e non influenzano il comportamento attuale (block + require).
* **CLEANUP_AT**:

  * `ttl_days` *(int, obbligatorio)* → giorni di retention.
  * `cleanup_column` *(text, default cleanup_at)* → colonna target.
  * `base_ts_column` *(text, opzionale)* → colonna timestamp base (fallback: data_insert/executed_at/occurred_at/created_at).
  * `apply_on_update` *(boolean, default false)* → ricalcola anche su righe già valorizzate.
* **CLEANUP_PURGE**:

  * `cleanup_column` *(text, default cleanup_at)* → colonna target.
  * `batch_limit` *(int, default 5000)* → dimensione batch.

---

### 🔗 Interazione con le altre tabelle

* **`automation_overrides_cols`** → risolve nomi di colonne non standard: `ATTIVO_COL`, `AUDIT_TS`, `AUDIT_USER`, `STORICO_FK`.
* **`automation_fk_exclusions`** → esclude specifiche coppie *parent/child* dalla regola `ATTIVO`.
* **`automation_cleanup_exclusions`** → esclude tabelle dal cleanup (rule_type CLEANUP_*).

---

### 🛠️ Comportamento degli orchestratori (riassunto)

* Scopo schemi: da `p_schemas` o tabella `dbops.automation_scope` (se presente), altrimenti tutti gli schemi *user* escluso `storico`.
* Per **TX_ID / AUDIT_UPDATE / STORICO**: loop per tabelle che matchano la regola (schema + table/pattern), valutano pre‑requisiti (colonne, storico presente), costruiscono nome via template, verificano esistenza secondo `existence_strategy`, **creano il trigger** se mancante (o **DRYRUN** se `p_dry_run=true`).
* Per **ATTIVO**: loop su **tutte** le FK nell'ambito (indipendentemente da `confdeltype`), filtra con `automation_fk_exclusions`, risolve colonne `attivo` su parent/child via overrides, poi applica:

  * **BLOCK** sul padre: impedisce `attivo=true -> false` se esistono figli **attivi** (o figli in generale se la colonna `attivo` sul figlio non esiste).
  * **REQUIRE** sul figlio: impedisce insert/update verso un padre non attivo. Se il figlio ha `attivo`, il controllo vale solo quando `attivo=true`.

**Nota**: **l’automazione ATTIVO viene applicata solo alle FK con colonna che termina in `_id`**; in caso contrario la regola viene saltata (per evitare riferimenti a codici testuali o chiavi non id).

Tutti i passaggi loggati in `dbops.audit_log` (`DRYRUN`/`OK`/`ERROR`).

---

### ✅ Esempi d'uso (seed minimal)

* Regola **TX_ID** per tutte le tabelle di `anagrafiche`:

```sql
INSERT INTO dbops.automation_rules_tbl(enabled, rule_type, target_schema, exec_mode, name_template, existence_strategy, params, priority, note)
VALUES (true, 'TX_ID', 'anagrafiche', 'AUTO', 'trg_{table}_ins_upd_gen_tx_id', 'BY_NAME', '{}'::jsonb, 100, 'txid di default');
```

* Regola **ATTIVO** per `vendite.%` (policy block):

```sql
INSERT INTO dbops.automation_rules_tbl(enabled, rule_type, target_schema, target_table, exec_mode, name_template, existence_strategy, params, priority)
VALUES (
  true, 'ATTIVO', 'vendite', '%%', 'AUTO',
  '{"block":"trg_{parent}_a10_{child}_block_deact_upd",
    "require":"trg_{child}_a10_{parent}_require_attivo_ins_upd"}',
  'BY_NAME', '{}'::jsonb, 100
);
```

---

### 🔍 Troubleshooting

* Nessun trigger creato? Controlla: `enabled=true`, *ambito* schemi corretto, `exec_mode` compatibile, `existence_strategy`, e pre‑requisiti (colonne/ storico/ FK).
* Conflitti di naming? Verifica la lunghezza (63 char) e l’univocità del template in combinazione con schema/tabella/FK.
* Debug rapido: guarda `dbops.audit_log` (filtra per `function_name='run_automations'` e `status IN ('DRYRUN','ERROR')`).

---


### 🔒 Vincoli & comportamento

* Ordinamento applicazione: `ORDER BY priority, id`.
* *exec_mode* filtro: la regola è valida se `exec_mode = p_exec_mode` **o** `exec_mode='AUTO'`.
* *target_table* può essere `NULL` → tutte le tabelle dello schema per quel *rule_type*.
* Per `ATTIVO`, `name_template` è JSON con i modelli `block` e `require`.

### 🧠 Best practice

* Mantieni template corti (<63 char finali) e coerenti con lo standard di progetto.
* Usa `params` per comportamenti opzionali specifici dei rule_type.
* Se servono eccezioni di naming, preferisci `automation_overrides_cols`.
* Tieni le regole **specifiche** (per schema e, se possibile, tabella) per evitare sorprese.

---

{% include-markdown "signature-core.md" %}
