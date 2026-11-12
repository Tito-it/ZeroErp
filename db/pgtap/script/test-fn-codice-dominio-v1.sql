-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_codice_dominio
--       Il codice di dominio di un errore catturato: il CONSTRAINT quando lo
--       SQLSTATE e' P0001 e il CONSTRAINT non e' vuoto (il contratto di
--       script.fn_log_and_raise_error), NULL altrimenti. E la regola ha una
--       sede sola: i due lettori la chiamano, nessuno la ricopia.
--
-- Elenco test:
--  1) P0001 + vincolo valorizzato -> il vincolo (il codice)
--  2) P0001 + vincolo vuoto       -> NULL (un RAISE di dominio senza codice)
--  3) P0001 + vincolo NULL        -> NULL
--  4) 23505 + vincolo valorizzato -> NULL (il nome di un vincolo, non un codice)
--  5) SQLSTATE NULL               -> NULL
--  6) dalla vera diagnostica: un E_ di fn_log_and_raise_error -> il codice;
--     un 23514 di un CHECK -> NULL
--  7) regola del 2: vendite.fn_batch_upsert_commessa_attivita e
--     maintenance.fn_run_and_log chiamano il BB, e nessuna delle due confronta
--     piu' lo SQLSTATE con 'P0001' sul posto
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   IMMEDIATE li riporta a scattare a fine di ogni istruzione (il COMMIT qui
--   non arriva mai).
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (ruolo OPERATORE +
-- RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- 1-5) La regola sui valori
-- ============================================================
SELECT is(script.fn_codice_dominio('P0001', 'E_UOM_MISSING'), 'E_UOM_MISSING',
    'P0001 + vincolo valorizzato: il codice');

SELECT is(script.fn_codice_dominio('P0001', ''), NULL,
    'P0001 + vincolo vuoto: NULL');

SELECT is(script.fn_codice_dominio('P0001', NULL), NULL,
    'P0001 + vincolo NULL: NULL');

SELECT is(script.fn_codice_dominio('23505', 'uq_qualcosa'), NULL,
    '23505 + vincolo: NULL, e'' il nome di un vincolo e non un codice');

SELECT is(script.fn_codice_dominio(NULL, 'E_UOM_MISSING'), NULL,
    'SQLSTATE NULL: NULL');

-- ============================================================
-- 6) Dalla vera diagnostica di un'eccezione
-- ============================================================
CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE
    v_sqlstate text;
    v_vincolo  text;
BEGIN
    EXECUTE p_sql;
    RETURN '(nessun errore)';
EXCEPTION WHEN others THEN
    GET STACKED DIAGNOSTICS v_sqlstate = RETURNED_SQLSTATE,
                            v_vincolo  = CONSTRAINT_NAME;
    RETURN script.fn_codice_dominio(v_sqlstate, v_vincolo);
END $$;

SELECT is(
    pg_temp.codice_di($q$
        SELECT script.fn_log_and_raise_error(
            'script', 'pgtap', 'E_UOM_MISSING',
            jsonb_build_object('campo', 'uom_id'), NULL::uuid,
            'U', 'B', 'A', '2026-01-01')
    $q$),
    'E_UOM_MISSING',
    'un errore di fn_log_and_raise_error: il codice dal canale CONSTRAINT');

CREATE TEMP TABLE tmp_check_dominio (n integer CONSTRAINT chk_tmp_positivo CHECK (n > 0));

SELECT is(
    pg_temp.codice_di('INSERT INTO tmp_check_dominio VALUES (0)'),
    NULL,
    'un 23514 di un CHECK: NULL, anche se il CONSTRAINT e'' valorizzato');

-- ============================================================
-- 7) Regola del 2: i lettori chiamano il BB, nessuno ricopia il confronto
-- ============================================================
--   Il nome si compone da pg_namespace: un regprocedure::text perde lo schema
--   quando lo schema e' nel search_path.
SELECT is(
    (SELECT array_agg(n.nspname || '.' || p.proname ORDER BY n.nspname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE p.oid IN ('vendite.fn_batch_upsert_commessa_attivita(jsonb)'::regprocedure,
                      'maintenance.fn_run_and_log(text, text, text, bigint, text, integer)'::regprocedure)
        AND p.prosrc LIKE '%script.fn_codice_dominio(%'
        AND p.prosrc NOT LIKE '%= ''P0001''%'),
    ARRAY['maintenance.fn_run_and_log'::text,
          'vendite.fn_batch_upsert_commessa_attivita'::text],
    'il batch e fn_run_and_log leggono script.fn_codice_dominio, senza una copia del confronto');

SELECT * FROM finish();
ROLLBACK;
