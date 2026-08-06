-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.event_log + vendite.fn_log_event
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) tabella event_log presente
-- 2) funzione fn_log_event presente
-- 3) insert base via fn_log_event -> id valorizzato
-- 4) evento base persistito correttamente
-- 5) severity default = INFO quando NULL
-- 6) payload default = {} quando NULL
-- 7) severity invalida bloccata dal CHECK
-- 8) append-only: UPDATE e DELETE bloccati da trigger
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

SELECT plan(9);
SELECT ok(
    to_regclass('vendite.event_log') IS NOT NULL,
    'tabella event_log presente'
  );
SELECT ok(
    EXISTS (
      SELECT 1
      FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname = 'fn_log_event'
    ),
    'funzione fn_log_event presente'
  );
CREATE TEMP TABLE tmp_event_log_base AS
SELECT vendite.fn_log_event(
    p_domain => 'PIPELINE',
    p_entity_type => 'LOTTO',
    p_entity_id => 123,
    p_event_code => 'STEP_STARTED',
    p_severity => 'INFO',
    p_correlation_id => NULL::uuid,
    p_actor => 'service:pgtap',
    p_source => 'sql',
    p_payload => jsonb_build_object('step', 'DRAFT')
  ) AS event_id;
SELECT ok(
    (
      SELECT event_id IS NOT NULL
      FROM tmp_event_log_base
    ),
    'insert base via fn_log_event -> id valorizzato'
  );
SELECT ok(
    EXISTS (
      SELECT 1
      FROM vendite.event_log e
      WHERE e.id = (
          SELECT event_id
          FROM tmp_event_log_base
        )
        AND e.domain = 'PIPELINE'
        AND e.entity_type = 'LOTTO'
        AND e.entity_id = 123
        AND e.event_code = 'STEP_STARTED'
        AND e.severity = 'INFO'
        AND e.actor = 'service:pgtap'
        AND e.source = 'sql'
        AND e.payload->>'step' = 'DRAFT'
    ),
    'evento base persistito correttamente'
  );
CREATE TEMP TABLE tmp_event_log_defaults AS
SELECT vendite.fn_log_event(
    p_domain => 'COMMESSE',
    p_entity_type => 'COMMESSA',
    p_entity_id => 456,
    p_event_code => 'PUSH_COMPLETED',
    p_severity => NULL,
    p_correlation_id => NULL::uuid,
    p_actor => NULL,
    p_source => NULL,
    p_payload => NULL
  ) AS event_id;
SELECT is(
    (
      SELECT e.severity
      FROM vendite.event_log e
      WHERE e.id = (
          SELECT event_id
          FROM tmp_event_log_defaults
        )
    ),
    'INFO'::text,
    'severity default = INFO quando NULL'
  );
SELECT is(
    (
      SELECT e.payload
      FROM vendite.event_log e
      WHERE e.id = (
          SELECT event_id
          FROM tmp_event_log_defaults
        )
    ),
    '{}'::jsonb,
    'payload default = {} quando NULL'
  );
SELECT throws_ok(
    $$
    SELECT vendite.fn_log_event(
        p_domain => 'PIPELINE',
        p_entity_type => 'LOTTO',
        p_entity_id => 1,
        p_event_code => 'STEP_FAILED',
        p_severity => 'KO',
        p_correlation_id => NULL::uuid,
        p_actor => NULL,
        p_source => NULL,
        p_payload => '{}'::jsonb
      );
$$,
'23514',
NULL,
'severity invalida bloccata dal CHECK'
);
SELECT throws_ok(
    $$
    UPDATE vendite.event_log
    SET event_code = 'MUTATED'
    WHERE id = (
        SELECT event_id
        FROM tmp_event_log_base
      );
$$,
'P0001',
NULL,
'append-only: UPDATE bloccato'
);
SELECT throws_ok(
    $$
    DELETE FROM vendite.event_log
    WHERE id = (
        SELECT event_id
        FROM tmp_event_log_base
      );
$$,
'P0001',
NULL,
'append-only: DELETE bloccato'
);
SELECT *
FROM finish();
ROLLBACK;