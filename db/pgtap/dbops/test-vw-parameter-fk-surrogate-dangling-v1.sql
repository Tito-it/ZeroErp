-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vista diagnostica dbops.vw_parameter_fk_surrogate_dangling.
--       Migrations:
--         20260502-09 (create-vw-parameter-fk-surrogate-dangling)
--
-- Indice test (1..4):
--   1) La vista esiste in dbops.
--   2) Il count dangling e' >= 0 (sanity, non assume DB pulito - puo'
--      esistere dangling pre-esistente storico in parameter_overrides).
--   3) Iniezione controllata: disabilita temporaneamente il pattern
--      DEFAULT_UTILITY nel registry, INSERT override con valore non
--      valido (passa perche' nessun pattern matcha), riabilita il
--      pattern, verifica che la vista incrementa il count delle righe
--      dangling di esattamente +1 (delta robusto rispetto a baseline).
--      No permessi speciali: solo UPDATE su parameter_fk_surrogate.
--   4) Le colonne attese sono tutte presenti (schema check).
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

SELECT plan(4);

-- ============================================================
-- 1) Vista esiste
-- ============================================================
SELECT has_view(
    'dbops',
    'vw_parameter_fk_surrogate_dangling',
    'dbops.vw_parameter_fk_surrogate_dangling esiste'
);

-- ============================================================
-- 2) Count dangling >= 0 (sanity, non blocca su pre-esistente)
-- ============================================================
SELECT cmp_ok(
    (SELECT count(*) FROM dbops.vw_parameter_fk_surrogate_dangling)::int,
    '>=',
    0,
    'Count dangling iniziale >= 0 (sanity)'
);

-- ============================================================
-- 3) Iniezione controllata via disable/enable del pattern.
--    Steps:
--      a) baseline count
--      b) disable pattern DEFAULT_UTILITY nel registry
--      c) INSERT override con valore non valido (passa: dispatcher
--         non trova pattern abilitato e fa no-op)
--      d) re-enable pattern
--      e) verifica delta vista = +1
--    Tutto in transazione -> ROLLBACK pulisce.
-- ============================================================
CREATE TEMP TABLE tmp_baseline_dangling AS
SELECT count(*)::int AS n FROM dbops.vw_parameter_fk_surrogate_dangling;

UPDATE config.parameter_fk_surrogate
   SET enabled = false
 WHERE code_pattern = 'DEFAULT_UTILITY';

INSERT INTO config.parameter_overrides
    (parameter_id, overridden_value, function_name)
SELECT id, 'PGTAP_VALORE_INESISTENTE', 'pgtap_test_dangling_v1'
  FROM config.parameters
 WHERE code = 'DEFAULT_UTILITY';

UPDATE config.parameter_fk_surrogate
   SET enabled = true
 WHERE code_pattern = 'DEFAULT_UTILITY';

SELECT is(
    (SELECT count(*) FROM dbops.vw_parameter_fk_surrogate_dangling)::int,
    (SELECT n FROM tmp_baseline_dangling) + 1,
    'Vista dangling incrementa di 1 dopo iniezione controllata'
);

-- ============================================================
-- 4) Schema: colonne attese
-- ============================================================
SELECT columns_are(
    'dbops',
    'vw_parameter_fk_surrogate_dangling',
    ARRAY['source','source_id','code','value','target',
          'matched_pattern','matched_mode'],
    'Vista ha esattamente le 7 colonne attese'
);

SELECT * FROM finish();
ROLLBACK;
