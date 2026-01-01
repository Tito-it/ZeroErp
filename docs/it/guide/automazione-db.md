# 📗 Guida Tecnica – Automazioni DB (aggiornata)

>
> (latest review 01-01-26)
>
> **Scope:** aggiorna la guida esistente con le novità su wildcard `*all` e gli ultimi affinamenti senza stravolgere la struttura.
>
> **Riferimenti chiave**:
>
> > * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)
>
> * [dbops.automation_fk_exclusions](/dbzero/dbops/tabelle/automation_fk_exclusions)
>
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols)
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)
>
> * Orchestratori:
>
> [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations),  
> [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id),  
>  [dbops.run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update),  
>  [dbops.run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico),   
> [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo)  

---

## 1) 🎯 Perché un framework di automazione

Automatizzare attività ripetitive (assegnazione `tx_id`, audit update, storico, soft‑delete/`attivo`) riduce errori manuali e accelera i rilasci. Le regole dichiarative descrivono **cosa** e **dove** applicare; gli orchestratori generano trigger/oggetti in modo **idempotente**, con **dry‑run** e **audit**.

---

## 2) 🧩 Architettura (sintesi)

* **Scope** (`automation_scope` + `fn_resolve_scope` / parametro): delimita gli schemi/tabelle.
* **Rules** (`automation_rules_tbl`): regole per schema/tabella (TX_ID, AUDIT_UPDATE, STORICO, + STORICO_PROVISION).
* **Overrides/Exclusions**: colonne non standard e FK da saltare.
* **Orchestratori**: `fn_run_automations_*` per ogni area.
* **Audit**: `audit_log` (anche out‑of‑tx via dblink opzionale).

---

## 3) 🔑 Regole supportate (sintesi)

**3.1 TX_ID**

Trigger `BEFORE INSERT OR UPDATE` → `dbops.trgfn_tx_id_managed()`.

**3.2 AUDIT_UPDATE**

Trigger `BEFORE UPDATE` → `script.trgfn_upd_audit_data_user_generic()`.

**3.3 STORICO (trigger)**

* Trigger **unico** `BEFORE UPDATE OR DELETE` → `script.trgfn_upd_dlt_storico_generic(fk)`.
* **Naming default**: `trgx_z90_{table}_upd_dlt_storico` (prefisso per ordinamento).
* Scrive su **`storico.<stesso_nome_tabella>`** (senza suffisso `_storico`).

**3.4 STORICO_PROVISION (provisioning tabelle storico)**

* Crea `storico.<tabella>` se mancante con struttura standard (FK → PK padre, `snapshot` JSONB, `change_type`, `tipo_operazione`, ecc.).
* Param opzionale: `create_gin_index` su `snapshot`.

**3.5 ATTIVO (soft‑delete funzionale – policy conservativa)**

L’automazione **ATTIVO** implementa una politica **BLOCK-ONLY** finalizzata a garantire la coerenza logica tra record padre e figli collegati tramite FK.

**Regola applicata**

* La disattivazione (`attivo = false`) di un **record PADRE** è consentita **solo se NON esistono record FIGLI collegati**.
* **Non viene applicata alcuna cascata automatica** sui figli.
* **Non viene creato alcun vincolo REQUIRE** sul figlio.
* La regola si applica esclusivamente se il **PADRE possiede la colonna `attivo`**.
* Le FK considerate sono `RESTRICT` e `NO ACTION` (anche `DEFERRABLE`).

**Trigger generato**

* **Tabella**: PADRE
* **Evento**: `BEFORE UPDATE OF attivo`
* **Funzione**:
  `dbops.trgfn_prevent_deactivate_if_children(child_schema, child_table, fk_col [, pk_col])`

**Effetto**

Se:

* `OLD.attivo = true`
* `NEW.attivo = false`
* esistono record figli collegati tramite FK

➡️ l’operazione viene **bloccata con errore**.

L’automazione **non modifica mai automaticamente i record figli**.

---

## 4) ⚙️ Configurazione

**4.1 `automation_rules_tbl` (novità `*all`)**

* `target_schema`: ora supporta **`'*all'`** per applicare la regola a **tutti gli schemi** nello scope risolto. Rimangono validi valori specifici (es. `anagrafiche`).
* `target_table`: pattern `LIKE` (es. `foo_%`).
* `existence_strategy`: `BY_NAME` / `BY_FUNCTION` / `BOTH` (consigliato `BOTH`).
* `name_template`: stringa; per ATTIVO JSON `{cascade,require,block}`.
* `params`: chiavi per singola regola (es. `apply_triggers`, `create_gin_index`, `include_no_action`, `drop_legacy_ud`).

**Esempi minimali**

* STORICO (trigger): `('STORICO','*all', name_template='trgx_z90_{table}_upd_dlt_storico', params='{"apply_triggers":true}')`.
* STORICO_PROVISION: `('STORICO_PROVISION','*all', name_template=NULL, params='{"create_gin_index":false}')`.

**4.2 `automation_scope` (novità `*all`)**

* Colonne: `schema_name`, `table_like` (PK composita). **`table_like` non è NULL**: usare il sentinel **`'*all'`** per indicare “tutte le tabelle dello schema”.
* Il runner usa:

  * `fn_resolve_scope(p_schemas)` → se `NULL` o vuoto: legge `automation_scope`; se assente/vuota: fallback a tutti gli schemi utente **escluso `storico`**.
  * `fn_table_in_scope(schema, table)` → rispetta `'*all'` e i pattern per singole tabelle.

**4.3 Overrides / Exclusions**

* `automation_overrides_cols`: override colonne (`ATTIVO_COL`, `AUDIT_TS`, `AUDIT_USER`, `STORICO_FK`, `STORICIZZA_COL`).
* `automation_fk_exclusions`: esclude coppie parent/child per ATTIVO.

---

## 5) 🧠 Naming & idempotenza

* Placeholder: `{schema}`, `{table}`, `{parent}`, `{child}`, `{fk}`, `{op}` (se usato). Con trigger unico storico passare `'upd_dlt'` **solo** se il template lo richiede; altrimenti usare il nuovo default senza `{op}`.
* Limite 63 char: helper `fn_name_from_template` gestisce abbreviazioni/hash.

---

## 6) 🚦 Esecuzione & modalità

* `exec_mode`: `AUTO`, `CI`, `SCHEDULED` (runner e job pgAgent puntano a queste modalità).
* **Dry‑run**: tutti i runner accettano `p_dry_run=true` e loggano con `fn_audit_log_once`.
* **Esclusione schema `storico`**: i runner **STORICO** e **STORICO_PROVISION** non processano tabelle nello schema `storico`.

---

## 7) 📝 Audit & Log

* `dbops.audit_log`: `DRYRUN/OK/ERROR/SKIP_EXISTS`, con `params` strutturati (tabella, trigger, azione…).
* Errori bloccanti: `script.fn_log_and_raise_error(...)` + audit.
* Facoltativo: log out‑of‑tx via dblink `logconn` (GUC `myapp.log_with_dblink='on'`).

---

## 8) ✅ Mini‑checklist di uso

1. Inserisci/aggiorna **rules** (usa `'*all'` dove serve).
2. (Opzionale) Popola **scope**: righe `('<schema>','*all')` o pattern puntuali.
3. Esegui **dry‑run** del/i runner interessati (es. `fn_run_automations_storico(..., true)`).
4. Verifica audit → poi **apply** (`p_dry_run=false`).
5. Controlla i trigger creati (`pg_trigger`) e, per STORICO, la presenza della tabella `storico.<tabella>`.

---

## 9) 📌 Note operative / differenze recenti

* **Wildcard `*all`** introdotta sia in **rules** (`target_schema`) sia in **scope** (`table_like`).
* **STORICO** separato da **STORICO_PROVISION**: meno ambiguità tra provisioning e trigger.
* **Storico table**: stesso nome della base, schema `storico` (niente `_storico`).
* **Trigger storico**: unificato **UPDATE+DELETE** con default `trgx_z90_{table}_upd_dlt_storico`.
* **ATTIVO**: adottata una **policy conservativa BLOCK-ONLY**:

  * nessuna cascata automatica;
  * nessun vincolo REQUIRE sul figlio;
  * un record padre può essere disattivato **solo se privo di figli FK**;
  * eventuali strategie più aggressive (cascata, archiviazione figli) sono demandate a operazioni esplicite.
* Runner aggiornati: `fn_resolve_scope`, `fn_table_in_scope`, `fn_schema_match('*all', ...)`.
* Guard globale: schema `storico` escluso dai runner di storico.

---

## 10) 🧪 Esempi di configurazione (`automation_rules_tbl`)

Di seguito insert **idempotenti** (usano `WHERE NOT EXISTS`) per le regole più comuni. Adatta `target_schema`/`target_table` alle tue esigenze.

**10.1 TX_ID**

```sql
INSERT INTO dbops.automation_rules_tbl
(enabled, rule_type, target_schema, target_table, exec_mode,
 name_template, existence_strategy, params, priority, note)
SELECT true,'TX_ID','*all',NULL,'AUTO',
       'trg_{table}_ins_upd_gen_tx_id','BOTH','{}'::jsonb,100,'tx_id globale'
WHERE NOT EXISTS (
  SELECT 1 FROM dbops.automation_rules_tbl
  WHERE rule_type='TX_ID' AND target_schema='*all'
);
```

**10.2 AUDIT_UPDATE**

```sql
INSERT INTO dbops.automation_rules_tbl
(enabled, rule_type, target_schema, target_table, exec_mode,
 name_template, existence_strategy, params, priority, note)
SELECT true,'AUDIT_UPDATE','*all',NULL,'AUTO',
       'trg_upd_{table}_audit_data_user','BOTH',
       '{"audit_ts":"data_update","audit_user":"user_update"}'::jsonb,
       100,'audit update globale'
WHERE NOT EXISTS (
  SELECT 1 FROM dbops.automation_rules_tbl
  WHERE rule_type='AUDIT_UPDATE' AND target_schema='*all'
);
```

**10.3 STORICO (trigger unico UPDATE+DELETE)**

```sql
INSERT INTO dbops.automation_rules_tbl
(enabled, rule_type, target_schema, target_table, exec_mode,
 name_template, existence_strategy, params, priority, note)
SELECT true,'STORICO','*all',NULL,'AUTO',
       'trgx_z90_{table}_upd_dlt_storico','BOTH',
       '{"apply_triggers": true, "drop_legacy_ud": true}'::jsonb,
       100,'storico: trigger unificato'
WHERE NOT EXISTS (
  SELECT 1 FROM dbops.automation_rules_tbl
  WHERE rule_type='STORICO' AND target_schema='*all'
);
```

> **Nota**: la tabella di destinazione deve esistere in `storico.<stesso_nome_tabella>` (creata da STORICO_PROVISION). Override possibili via `automation_overrides_cols` (`STORICIZZA_COL`, `STORICO_FK`).

**10.4 STORICO_PROVISION (creazione tabelle in `storico`)**

```sql
INSERT INTO dbops.automation_rules_tbl
(enabled, rule_type, target_schema, target_table, exec_mode,
 name_template, existence_strategy, params, priority, note)
SELECT true,'STORICO_PROVISION','*all',NULL,'AUTO',
       NULL,'BOTH', '{"create_gin_index": false}'::jsonb,
       100,'storico: provisioning tabelle'
WHERE NOT EXISTS (
  SELECT 1 FROM dbops.automation_rules_tbl
  WHERE rule_type='STORICO_PROVISION' AND target_schema='*all'
);
```

Esempio più mirato (solo schema `catalogo`, tabelle `articoli_%`):

```sql
INSERT INTO dbops.automation_rules_tbl
(enabled, rule_type, target_schema, target_table, exec_mode,
 name_template, existence_strategy, params, priority, note)
VALUES (true,'STORICO_PROVISION','catalogo','articoli_%','AUTO',
        NULL,'BOTH','{"create_gin_index": true}'::jsonb,100,'storico: prov catalogo');
```

**10.5 ATTIVO (soft-delete / consistenza funzionale – BLOCK-ONLY)**

```sql
INSERT INTO dbops.automation_rules_tbl
(enabled, rule_type, target_schema, target_table, exec_mode,
 name_template, existence_strategy, params, priority, note)
SELECT true,'ATTIVO','*all',NULL,'AUTO',
       '{"block":"trg_block_deact_{parent}__{child}"}',
       'BOTH', '{}'::jsonb,
       100,'attivo: blocco disattivazione padre se esistono figli'
WHERE NOT EXISTS (
  SELECT 1 FROM dbops.automation_rules_tbl
  WHERE rule_type='ATTIVO' AND target_schema='*all'
);
```

**Comportamento**:

* crea **solo** trigger di BLOCCO sul PADRE;
* nessuna cascata;
* nessun trigger REQUIRE sul figlio;
* applicabile a FK `RESTRICT` e `NO ACTION`.

**10.6 Esempi di override (colonne non standard)**

> La tabella `automation_overrides_cols` permette di definire nomi custom per colonna per tabella.

```sql
-- Usa "attivo_flag" invece di "attivo"
INSERT INTO dbops.automation_overrides_cols(schema_name, table_name, override_key, column_name)
VALUES ('vendite','ordini','ATTIVO_COL','attivo_flag');

-- Per storico: FK diversa da <table>_id
INSERT INTO dbops.automation_overrides_cols(schema_name, table_name, override_key, column_name)
VALUES ('catalogo','articoli_componenti','STORICO_FK','articoli_componenti_id');
```

**10.7 Note pratiche**

* Usa `target_schema='*all'` quando vuoi applicare globalmente, altrimenti specifica lo schema.
* `existence_strategy='BOTH'` minimizza conflitti (nome o funzione).
* Per STORICO, preferisci il template **senza** `{op}` (trigger unico). Se mantieni un template con `{op}`, passa `'upd_dlt'` all’helper di naming.
* Tutti i runner supportano `p_dry_run`. Controlla gli esiti in `dbops.audit_log`.

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
* [ ] In caso di **ATTIVO**:

  * è attiva **solo la policy BLOCK-ONLY**;
  * il padre può essere disattivato **solo se non esistono figli FK**;
  * non avvengono cascata né modifiche automatiche sui figli.

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
  * **ATTIVO**: set padre `attivo=false` → disattivazione consentita solo se privo di figli FK.

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