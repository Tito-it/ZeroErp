# 📗 Guida Tecnica – Framework DB (aggiornata)

>
> **(latest review 18-01-26)**
>
> **Scope:** descrive il framework DB. Le automazioni sono una parte del framework, incluse le novità su wildcard `*all` e gli ultimi affinamenti senza stravolgere la struttura.
>
> **Riferimenti chiave**:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)
>
> * [dbops.automation_fk_exclusions](/dbzero/dbops/tabelle/automation_fk_exclusions)
>
> * [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions)
>
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols)
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)
>
> * [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap)
>
> * *Orchestratori:*
>
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations),  
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id),  
>  * [dbops.run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update),  
>  * [dbops.run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico),   
>  * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns),  
>  * [dbops.fn_run_automations_drop_lock_trg](/dbzero/dbops/funzioni/fn_run_automations_drop_lock_trg),  
>  * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo),  
>  * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block)  
>  * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup)  

---

## 1) 🎯 Perché un framework di automazione

Automatizzare attività ripetitive (assegnazione `tx_id`, audit update, storico, soft‑delete/`attivo`) riduce errori manuali e accelera i rilasci. Le regole dichiarative descrivono **cosa** e **dove** applicare; gli orchestratori generano trigger/oggetti in modo **idempotente**, con **dry‑run** e **audit**.

> ⚠️ **Avvertenza**
>
> Per garantire il corretto funzionamento del framework e delle regole di applicazione, nello sviluppo è **obbligatorio** rispettare le convenzioni di naming indicate  nella apposita sezione **[Linee guida sql](/linee-guida-sql)** .    
> In caso contrario le automazioni possono **non essere applicate**, con conseguenti interventi manuali, debug non necessari e perdita di tempo nel capire perché il framework non abbia agito.

---

## 2) 🧩 Architettura (sintesi)

* **Scope** (`automation_scope` + `fn_resolve_scope` / parametro): delimita gli schemi/tabelle.
* **Rules** (`automation_rules_tbl`): regole per schema/tabella (TX_ID, AUDIT_UPDATE, STORICO, LOCK_COLUMNS, CLEANUP, + STORICO_PROVISION).
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

**3.5 LOCK_COLUMNS (blocco colonne critiche)**

Trigger `BEFORE UPDATE OF ...` → `script.trgfn_lock_columns(...)`.

* Usa `automation_rules_tbl` per `name_template` ed `existence_strategy`.
* La colonna **`codice_interno`** e' implicita: se presente in tabella viene sempre inclusa.
* Le colonne extra si configurano in `dbops.automation_lock_columns`.

**3.5.1 LOCK_COLUMNS cleanup (drop trigger obsoleti)**

Quando **non esistono colonne da bloccare** (nessun `codice_interno` e nessuna colonna extra attiva),
i trigger LOCK_COLUMNS possono restare obsoleti.  
La funzione `dbops.fn_run_automations_drop_lock_trg` rimuove questi trigger.

**3.6 ATTIVO (soft‑delete funzionale – policy conservativa)**

L’automazione **ATTIVO** implementa una politica **BLOCK-ONLY** finalizzata a garantire la coerenza logica tra record padre e figli collegati tramite FK.

**Regola applicata**

* La disattivazione (`attivo = false`) di un **record PADRE** è consentita **solo se NON esistono record FIGLI collegati**.
* **Non viene applicata alcuna cascata automatica** sui figli.
* **Non viene creato alcun vincolo REQUIRE** sul figlio.
* La regola si applica esclusivamente se il **PADRE possiede la colonna `attivo`**.
* Le FK considerate sono `RESTRICT` e `NO ACTION` (anche `DEFERRABLE`).

**Nota**: **l’automazione ATTIVO viene applicata solo alle FK con colonna che termina in `_id`**; in caso contrario la regola viene saltata per evitare riferimenti a codici testuali o chiavi non id.

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

**3.7 OVERLAP (anti-sovrapposizione temporale)**

L'automazione **OVERLAP** centralizza la gestione dei vincoli **EXCLUDE GiST** per evitare sovrapposizioni
su tabelle **versionate** con colonne periodo (`valido_dal/valido_al` o `valid_from/valid_to`).

Componenti principali:

* **Config**: `dbops.automazione_overlap` con chiavi logiche, colonne periodo e flag `active`.
* **Seed**: `dbops.fn_seed_automazione_overlap()` rileva tabelle eleggibili e imposta `active=true` solo se versionate.
* **Apply**: `dbops.fn_apply_automazione_overlap()` crea i vincoli `EXCLUDE` sulle tabelle `active=true`.

Note operative:

* Se `key_columns` non e' valorizzato, il vincolo non viene creato.
* Per chiavi UUID e' richiesta l'estensione `btree_gist`.
* Le tabelle non versionate restano `active=false`.

**3.8 DELETE_BLOCK (blocco DELETE con GUC)**

Automazione dedicata a tabelle sensibili (es. ruoli) per **bloccare la DELETE** salvo bypass esplicito via GUC.

Componenti principali:

* **Config**: `dbops.automation_delete_block` con schema/tabella, GUC e flag `enabled`.
* **Trigger**: `script.trgfn_delete_block_by_guc(guc_key)`.
* **Apply**: `dbops.fn_run_automations_delete_block()` applica i trigger.

**3.9 CLEANUP (cleanup_at)**

Automazione per **calcolare `cleanup_at`** e **purge** dei record scaduti.

Componenti principali:

* **Config regole**: `dbops.automation_rules_tbl` con `rule_type`:
  * `CLEANUP_AT` → calcola `cleanup_at` con TTL fisso
  * `CLEANUP_PURGE` → elimina record scaduti (batch)
* **Esclusioni**: `dbops.automation_cleanup_exclusions`
* **Apply**: `dbops.fn_run_automations_cleanup()`

Parametri JSON tipici:

* `CLEANUP_AT`: `ttl_days`, `cleanup_column`, `base_ts_column`, `apply_on_update`
* `CLEANUP_PURGE`: `cleanup_column`, `batch_limit`

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

**4.4 `automation_lock_columns`**

* Configura **colonne extra** da bloccare per singola `schema.tabella`.
* Campi chiave: `target_schema`, `target_table`, `column_name`, `error_code`, `exec_mode`, `enabled`.
* Se la colonna non esiste fisicamente nella tabella target, il runner la ignora.

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
3. Esegui **dry‑run** del/i runner interessati (es. `fn_run_automations_storico(..., true)` o `fn_run_automations_lock_columns(..., true)`).
4. Se stai disattivando colonne LOCK_COLUMNS, valuta il cleanup:  
   `SELECT dbops.fn_run_automations_drop_lock_trg('AUTO', NULL, false);`
4. Verifica audit → poi **apply** (`p_dry_run=false`).
5. Controlla i trigger creati (`pg_trigger`) e, per STORICO, la presenza della tabella `storico.<tabella>`.

---

## 9) 📌 Note operative / differenze recenti

* **Wildcard `*all`** introdotta sia in **rules** (`target_schema`) sia in **scope** (`table_like`).
* **STORICO** separato da **STORICO_PROVISION**: meno ambiguità tra provisioning e trigger.
* **Storico table**: stesso nome della base, schema `storico` (niente `_storico`).
* **Trigger storico**: unificato **UPDATE+DELETE** con default `trgx_z90_{table}_upd_dlt_storico`.
* **LOCK_COLUMNS**: trigger unico per tabella con `UPDATE OF` sulle colonne effettive e `script.trgfn_lock_columns(...)`.
* **ATTIVO**: adottata una **policy conservativa BLOCK-ONLY**:

  * nessuna cascata automatica;
  * nessun vincolo REQUIRE sul figlio;
  * un record padre può essere disattivato **solo se privo di figli FK**;
  * eventuali strategie più aggressive (cascata, archiviazione figli) sono demandate a operazioni esplicite.
* Runner aggiornati: `fn_resolve_scope`, `fn_table_in_scope`, `fn_schema_match('*all', ...)`.
* Guard globale: schema `storico` escluso dai runner di storico.

---

## 9bis) 🔍 Policy indici FK (governance)

**Obiettivo**: evitare la creazione manuale di indici FK e centralizzare la decisione in `dbops.fk_index_policy`.

**Componenti principali**

* **Tabella policy**: [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) (flag `consentito` + `dll_command`).
* **View di supporto**:
  * [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy) → FK con indice esistente ma **senza** policy (filtrata per `automation_scope`).
  * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice)→ FK **senza** indice (filtrata per `automation_scope` e **considera anche UNIQUE**).
  * [dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes) → rileva indici duplicati per schema/tabella.
* **Funzioni**:
  * [dbops.fn_seed_fk_index_policy()](/dbzero/dbops/funzioni/fn_seed_fk_index_policy) → registra in policy le FK gia' indicizzate (`consentito=true`).
  * [dbops.fn_populate_fk_index_policy()](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) → registra in policy le FK senza indice (`consentito=false`).
  * [dbops.fn_populate_fk_index_policy()](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) → crea/rimuove indici in base alla policy.

**Regola operativa**

* **Non creare indici FK manualmente**: se servono, usa la policy e il naming coerente, poi registra in `fk_index_policy`.
* **Scope schemi**: le view lavorano solo sugli schemi presenti in `dbops.automation_scope`.

**Flusso consigliato**

1. **Seed** (indici gia' presenti):
   `SELECT dbops.fn_seed_fk_index_policy();`
2. **Populate** (indici mancanti):
   `SELECT dbops.fn_populate_fk_index_policy();`
3. **Apply**:
   `CALL dbops.apply_fk_index_policy();`

**Job schedulabile**

* Wrapper in maintenance: `maintenance.proc_apply_fk_index_policy_job()` (logging + lock).

---

## 10) 🔢 Generazione automatica codici/numero

Questa parte del framework gestisce la **generazione automatica di codici o numeri** sulle tabelle applicative tramite configurazione declarativa e trigger generati automaticamente.

### 10.1 Componenti principali

**Tabella di configurazione**

* [config.sistema_codici](/dbzero/config/manual/sistema_codici)

**Funzioni**

* [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice) → genera il codice in base alla configurazione e usa una sequenza pre-provisionata.
* [script.trgfn_config_sistema_codici_sync_gen_codice](/dbzero/script/funzioni/trgfn_config_sistema_codici_sync_gen_codice) → sincronizza i trigger sulle tabelle target.

### 10.2 Regole operative

* La generazione avviene **solo** se `usa_sequenza = TRUE`.
* Il nome sequenza e' **sempre derivato** come `<schema>.<tabella>_<colonna>_seq`.
* Il trigger applicato alla tabella target e' `BEFORE INSERT OR UPDATE OF <colonna>`.
* La generazione avviene solo se il campo target e' **nullo** o **vuoto**:
  * numerici: `NULL` o `0`
  * alfanumerici: `NULL` o stringa vuota

### 10.3 Naming e posizione oggetti

* **Trigger**: `trg_<tabella>_a10_gen_codice_ins_upd`
* **Trigger function**: `trgfn_<tabella>_gen_codice`
* La trigger function viene creata **nello stesso schema** della tabella target.

### 10.4 Flusso di sincronizzazione

1. Inserimento/aggiornamento/cancellazione in `config.sistema_codici`.
2. Il trigger su `config.sistema_codici` chiama `script.trgfn_config_sistema_codici_sync_gen_codice()`.
3. La funzione crea/aggiorna/rimuove trigger e trigger function sulla tabella target.

### 10.5 Checklist

* Verificare che esista la riga in `config.sistema_codici` per `codice_interno`.
* Popolare `schema_tabella`, `nome_tabella`, `nome_colonna`.
* Impostare `usa_sequenza = TRUE` per attivare la generazione.

---

## 11) 🧪 Esempi di configurazione (`automation_rules_tbl`)

Di seguito insert **idempotenti** (usano `WHERE NOT EXISTS`) per le regole più comuni. Adatta `target_schema`/`target_table` alle tue esigenze.

**11.1 TX_ID**

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

**11.2 AUDIT_UPDATE**

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

**11.3 STORICO (trigger unico UPDATE+DELETE)**

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

**11.4 STORICO_PROVISION (creazione tabelle in `storico`)**

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

**11.5 ATTIVO (soft-delete / consistenza funzionale – BLOCK-ONLY)**

```sql
INSERT INTO dbops.automation_rules_tbl
(enabled, rule_type, target_schema, target_table, exec_mode,
 name_template, existence_strategy, params, priority, note)
SELECT true,'ATTIVO','*all',NULL,'AUTO',
       '{"block":"trg_{parent}_a10_{child}_block_deact_upd",
         "require":"trg_{child}_a10_{parent}_require_attivo_ins_upd"}',
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
