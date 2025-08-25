# 📗 Guida Tecnica – Automazioni DB

> 📋 **Destinatari:** sviluppatori database, backend, devops
>
> 👀 **Vedi anche:**
>
> * Tabelle: `dbops.automation_rules_tbl`, `dbops.automation_overrides_cols`, `dbops.automation_fk_exclusions`, `dbops.automation_scope`, `dbops.audit_log`
> * Funzioni orchestratore: `dbops.fn_run_automations`, `dbops.run_automations_tx_id`, `dbops.run_automations_audit_update`, `dbops.run_automations_storico`, `dbops.fn_run_automations_attivo`
> * Trigger/Helpers: `dbops.trgfn_tx_id_managed`, `script.trgfn_upd_audit_data_user_generic`, `script.trgfn_upd_dlt_storico_generic`, `dbops.trgfn_soft_delete_cascade`, `dbops.trgfn_child_requires_active_parent`, `dbops.trgfn_prevent_deactivate_if_children`
> * Logging: `dbops.audit_log` (+ dblink `logconn` via `script.fn_ensure_logconn`)

---

## 1) 🎯 Perché un framework di automazione

### Esigenza

In Zero ERP molte attività DB sono **ripetitive** e **basate su convenzioni**: assegnare `tx_id`, aggiornare `data_update/user_update`, gestire storico, propagare `attivo` su relazioni padre/figlio. Farlo a mano è costoso, introduce **incoerenze** e rallenta il delivery.

### Idea di fondo

Rendere queste attività **dichiarative**: invece di scrivere N trigger per M tabelle, l’owner dichiara *cosa* vuole (regola), *dove* applicarla (scope) e *come* chiamarla (template). L’orchestratore traduce la configurazione in trigger/constraint coerenti, idempotenti e osservabili.

**Obiettivi**

* **Coerenza**: stessi nomi, stesse funzioni, stesse condizioni di attivazione.
* **Velocità**: onboarding immediato di nuove tabelle/schema con poche righe di config.
* **Sicurezza**: dry‑run, audit strutturato, strategie di esistenza configurabili.
* **Flessibilità**: override di colonne non standard e esclusioni puntuali.

---

## 2) 🧩 Architettura logica

```
┌────────────────────┐        ┌────────────────────────────┐
│ automation_scope   │  →     │ fn_run_automations*        │
└────────────────────┘        │  (orchestratori modulari)  │
          │                   └────────────────────────────┘
          │                           │
          ▼                           ▼
┌────────────────────┐       ┌──────────────────────────────┐
│ automation_rules   │  +→   │ GENERATORI TRIGGER           │
│  (rule_type, ... ) │       │  • TX_ID                     │
└────────────────────┘       │  • AUDIT_UPDATE              │
          │                  │  • STORICO                   │
          │                  │  • ATTIVO (cascade/require/  │
          ▼                  │           block su FK)       │
┌────────────────────┐       └──────────────────────────────┘
│ overrides_cols     │                ▲
│ fk_exclusions      │                │
└────────────────────┘                │
          │                           │
          ▼                           │
     ┌───────────┐      audit →  ┌──────────────┐
     │ pg_catalog│  ───────────→ │ dbops.audit_ │
     │ (intros.) │               │ log          │
     └───────────┘               └──────────────┘
```

Componenti:

* **Scope**: limita gli schemi target (parametro, tabella o fallback su catalogo).
* **Rules**: cosa applicare (TX_ID, AUDIT_UPDATE, STORICO, ATTIVO), dove, con quale naming ed esistenza.
* **Overrides/Exclusions**: adattano casi particolari (colonne non standard, relazioni da saltare).
* **Orchestratori**: funzioni PL/pgSQL che leggono config + catalogo e creano i trigger idempotentemente.
* **Audit**: `dbops.audit_log` cattura dry‑run, apply, errori (anche **fuori transazione** via dblink).

---

## 3) 🔑 Regole supportate

### 3.1 TX_ID

**Scopo**: garantire un `tx_id` coerente su tabelle che lo espongono.
**Meccanismo**: trigger `BEFORE INSERT OR UPDATE` → `dbops.trgfn_tx_id_managed()`.

### 3.2 AUDIT_UPDATE

**Scopo**: aggiornare metadati `data_update` / `user_update`.
**Meccanismo**: trigger `BEFORE UPDATE` → `script.trgfn_upd_audit_data_user_generic()`.

### 3.3 STORICO

**Scopo**: snapshot JSONB degli UPDATE/DELETE verso `storico.<tabella>_storico`.
**Meccanismo**: trigger `BEFORE UPDATE` + `BEFORE DELETE` → `script.trgfn_upd_dlt_storico_generic(fk)`.

### 3.4 ATTIVO (soft‑delete funzionale)

**Scopo**: coerenza dello stato `attivo` tra padre/figlio con FK **NO ACTION/RESTRICT**.
**Meccanismo**:

* **CASO A**: padre *e* figlio hanno `attivo` →

  * padre: `AFTER UPDATE OF attivo` → `dbops.trgfn_soft_delete_cascade(child_schema, child_table, fk_col)`
  * figlio: `CONSTRAINT TRIGGER DEFERRABLE` → `dbops.trgfn_child_requires_active_parent(parent_schema, parent_table, parent_attivo, fk_col)`
* **CASO B**: solo il padre ha `attivo` →

  * padre: `BEFORE UPDATE OF attivo` → `dbops.trgfn_prevent_deactivate_if_children(child_schema, child_table, fk_col)`

**Nota FK**: supporto a `confdeltype IN ('r','a')` (RESTRICT e NO ACTION). `NO ACTION` permette coerenze **deferrable** a fine transazione.

---

## 4) ⚙️ Configurazione (tabelle chiave)

### 4.1 `dbops.automation_rules_tbl`

Regole per schema/tabella, con:

* `rule_type` ∈ {TX_ID, AUDIT_UPDATE, STORICO, ATTIVO}
* `exec_mode` ∈ {AUTO, CI, SCHEDULED}
* `name_template` (stringa; per ATTIVO: JSON con `cascade/require/block`)
* `existence_strategy` ∈ {BY_NAME, BY_FUNCTION, BOTH}
* `params` (JSONB) per dettagli opzionali (es. `include_no_action`)
* `priority`, `note`, audit fields

### 4.2 `dbops.automation_overrides_cols`

Override delle colonne non standard per tabella:
`ATTIVO_COL`, `AUDIT_TS`, `AUDIT_USER`, `STORICO_FK`.

### 4.3 `dbops.automation_fk_exclusions`

Esclude coppie **parent/child** dall’applicazione della regola `ATTIVO`.

### 4.4 `dbops.automation_scope`

Lista di schemi da considerare. Se assente/vuota → fallback su tutti gli schemi utente (escluso `storico`).

---

## 5) 🧠 Naming & Idempotenza

* **Template** con placeholder: `{schema}`, `{table}`, `{parent}`, `{child}`, `{fk}`, `{op}` (`upd|dlt`).
* **Limite 63 char**: adottare eventuale abbreviatore/hash nel helper `fn_name_from_template`.
* **Strategie di esistenza**:

  * `BY_NAME` → verifica su `pg_trigger.tgname`.
  * `BY_FUNCTION` → verifica su funzione invocata.
  * `BOTH` → vero se almeno uno dei due.

---

## 6) 🚦 Esecuzione: modalità & rollout

* **`AUTO`**: regola sempre valida per qualunque esecuzione.
* **`CI`**: usata in pipeline CI/CD (migrazioni).
* **`SCHEDULED`**: demandata a job periodici (scheduler DB o sistema).

**Liquibase contexts** (raccomandato nei test):

* `test` → setup playground + seed rules
* `test_apply` → apply reale
* `test_cleanup` → cleanup

**Dry‑run**: `p_dry_run=true` produce solo log in `dbops.audit_log` senza creare oggetti.

---

## 7) 📝 Audit & Osservabilità

* **`dbops.audit_log`**: `BEGIN/END` e `one‑shot` (`fn_audit_begin`, `fn_audit_end`, `fn_audit_log_once`).
* **Out‑of‑transaction**: via dblink `logconn` (GUC `myapp.log_with_dblink` + `script.fn_ensure_logconn`).
* Colonne utili: `exec_mode`, `parts`, `rule_type`, `dry_run`, `sqlstate`, `result` (conteggi/nomi trigger), `duration_ms`.

Esempio DRYRUN (TX_ID):

```sql
PERFORM dbops.fn_audit_log_once(
  p_function_name => 'run_automations',
  p_status        => 'DRYRUN',
  p_rule_type     => 'TX_ID',
  p_exec_mode     => 'CI',
  p_parts         => ARRAY['TX_ID'],
  p_dry_run       => true,
  p_params        => jsonb_build_object('table', 'anagrafiche.soggetti', 'trigger', 'trg_soggetti_ins_upd_gen_tx_id'),
  p_message       => 'Trigger would be created'
);
```

---

## 8) 🔍 Pattern operativi di test

1. **Seed** regole su `lab` (context `test`).
2. **Dry‑run** `TX_ID/AUDIT_UPDATE/STORICO/ATTIVO`.
3. **Apply** (context `test_apply`).
4. **Verify**: elenco trigger su `lab.%` e assert minimi.
5. **Cleanup** (context `test_cleanup`).

---

## 9) ⚠️ Errori tipici & rimedi

* **Nessun trigger creato**: regola disabilitata, scope vuoto, `exec_mode` non compatibile, strategia esistenza errata.
* **Nome oltre 63 char**: riduci template o usa helper con hash.
* **Storico non attivo**: tabella `storico.<t>_storico` assente o `STORICO_FK` non risolto.
* **ATTIVO non applicato**: relazione esclusa in `automation_fk_exclusions` o mancanza della colonna `attivo` su parent/child.

---

## 10) 🔐 Sicurezza & permessi

* L’utente dell’orchestratore deve poter **CREARE TRIGGER/FUNCTION** negli schemi target.
* Le funzioni richiamate devono avere **schema qualificato** ed essere **SECURITY DEFINER** solo se necessario.

---

## 11) 📌 Best practice

* Mantieni regole **specifiche** per schema/tabella; usa i pattern con moderazione.
* Standardizza i template naming (brevi e leggibili).
* Versiona seed e modifiche con changeSet dedicati e `runOnChange` solo dove serve.
* Usa **`NO ACTION DEFERRABLE`** dove possibile sulle FK che devono rispettare coerenze a fine transazione.

---

## 12) 📊 Esempi rapidi di configurazione

**Rule TX_ID (schema intero)**

```sql
INSERT INTO dbops.automation_rules_tbl(enabled, rule_type, target_schema, exec_mode, name_template, existence_strategy, params, priority)
VALUES (true,'TX_ID','anagrafiche','AUTO','trg_{table}_ins_upd_gen_tx_id','BY_NAME','{}'::jsonb,100);
```

**Rule ATTIVO (includi NO ACTION, template personalizzati)**

```sql
INSERT INTO dbops.automation_rules_tbl(enabled, rule_type, target_schema, exec_mode, name_template, existence_strategy, params, priority)
VALUES (
  true,'ATTIVO','vendite','AUTO',
  '{"cascade":"trg_soft_del_{parent}__{child}__{fk}",
    "require":"trg_chk_{child}_parent_{fk}",
    "block":"trg_block_deact_{parent}__{child}"}',
  'BY_NAME','{"include_no_action":true}'::jsonb,100);
```

---

> 🧠 **In sintesi**: l’automazione sposta il focus dalla *scrittura di trigger* alla *dichiarazione di regole*. Con scope controllato, override mirati e audit forte, si ottiene un rollout rapido, coerente e osservabile in tutti gli ambienti.

---

{% include-markdown "signature-core.md" %}

---

# 🧾 Mini checklist operativa – Automazioni (1 pagina)

> Stampabile e da usare prima/durante/dopo il rollout. Segna ✓ quando completato.

## Pre‑flight (obbligatorio)

* [ ] **Contesto Liquibase**: conferma che in CI **non** passi `--contexts=test` (solo locale).
* [ ] **DB corretto**: `SELECT lower(current_database());` ∈ {`zero`,`zeroerp`}.
* [ ] **Permessi**: utente con `CREATE TRIGGER` negli schemi target.
* [ ] **Scope**: definito uno tra `p_schemas`, `dbops.automation_scope` oppure fallback accettato.
* [ ] **Estensioni**: se vuoi audit out‑of‑tx → `dblink` installata e GUC `myapp.log_with_dblink='on'` configurata.

## Dry‑run (sicurezza)

* [ ] Esegui **DRYRUN** su schema/e target:

  ```sql
  SELECT dbops.fn_run_automations('CI', ARRAY['lab'], true, ARRAY['TX_ID','AUDIT_UPDATE','STORICO','ATTIVO']);
  ```
* [ ] Verifica log:

  ```sql
  SELECT executed_at, rule_type, params->>'table' AS table, params->>'trigger' AS trigger
  FROM dbops.audit_log
  WHERE status='DRYRUN'
  ORDER BY executed_at DESC
  LIMIT 50;
  ```

## Apply (controllato)

* [ ] Esegui APPLY solo sui moduli necessari (meglio uno alla volta):

  ```sql
  SELECT dbops.fn_run_automations('CI', ARRAY['lab'], false, ARRAY['TX_ID']);
  ```
* [ ] In caso di **ATTIVO**, ricordati che copre FK `NO ACTION` e `RESTRICT`.

## Verifica post‑apply

* [ ] Trigger presenti:

  ```sql
  SELECT n.nspname, c.relname, t.tgname
  FROM pg_trigger t
  JOIN pg_class c ON c.oid=t.tgrelid
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname IN ('lab') AND NOT t.tgisinternal
  ORDER BY 1,2,3;
  ```
* [ ] Test funzionali minimi (esempi):

  * **TX_ID**: insert/update → `tx_id` non nullo.
  * **AUDIT_UPDATE**: update → `data_update/user_update` aggiornati.
  * **STORICO**: update/delete → riga in `storico.<t>_storico`.
  * **ATTIVO**: set padre `attivo=false` → cascade/block/require coerenti.

## Osservabilità & log

* [ ] Consulta audit esiti:

  ```sql
  SELECT executed_at, status, rule_type, message, duration_ms
  FROM dbops.audit_log
  WHERE function_name='run_automations'
  ORDER BY executed_at DESC LIMIT 50;
  ```
* [ ] In caso di errore:

  ```sql
  SELECT executed_at, rule_type, sqlstate, error_context, params
  FROM dbops.audit_log
  WHERE status='ERROR'
  ORDER BY executed_at DESC LIMIT 20;
  ```

## Naming & config

* [ ] Template rispettano limite **63 char** (valuta abbreviazioni/hash se lunghi).
* [ ] Eventuali derivazioni colonne definite in `automation_overrides_cols` (`ATTIVO_COL`, `AUDIT_TS`, `AUDIT_USER`, `STORICO_FK`).
* [ ] Esclusioni specifiche in `automation_fk_exclusions` (solo per `ATTIVO`).
* [ ] `existence_strategy` coerente (`BY_NAME` / `BY_FUNCTION` / `BOTH`).

## Cleanup (solo in lab)

* [ ] Esegui cleanup **solo** con context dedicato:

  ```bash
  liquibase --contexts=test,test_cleanup update
  ```

## CI/CD – promemoria

* [ ] `tests/changelog.yaml` incluso nel master, ma eseguito **solo** se passi i context di test.
* [ ] Pipeline CI usa **solo** `update` senza contexts di test.

> Tip: mantieni una **issue checklist** per ogni rollout con riferimento alle regole toccate e ai nomi trigger generati.
