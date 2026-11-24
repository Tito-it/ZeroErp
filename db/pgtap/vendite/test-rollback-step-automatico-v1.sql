-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il rollback di uno step parte da solo solo se la corsia lo accende e
--   nessun suo task e' distruttivo o sconosciuto.
-- Riferimento: brief-db-porte-aperte-dalla-sola-guc §4.8 (R-DB-I3; D-I.3 a e la
--   forma «decisione intera» e «colonna» di Tid, 2026-11-24); changeSet
--   00_schema/dbops/20261123-95 (pipeline_task_registry.distruttivo),
--   00_schema/vendite/20261123-96 (fatturazione_pipeline.auto_step_rollback e il
--   CHECK sul meta), 20_code/vendite/20261123-97
--   (vendite.fn_check_rollback_step_automatico).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - le due colonne nascono boolean NOT NULL, default false: un task che non
--     dice niente non e' distruttivo, una corsia che non dice niente non fa
--     partire il rollback da solo;
--   - la chiave meta.auto_step_rollback e' rifiutata: la sede e' la colonna;
--   - la funzione risponde true solo con il flag acceso, un rollback non vuoto
--     e ogni task registrato, attivo e non distruttivo. ⭐ Fail-closed: spento o
--     sconosciuto vale come distruttivo;
--   - legge il `rollback` dello step, non i `processi`;
--   - uno step che non si risolve: false; un parametro invalido solleva, dalla
--     risoluzione dello step.
--
-- I casi sono COSTRUITI (regola zero, AGENTS.md): uno stato di prova con la sua
--   pipeline MASSIVO e tre task di prova nel dominio FATTURAZIONE. Oggi nessuna
--   pipeline del seed ha un rollback, quindi il seed non saprebbe produrre
--   nessuno di questi casi.
-- Gira come l'applicazione (runner di default).
--
-- Elenco test (plan 14):
--    1) dbops.pipeline_task_registry.distruttivo: boolean, NOT NULL, default false
--    2) vendite.fatturazione_pipeline.auto_step_rollback: boolean, NOT NULL, default false
--    3) la chiave auto_step_rollback nel meta e' rifiutata dal CHECK
--    4) setup: stato, pipeline e tre task di prova
--    5) flag acceso, rollback di un task sicuro: true
--    6) flag spento, stesso rollback: false
--    7) flag acceso, rollback vuoto: false
--    8) ⭐ flag acceso, rollback con un task distruttivo: false
--    9) flag acceso, rollback con un task spento: false
--   10) flag acceso, rollback con un task che il registro non conosce: false
--   11) flag acceso, rollback con un elemento senza la chiave «task»: false
--   12) un task distruttivo nei PROCESSI non chiude il rollback: true
--   13) uno step che non si risolve: false
--   14) p_tipo_lotto NULL: E_PARAMETRO_INVALIDO
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- 1-2 Le colonne
-- ============================================================
-- Tipi nudi: una tabella e un nome di colonna del catalogo, e la forma resa come
--   testo; nessuno e' il riflesso di una colonna.
CREATE OR REPLACE FUNCTION pg_temp.forma_colonna(p_tabella regclass, p_colonna name)
RETURNS text LANGUAGE sql STABLE AS $f$
  SELECT format_type(a.atttypid, a.atttypmod) || ' ' || a.attnotnull::text || ' '
         || pg_get_expr(d.adbin, d.adrelid)
    FROM pg_catalog.pg_attribute a
    LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
   WHERE a.attrelid = p_tabella AND a.attname = p_colonna AND NOT a.attisdropped;
$f$;

SELECT is(pg_temp.forma_colonna('dbops.pipeline_task_registry'::regclass, 'distruttivo'),
          'boolean true false',
          '1) dbops.pipeline_task_registry.distruttivo: boolean, NOT NULL, default false');

SELECT is(pg_temp.forma_colonna('vendite.fatturazione_pipeline'::regclass, 'auto_step_rollback'),
          'boolean true false',
          '2) vendite.fatturazione_pipeline.auto_step_rollback: boolean, NOT NULL, default false');

-- ============================================================
-- Setup: uno stato con la sua pipeline, uno senza, tre task
-- ============================================================
CREATE TEMP TABLE tmp_rb_ids (
  stato_id        bigint,
  stato_vuoto_id  bigint,
  pipeline_id     bigint
) ON COMMIT DROP;

-- La forma dello stato e' quella di test-fatturazione-pipeline-fallback:
--   IN_CORSO, una tappa tecnica del giro, ne' inizio ne' termine.
WITH ins AS (
  INSERT INTO config.stati_doc_fiscale (codice, descrizione, attivo, ordine, meta,
                                        codice_interno, applica_lotto, applica_fattura, fase)
  SELECT v.codice, 'Stato rollback automatico (pgTAP)', true, v.ordine, '{}'::jsonb,
         v.codice, true, false, 'IN_CORSO'
    FROM (VALUES ('TPRB_CON_PIPELINE', 996), ('TPRB_SENZA_PIPELINE', 997)) AS v(codice, ordine)
  RETURNING id, codice
)
INSERT INTO tmp_rb_ids (stato_id, stato_vuoto_id)
SELECT (SELECT id FROM ins WHERE codice = 'TPRB_CON_PIPELINE'),
       (SELECT id FROM ins WHERE codice = 'TPRB_SENZA_PIPELINE');

WITH ins AS (
  INSERT INTO vendite.fatturazione_pipeline (descrizione, tipo_lotto, utility_id, tipo_doc_fiscale_id,
                                             stato_doc_fiscale_id, processi, rollback, attivo, meta)
  SELECT 'Pipeline rollback automatico (pgTAP)', 'MASSIVO', NULL, NULL,
         i.stato_id, '[]'::jsonb, '[]'::jsonb, true, '{}'::jsonb
    FROM tmp_rb_ids i
  RETURNING id
)
UPDATE tmp_rb_ids SET pipeline_id = (SELECT id FROM ins);

INSERT INTO dbops.pipeline_task_registry (dominio_id, task_code, descrizione, attivo, distruttivo)
SELECT d.id, v.task_code, 'Task di prova del rollback automatico', v.attivo, v.distruttivo
  FROM dbops.domini_task d
 CROSS JOIN (VALUES ('zz_pgtap_rb_sicuro',      true,  false),
                    ('zz_pgtap_rb_distruttivo', true,  true),
                    ('zz_pgtap_rb_spento',      false, false)) AS v(task_code, attivo, distruttivo)
 WHERE d.codice = 'FATTURAZIONE';

-- Mette la pipeline di prova in un assetto: la scrittura in un'istruzione, la
--   lettura nella successiva (lo snapshot della stessa istruzione non la vede).
CREATE OR REPLACE FUNCTION pg_temp.assetto(
    p_flag     vendite.fatturazione_pipeline.auto_step_rollback%TYPE,
    p_rollback vendite.fatturazione_pipeline.rollback%TYPE,
    p_processi vendite.fatturazione_pipeline.processi%TYPE DEFAULT '[]'::jsonb)
RETURNS void LANGUAGE sql AS $f$
  UPDATE vendite.fatturazione_pipeline fp
     SET auto_step_rollback = p_flag, rollback = p_rollback, processi = p_processi
   WHERE fp.id = (SELECT pipeline_id FROM tmp_rb_ids);
$f$;

-- boolean: la risposta della funzione esaminata, non il riflesso di una colonna.
CREATE OR REPLACE FUNCTION pg_temp.ammesso()
RETURNS boolean LANGUAGE sql AS $f$
  SELECT vendite.fn_check_rollback_step_automatico('MASSIVO', (SELECT stato_id FROM tmp_rb_ids));
$f$;

-- ============================================================
-- 3 Il CHECK sul meta
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE vendite.fatturazione_pipeline SET meta = meta || ''{"auto_step_rollback": true}''::jsonb WHERE id = %s',
    (SELECT pipeline_id FROM tmp_rb_ids))),
  'chk_fatturazione_pipeline_meta_senza_auto_step_rollback',
  '3) la chiave auto_step_rollback nel meta e'' rifiutata: la sede e'' la colonna');

SELECT is(
  (SELECT count(*)::int FROM tmp_rb_ids
    WHERE stato_id IS NOT NULL AND stato_vuoto_id IS NOT NULL AND pipeline_id IS NOT NULL)
  + (SELECT count(*)::int FROM dbops.pipeline_task_registry r
       JOIN dbops.domini_task d ON d.id = r.dominio_id AND d.codice = 'FATTURAZIONE'
      WHERE r.task_code LIKE 'zz\_pgtap\_rb\_%'),
  4,
  '4) setup: stato, pipeline e tre task di prova');

-- ============================================================
-- 5-12 La decisione
-- ============================================================
SELECT pg_temp.assetto(true, '[{"task": "zz_pgtap_rb_sicuro"}]');
SELECT is(pg_temp.ammesso(), true,
          '5) flag acceso, rollback di un task sicuro: parte da solo');

SELECT pg_temp.assetto(false, '[{"task": "zz_pgtap_rb_sicuro"}]');
SELECT is(pg_temp.ammesso(), false,
          '6) flag spento, stesso rollback: non parte da solo');

SELECT pg_temp.assetto(true, '[]');
SELECT is(pg_temp.ammesso(), false,
          '7) flag acceso, rollback vuoto: non c''e'' niente da far partire');

SELECT pg_temp.assetto(true, '[{"task": "zz_pgtap_rb_sicuro"}, {"task": "zz_pgtap_rb_distruttivo"}]');
SELECT is(pg_temp.ammesso(), false,
          '8) flag acceso, rollback con un task distruttivo: non parte da solo');

SELECT pg_temp.assetto(true, '[{"task": "zz_pgtap_rb_sicuro"}, {"task": "zz_pgtap_rb_spento"}]');
SELECT is(pg_temp.ammesso(), false,
          '9) flag acceso, rollback con un task spento: non parte da solo (fail-closed)');

SELECT pg_temp.assetto(true, '[{"task": "zz_pgtap_rb_sicuro"}, {"task": "zz_pgtap_rb_che_non_esiste"}]');
SELECT is(pg_temp.ammesso(), false,
          '10) flag acceso, rollback con un task che il registro non conosce: non parte da solo (fail-closed)');

SELECT pg_temp.assetto(true, '[{"task": "zz_pgtap_rb_sicuro"}, {"nome": "zz_pgtap_rb_sicuro"}]');
SELECT is(pg_temp.ammesso(), false,
          '11) flag acceso, un elemento del rollback senza la chiave «task»: non parte da solo');

SELECT pg_temp.assetto(true, '[{"task": "zz_pgtap_rb_sicuro"}]', '[{"task": "zz_pgtap_rb_distruttivo"}]');
SELECT is(pg_temp.ammesso(), true,
          '12) un task distruttivo nei processi non chiude il rollback: conta il rollback dello step');

-- ============================================================
-- 13-14 Lo step
-- ============================================================
SELECT is(vendite.fn_check_rollback_step_automatico('MASSIVO', (SELECT stato_vuoto_id FROM tmp_rb_ids)),
          false,
          '13) uno step che non si risolve: false');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'SELECT vendite.fn_check_rollback_step_automatico(NULL, %s)', (SELECT stato_id FROM tmp_rb_ids))),
  'E_PARAMETRO_INVALIDO',
  '14) p_tipo_lotto NULL: E_PARAMETRO_INVALIDO, dalla risoluzione dello step');

SELECT * FROM finish();
ROLLBACK;
