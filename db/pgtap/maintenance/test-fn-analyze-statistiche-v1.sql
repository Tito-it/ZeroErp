-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le statistiche del planner — il verbo, la sua autoverifica, il perimetro
--       e il processo che lo porta in pgAgent e in CI (D15)
-- Brief: brief-db-statistiche-tabelle-job-notturno §4, §5
--
-- Elenco test (plan 10):
--  1) la vista e il verbo esistono
--  2) prima di ANALYZE: le tabelle temporanee costruite qui sono MAI_ANALIZZATA
--     (piena, vuota, partizionata con una partizione, e la partizione)
--  3) la partizionata SENZA partizioni non c'e': non ha dati da descrivere,
--     e resta a reltuples -1 anche dopo ANALYZE
--  4) il verbo sulle tabelle costruite ritorna 0 (non solleva)
--  5) dopo il verbo nessuna di loro e' piu' senza statistiche — vuota compresa
--  6) una tabella che il ruolo non puo' analizzare e' NON_ANALIZZABILE
--  7) ⭐ il verbo su quella tabella SOLLEVA E_STATISTICHE_MANCANTI: ANALYZE la
--     salta con un WARNING, e senza l'autoverifica il giornale direbbe «done»
--  8) nessun oggetto di un'estensione e' nel perimetro
--  9) il processo analyze_statistiche e' a catalogo come job pgAgent, con
--     jobname = codice e la procedura che esiste
-- 10) ed e' l'ULTIMO della convergenza in CI: si analizza dopo che le
--     automazioni hanno creato le tabelle di storico
--
-- ── Perche' le temporanee ────────────────────────────────────────────
--   Il runner gira come zeroerp_app, che non possiede nessuna tabella di
--   progetto e non puo' crearne. Le temporanee della SESSIONE CORRENTE sono nel
--   perimetro della vista apposta: il caso si costruisce, non si cerca. E il
--   verbo riceve l'elenco (p_tabelle), cosi' il test non analizza tutto il
--   database.
--
-- ⚠️ 6 e 7 dipendono dal RUOLO del runner: come owner o superuser la tabella
--   del giornale e' analizzabile e il caso negativo non si costruisce. Li'
--   sono skip() dichiarati, non verdi per sottrazione.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture: quattro forme di tabella, mai analizzate
-- ============================================================
CREATE TEMP TABLE t_stat_piena (a integer);
INSERT INTO t_stat_piena SELECT g FROM generate_series(1, 20) AS g;

CREATE TEMP TABLE t_stat_vuota (a integer);

CREATE TEMP TABLE t_stat_part (a integer) PARTITION BY RANGE (a);
CREATE TEMP TABLE t_stat_part_1 PARTITION OF t_stat_part FOR VALUES FROM (0) TO (100);
INSERT INTO t_stat_part VALUES (5), (6);

CREATE TEMP TABLE t_stat_part_senza (a integer) PARTITION BY RANGE (a);

-- L'esito di un'istruzione: NULL se passa, il codice di dominio (CONSTRAINT)
-- se solleva P0001, altrimenti lo SQLSTATE.
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' THEN v_c ELSE v_s || ' ' || coalesce(v_c, '') END;
END $$;

-- ============================================================
-- 1. Gli oggetti
-- ============================================================
SELECT ok(
    to_regclass('maintenance.vw_statistiche_mancanti') IS NOT NULL
    AND to_regprocedure('maintenance.fn_analyze_statistiche(regclass[])') IS NOT NULL,
    '1. maintenance.vw_statistiche_mancanti e maintenance.fn_analyze_statistiche esistono'
);

-- ============================================================
-- 2..3. Prima di ANALYZE
-- ============================================================
SELECT set_eq(
    $$SELECT tabella_nome, motivo FROM maintenance.vw_statistiche_mancanti
       WHERE relid IN ('pg_temp.t_stat_piena'::regclass, 'pg_temp.t_stat_vuota'::regclass,
                       'pg_temp.t_stat_part'::regclass, 'pg_temp.t_stat_part_1'::regclass)$$,
    $$VALUES ('t_stat_piena', 'MAI_ANALIZZATA'), ('t_stat_vuota', 'MAI_ANALIZZATA'),
             ('t_stat_part', 'MAI_ANALIZZATA'), ('t_stat_part_1', 'MAI_ANALIZZATA')$$,
    '2. prima di ANALYZE le quattro tabelle costruite sono MAI_ANALIZZATA'
);

SELECT is_empty(
    $$SELECT 1 FROM maintenance.vw_statistiche_mancanti
       WHERE relid = 'pg_temp.t_stat_part_senza'::regclass$$,
    '3. la partizionata senza partizioni non e'' nel perimetro: non ha dati da descrivere'
);

-- ============================================================
-- 4..5. Il verbo
-- ============================================================
SELECT is(
    maintenance.fn_analyze_statistiche(ARRAY[
        'pg_temp.t_stat_piena'::regclass, 'pg_temp.t_stat_vuota'::regclass,
        'pg_temp.t_stat_part'::regclass,  'pg_temp.t_stat_part_1'::regclass,
        'pg_temp.t_stat_part_senza'::regclass]),
    0,
    '4. il verbo sulle tabelle costruite ritorna 0 e non solleva'
);

SELECT is_empty(
    $$SELECT tabella_nome FROM maintenance.vw_statistiche_mancanti
       WHERE relid IN ('pg_temp.t_stat_piena'::regclass, 'pg_temp.t_stat_vuota'::regclass,
                       'pg_temp.t_stat_part'::regclass, 'pg_temp.t_stat_part_1'::regclass,
                       'pg_temp.t_stat_part_senza'::regclass)$$,
    '5. dopo il verbo nessuna tabella costruita e'' senza statistiche, la vuota compresa'
);

-- ============================================================
-- 6..7. ⭐ La tabella che il ruolo non puo' analizzare
-- ============================================================
SELECT CASE
    WHEN has_table_privilege('maintenance.job_run_log'::regclass, 'MAINTAIN') THEN
        skip('il runner puo'' analizzare maintenance.job_run_log (owner o superuser): il caso negativo si costruisce solo come zeroerp_app', 2)
    ELSE
        is((SELECT motivo FROM maintenance.vw_statistiche_mancanti
             WHERE relid = 'maintenance.job_run_log'::regclass),
           'NON_ANALIZZABILE',
           '6. maintenance.job_run_log, senza MAINTAIN, e'' NON_ANALIZZABILE')
        || E'\n' ||
        is(pg_temp.esito($$SELECT maintenance.fn_analyze_statistiche(
                              ARRAY['maintenance.job_run_log'::regclass])$$),
           'E_STATISTICHE_MANCANTI',
           '7. il verbo su una tabella che ANALYZE salterebbe solleva E_STATISTICHE_MANCANTI')
END;

-- ============================================================
-- 8. Il perimetro esclude le estensioni, per struttura
-- ============================================================
SELECT is_empty(
    $$SELECT m.relid::text
        FROM maintenance.vw_statistiche_mancanti m
        JOIN pg_catalog.pg_depend d
          ON d.classid = 'pg_catalog.pg_class'::regclass
         AND d.objid = m.relid
         AND d.refclassid = 'pg_catalog.pg_extension'::regclass
         AND d.deptype = 'e'$$,
    '8. nessun oggetto di un''estensione e'' nel perimetro'
);

-- ============================================================
-- 9..10. Il processo
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM dbops.processi p
             WHERE p.codice = 'analyze_statistiche'
               AND p.attivo
               AND p.canale = 'PGAGENT'
               AND p.jobname_pgagent = p.codice
               AND to_regprocedure(p.ci_procedura) = 'maintenance.proc_analyze_statistiche_job()'::regprocedure),
    '9. analyze_statistiche e'' a catalogo: job pgAgent, jobname = codice, procedura esistente'
);

SELECT is(
    (SELECT p.codice FROM dbops.processi p
      WHERE p.attivo AND p.ci_ordine IS NOT NULL
      ORDER BY p.ci_ordine DESC, p.codice
      LIMIT 1),
    'analyze_statistiche',
    '10. ed e'' l''ultimo della convergenza in CI'
);

SELECT * FROM finish();
ROLLBACK;
