-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: immutabilita cliente su vendite.ordini (DB-ORD-LOCK 2026-06-04).
-- Scope: verifica strutturale (introspezione, no fixture) della consegna:
--   registro automation_lock_columns + codice errore + trigger materializzati
--   + cleanup del ramo morto in trgfn_ordini_normalize.
-- Il comportamento di rifiuto e' garantito da script.trgfn_lock_columns
-- (gia coperto dai test generici di lock).
--
-- PREREQUISITO: l'automazione che materializza i trigger dal registro
--   (maintenance.proc_automations_lock_columns_job / dbops.fn_run_automations_lock_columns)
--   deve essere stata eseguita prima di questo test (vedi brief §S5).
--
-- Indice test (1..8):
--   1. Registro: riga vendite.ordini.billing_account_id presente, enabled, codice corretto
--   2. Registro: riga vendite.ordini.soggetto_ruolo_id presente, enabled, codice corretto
--   3. Codice errore E_ORD_CLIENTE_IMMUTABILE registrato in config.messaggi_errore (it)
--   4. Trigger lock materializzato su billing_account_id (BEFORE UPDATE, trgfn_lock_columns)
--   5. Trigger lock materializzato su soggetto_ruolo_id (BEFORE UPDATE, trgfn_lock_columns)
--   6. Regressione: lock su numero ancora presente
--   7. Cleanup: trgfn_ordini_normalize NON contiene piu il ramo UPDATE su cambio BA
--   8. trgfn_ordini_normalize conserva l'eredita fatturazione_trigger su INSERT
-- ------------------------------------------------------------
BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- 1. Registro: billing_account_id
SELECT ok(
    EXISTS (
        SELECT 1 FROM dbops.automation_lock_columns
         WHERE target_schema = 'vendite'
           AND target_table  = 'ordini'
           AND column_name   = 'billing_account_id'
           AND error_code    = 'E_ORD_CLIENTE_IMMUTABILE'
           AND enabled IS TRUE
    ),
    '1. Registro automation_lock_columns: vendite.ordini.billing_account_id (E_ORD_CLIENTE_IMMUTABILE, enabled)'
);

-- 2. Registro: soggetto_ruolo_id
SELECT ok(
    EXISTS (
        SELECT 1 FROM dbops.automation_lock_columns
         WHERE target_schema = 'vendite'
           AND target_table  = 'ordini'
           AND column_name   = 'soggetto_ruolo_id'
           AND error_code    = 'E_ORD_CLIENTE_IMMUTABILE'
           AND enabled IS TRUE
    ),
    '2. Registro automation_lock_columns: vendite.ordini.soggetto_ruolo_id (E_ORD_CLIENTE_IMMUTABILE, enabled)'
);

-- 3. Codice errore registrato
SELECT ok(
    EXISTS (
        SELECT 1 FROM config.messaggi_errore
         WHERE codice = 'E_ORD_CLIENTE_IMMUTABILE'
           AND lingua = 'it'
    ),
    '3. Codice errore E_ORD_CLIENTE_IMMUTABILE registrato in config.messaggi_errore (it)'
);

-- 4. Trigger lock materializzato su billing_account_id
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
         WHERE t.tgrelid = 'vendite.ordini'::regclass
           AND NOT t.tgisinternal
           AND pg_get_triggerdef(t.oid) ILIKE '%before update%'
           AND pg_get_triggerdef(t.oid) LIKE '%trgfn_lock_columns%'
           AND pg_get_triggerdef(t.oid) LIKE '%billing_account_id%'
    ),
    '4. Trigger BEFORE UPDATE che locka billing_account_id via trgfn_lock_columns'
);

-- 5. Trigger lock materializzato su soggetto_ruolo_id
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
         WHERE t.tgrelid = 'vendite.ordini'::regclass
           AND NOT t.tgisinternal
           AND pg_get_triggerdef(t.oid) ILIKE '%before update%'
           AND pg_get_triggerdef(t.oid) LIKE '%trgfn_lock_columns%'
           AND pg_get_triggerdef(t.oid) LIKE '%soggetto_ruolo_id%'
    ),
    '5. Trigger BEFORE UPDATE che locka soggetto_ruolo_id via trgfn_lock_columns'
);

-- 6. Regressione: lock su numero ancora attivo
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
         WHERE t.tgrelid = 'vendite.ordini'::regclass
           AND NOT t.tgisinternal
           AND pg_get_triggerdef(t.oid) LIKE '%trgfn_lock_columns%'
           AND pg_get_triggerdef(t.oid) LIKE '%numero%'
    ),
    '6. Regressione: lock su numero (CODICE_NON_MODIFICABILE) ancora presente'
);

-- 7. Cleanup: nessun ramo UPDATE su cambio billing_account_id in normalize
SELECT ok(
    pg_get_functiondef('vendite.trgfn_ordini_normalize()'::regprocedure)
        NOT LIKE '%OLD.billing_account_id IS DISTINCT FROM NEW.billing_account_id%',
    '7. trgfn_ordini_normalize: rimosso il ramo UPDATE su cambio billing_account_id (codice morto)'
);

-- 8. Normalize conserva l'eredita fatturazione_trigger (su INSERT)
SELECT ok(
    pg_get_functiondef('vendite.trgfn_ordini_normalize()'::regprocedure) LIKE '%fatturazione_ordini%',
    '8. trgfn_ordini_normalize: eredita fatturazione_trigger da billing_account conservata (INSERT)'
);

SELECT * FROM finish();
ROLLBACK;
