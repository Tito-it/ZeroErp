# Tutorial – framework di automazione DB

> (latest review 02-03-26)
>
> Destinatari: sviluppatori database che devono portare una nuova tabella nel framework
>
> Prerequisiti: conoscenza base di PostgreSQL e delle tabelle del progetto
>
> Vedi anche
>
> * [Guida Framework Automazione DB](/guide/automazione-db) — reference completo del framework
> * [Linee guida SQL](/linee-guida-sql) — convenzioni di naming obbligatorie

---

## Obiettivo

Hai appena creato una nuova tabella nel database e vuoi che il framework la gestisca automaticamente: `tx_id`, audit, storicizzazione, e tutte le altre regole applicabili.

Questo tutorial ti accompagna passo per passo, dalla verifica dell'ambito fino alla conferma che tutto funzioni.

**Tempo stimato**: 10-15 minuti per la prima volta, 2-3 minuti quando avrai familiarita.

---

## Scenario di esempio

Usiamo come esempio una tabella appena creata:

```sql
CREATE TABLE catalogo.categorie_materiali (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codice_interno TEXT NOT NULL,
    descrizione TEXT NOT NULL,
    attivo BOOLEAN NOT NULL DEFAULT true,
    tx_id UUID,
    date_insert TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert TEXT NOT NULL DEFAULT current_user,
    date_update TIMESTAMPTZ,
    user_update TEXT
);
```

La tabella ha tutte le colonne standard: `tx_id`, `attivo`, campi audit (`date_insert`, `user_insert`, `date_update`, `user_update`), e `codice_interno`. Il framework puo applicare tutte le regole core.

---

## Passo 1 – Verifica che lo schema sia nell'ambito

Il framework opera solo sugli schemi e tabelle dichiarati nell'**ambito**. Per prima cosa verifica se lo schema della tua tabella e gia presente.

```sql
SELECT * FROM dbops.automation_scope
WHERE schema_name = 'catalogo';
```

**Se trovi righe** (es. `('catalogo', '*all')`): lo schema e gia nell'ambito, la tua tabella e automaticamente inclusa. Vai al Passo 2.

**Se non trovi righe**: aggiungi lo schema all'ambito:

```sql
INSERT INTO dbops.automation_scope (schema_name, table_like)
VALUES ('catalogo', '*all');
```

Usa `'*all'` per includere tutte le tabelle dello schema. Se vuoi limitare a un pattern specifico, usa un pattern LIKE (es. `'categorie_%'`).

---

## Passo 2 – Verifica le regole esistenti

Le regole globali (con `target_schema='*all'`) si applicano a tutte le tabelle nell'ambito. Nella maggior parte dei casi non serve aggiungere nuove regole.

```sql
SELECT rule_type, target_schema, target_table, enabled
FROM dbops.automation_rules_tbl
WHERE enabled = true
ORDER BY rule_type;
```

Dovresti vedere righe come:

| rule_type         | target_schema | target_table | enabled |
| ----------------- | ------------- | ------------ | ------- |
| TX_ID             | *all          | NULL         | true    |
| AUDIT_UPDATE      | *all          | NULL         | true    |
| STORICO           | *all          | NULL         | true    |
| STORICO_PROVISION | *all          | NULL         | true    |
| ATTIVO            | *all          | NULL         | true    |

**Se queste regole ci sono**: la tua tabella e coperta. Vai al Passo 3.

**Se mancano**: consulta la [Guida Framework – Esempi SQL](/guide/automazione-db#6-esempi-sql-di-configurazione) per gli insert SQL di ciascuna regola.

---

## Passo 3 – Esegui il dry-run

Il dry-run simula l'esecuzione senza creare nulla. Ti mostra cosa succederebbe se eseguissi il runner per davvero.

A differenza dell'apply (Passo 4), qui puoi lanciare **tutte le regole insieme**: il dry-run non modifica nulla, quindi non c'e rischio. L'apply invece conviene farlo un tipo alla volta per facilitare la diagnostica in caso di errore.

```sql
-- Dry-run su tutte le regole per lo schema catalogo
SELECT dbops.fn_run_automations(
    'AUTO',                -- exec_mode
    ARRAY['catalogo'],     -- solo lo schema della nuova tabella
    true,                  -- dry_run = true
    ARRAY['TX_ID', 'AUDIT_UPDATE', 'STORICO', 'STORICO_PROVISION', 'ATTIVO']
);
```

Ora verifica cosa ha loggato:

```sql
SELECT executed_at, rule_type, status,
       params->>'table' AS tabella,
       params->>'trigger' AS trigger,
       message
FROM dbops.audit_log
WHERE status = 'DRYRUN'
ORDER BY executed_at DESC
LIMIT 20;
```

Dovresti vedere righe con la tua tabella `categorie_materiali` e i trigger che verrebbero creati:

* `trg_categorie_materiali_ins_upd_gen_tx_id` (TX_ID)
* `trg_upd_categorie_materiali_audit_data_user` (AUDIT_UPDATE)
* `trgx_z90_categorie_materiali_upd_dlt_storico` (STORICO)
* Creazione tabella `storico.categorie_materiali` (STORICO_PROVISION)
* Trigger ATTIVO per eventuali FK padre/figlio

**Se vedi `SKIP_EXISTS`**: il trigger esiste gia (va bene, il framework e idempotente).

**Se non vedi la tua tabella**: torna al Passo 1 e verifica l'ambito.

---

## Passo 4 – Esegui l'apply

Soddisfatto del dry-run? Ora esegui per davvero. E consigliato procedere **un tipo di regola alla volta**, cosi e piu facile diagnosticare eventuali problemi.

```sql
-- 1. Prima STORICO_PROVISION (crea la tabella storico)
SELECT dbops.fn_run_automations(
    'AUTO', ARRAY['catalogo'], false,
    ARRAY['STORICO_PROVISION']
);

-- 2. Poi TX_ID + AUDIT_UPDATE + STORICO
SELECT dbops.fn_run_automations(
    'AUTO', ARRAY['catalogo'], false,
    ARRAY['TX_ID', 'AUDIT_UPDATE', 'STORICO']
);

-- 3. Infine ATTIVO (se la tabella ha la colonna attivo e relazioni FK)
SELECT dbops.fn_run_automations(
    'AUTO', ARRAY['catalogo'], false,
    ARRAY['ATTIVO']
);
```

---

## Passo 5 – Verifica post-apply

### 5.1 Controlla i trigger creati

```sql
SELECT t.tgname AS trigger_name
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'catalogo'
  AND c.relname = 'categorie_materiali'
  AND NOT t.tgisinternal
ORDER BY t.tgname;
```

Dovresti vedere almeno:

* `trg_categorie_materiali_ins_upd_gen_tx_id`
* `trg_upd_categorie_materiali_audit_data_user`
* `trgx_z90_categorie_materiali_upd_dlt_storico`

### 5.2 Controlla la tabella storico

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'storico'
  AND table_name = 'categorie_materiali'
ORDER BY ordinal_position;
```

### 5.3 Test funzionali

```sql
-- Test TX_ID: insert e verifica tx_id
INSERT INTO catalogo.categorie_materiali (codice_interno, descrizione)
VALUES ('TEST001', 'Materiale di test');

SELECT id, codice_interno, tx_id
FROM catalogo.categorie_materiali
WHERE codice_interno = 'TEST001';
-- tx_id deve essere NOT NULL

-- Test AUDIT: update e verifica campi audit
UPDATE catalogo.categorie_materiali
SET descrizione = 'Materiale di test aggiornato'
WHERE codice_interno = 'TEST001';

SELECT date_update, user_update
FROM catalogo.categorie_materiali
WHERE codice_interno = 'TEST001';
-- date_update e user_update devono essere valorizzati

-- Test STORICO: verifica snapshot
SELECT *
FROM storico.categorie_materiali
WHERE snapshot->>'codice_interno' = 'TEST001';
-- deve esserci una riga con lo snapshot prima dell'update

-- Cleanup test
DELETE FROM catalogo.categorie_materiali
WHERE codice_interno = 'TEST001';
```

### 5.4 Controlla l'audit log

```sql
SELECT executed_at, status, rule_type, message
FROM dbops.audit_log
WHERE params->>'table' = 'categorie_materiali'
ORDER BY executed_at DESC;
-- tutti gli status devono essere OK
```

---

## Passo 6 (opzionale) – LOCK_COLUMNS

Se la tabella ha `codice_interno` (come nel nostro esempio), potresti voler bloccare la modifica di questa colonna dopo l'inserimento.

### 6.1 Verifica se la regola LOCK_COLUMNS esiste

```sql
SELECT * FROM dbops.automation_rules_tbl
WHERE rule_type = 'LOCK_COLUMNS' AND enabled = true;
```

### 6.2 Se vuoi aggiungere colonne extra (oltre a codice_interno)

```sql
INSERT INTO dbops.automation_lock_columns
    (target_schema, target_table, column_name, error_code, exec_mode, enabled)
VALUES
    ('catalogo', 'categorie_materiali', 'id', 'ERR_LOCK_PK', 'AUTO', true);
```

### 6.3 Esegui il runner

```sql
-- Dry-run
SELECT dbops.fn_run_automations_lock_columns('AUTO', ARRAY['catalogo'], true);

-- Apply
SELECT dbops.fn_run_automations_lock_columns('AUTO', ARRAY['catalogo'], false);
```

---

## Passo 7 (opzionale) – Policy indici FK

Se la tabella ha chiavi esterne, registrale nella policy per garantire che gli indici siano gestiti centralmente.

```sql
-- 1. Seed (registra FK gia indicizzate)
SELECT dbops.fn_seed_fk_index_policy();

-- 2. Populate (registra FK senza indice)
SELECT dbops.fn_populate_fk_index_policy();

-- 3. Verifica cosa e stato registrato
SELECT * FROM dbops.fk_index_policy
WHERE child_table = 'categorie_materiali';

-- 4. Apply (crea gli indici mancanti dove consentito)
CALL dbops.apply_fk_index_policy();
```

---

## Riepilogo dei passi

```text
1. Scope     → verifica/aggiungi lo schema in automation_scope
2. Rules     → verifica che le regole globali (*all) siano presenti
3. Dry-run   → simula con p_dry_run=true, controlla audit_log
4. Apply     → esegui con p_dry_run=false, un tipo alla volta
5. Verifica  → trigger presenti, tabella storico creata, test funzionali
6. (Opz.)    → LOCK_COLUMNS per colonne critiche
7. (Opz.)    → Policy FK per indici centralizzati
```

---

## I job pgAgent: cosa succede dopo il deploy

Una volta applicati manualmente i trigger (Passi 1-5), non devi preoccuparti della manutenzione. Il framework ha dei **job schedulati** tramite pgAgent che rieseguono automaticamente i runner a intervalli regolari. Se aggiungi una nuova tabella senza eseguire manualmente l'apply, il job notturno la coprira comunque.

### Come funzionano i job

Ogni job chiama una **procedura wrapper** nello schema `maintenance`, che a sua volta invoca il runner del framework. Tutti i wrapper usano `maintenance.fn_run_and_log` per:

* Acquisire un **advisory lock** (impedisce esecuzioni concorrenti dello stesso job)
* Registrare inizio, fine, esito e righe impattate in `maintenance.job_run_log`
* Catturare errori con SQLSTATE, dettagli e contesto

### Mappa completa: funzionalita → job schedulato

#### Job giornalieri (ogni sera alle 21:00)

Questi job mantengono allineati i trigger su tutte le tabelle nell'ambito. Se crei una nuova tabella durante il giorno e dimentichi l'apply manuale, il job serale la copre.

| Funzionalita          | Job pgAgent                     | Procedura maintenance                      | Runner invocato                                                        |
| --------------------- | ------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------- |
| **TX_ID**             | `automations_tx_id`             | `proc_automations_tx_id_job()`             | `dbops.fn_run_automations_tx_id('SCHEDULED', NULL, false)`             |
| **AUDIT_UPDATE**      | `automations_audit_update`      | `proc_automations_audit_update_job()`      | `dbops.fn_run_automations_audit_update('SCHEDULED', NULL, false)`      |
| **STORICO_PROVISION** | `automations_storico_provision` | `proc_automations_storico_provision_job()` | `dbops.fn_run_automations_storico_provision('SCHEDULED', NULL, false)` |
| **STORICO**           | `automations_storico`           | `proc_automations_storico_job()`           | `dbops.fn_run_automations_storico('SCHEDULED', NULL, false)`           |
| **ATTIVO**            | `automations_attivo`            | `proc_automations_attivo_job()`            | `dbops.fn_run_automations_attivo('SCHEDULED', NULL, false)`            |
| **LOCK_COLUMNS**      | `automations_lock_columns`      | `proc_automations_lock_columns_job()`      | `fn_run_automations_lock_columns` + `fn_run_automations_drop_lock_trg` |

#### Job settimanali (sabato/domenica)

Questi job si occupano di manutenzione e allineamento configurazioni.

| Funzionalita            | Job pgAgent                           | Procedura maintenance                    | Quando         | Cosa fa                                                                                  |
| ----------------------- | ------------------------------------- | ---------------------------------------- | -------------- | ---------------------------------------------------------------------------------------- |
| **Storicizza defaults** | `apply_storicizza_weekly`             | `proc_apply_storicizza_defaults_job()`   | Sabato 07:00   | Imposta `DEFAULT=true` sulla colonna `storicizza` nelle tabelle registrate               |
| **Sync storico set**    | `sync_storico_set_storicizza`         | `proc_sync_storico_set_storicizza_job()` | Sabato 07:05   | Scopre tabelle con colonna `storicizza` e le registra in `config.storico_set_storicizza` |
| **CLEANUP**             | `automations_cleanup_weekly`          | `proc_automations_cleanup_job()`         | Domenica 23:00 | Rimuove artefatti obsoleti (trigger/funzioni non piu necessari)                          |
| **FK Index Policy**     | `automations_apply_fk_indexes_policy` | `proc_apply_fk_index_policy_job()`       | Domenica 23:00 | Crea/rimuove indici FK secondo la policy                                                 |

#### Job senza scheduling automatico

| Funzionalita     | Procedura maintenance                 | Note                                                              |
| ---------------- | ------------------------------------- | ----------------------------------------------------------------- |
| **DELETE_BLOCK** | `proc_automations_delete_block_job()` | Solo invocazione manuale — le tabelle protette cambiano raramente |

### Riepilogo visuale della schedulazione

```text
Giornaliero @ 21:00
├── automations_tx_id
├── automations_audit_update
├── automations_storico_provision
├── automations_storico
├── automations_attivo
└── automations_lock_columns

Sabato @ 07:00
└── apply_storicizza_weekly

Sabato @ 07:05
└── sync_storico_set_storicizza

Domenica @ 23:00
├── automations_cleanup_weekly
└── automations_apply_fk_indexes_policy
```

### Consultare i log dei job

Per verificare che i job siano andati a buon fine:

```sql
-- Ultimi 20 esiti dei job di automazione
SELECT jobname, stepname, started_at, ended_at, ok, rows_affected, message
FROM maintenance.job_run_log
WHERE jobname LIKE 'automations_%'
   OR jobname LIKE 'apply_%'
   OR jobname LIKE 'sync_%'
ORDER BY started_at DESC
LIMIT 20;

-- Solo gli errori recenti
SELECT jobname, started_at, error_code, error_detail, message
FROM maintenance.job_run_log
WHERE ok = false
ORDER BY started_at DESC
LIMIT 10;
```

### In pratica: devo eseguire i runner manualmente o aspetto il job?

* **Nuova tabella in sviluppo** → esegui manualmente (Passi 3-5). I trigger ti servono subito per testare
* **Tabella gia in produzione** → il job serale la copre. Ma se hai urgenza, esegui manualmente
* **Dopo un deploy Liquibase** → i job serali allineano tutto. Per sicurezza puoi lanciare un dry-run manuale per conferma

---

## Errori comuni e soluzioni

| Problema                               | Causa probabile                                      | Soluzione                                                    |
| -------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------ |
| La tabella non appare nel dry-run      | Schema non nell'ambito                               | Aggiungi lo schema in `automation_scope`                     |
| Trigger non creato nonostante apply    | `SKIP_EXISTS` — esiste gia                           | Controlla `audit_log` per conferma                           |
| Errore "column does not exist"         | Manca una colonna standard (es. `tx_id`)             | Aggiungi la colonna alla tabella                             |
| Tabella storico non creata             | Regola STORICO_PROVISION non presente o disabilitata | Aggiungi/abilita la regola                                   |
| Naming troppo lungo (>63 char)         | Nome tabella molto lungo                             | Il framework abbrevia automaticamente; verifica il risultato |
| Errore su ATTIVO ma non hai la colonna | Il runner salta le tabelle senza `attivo`            | Nessuna azione richiesta                                     |

---

{% include-markdown "signature-core.md" %}
