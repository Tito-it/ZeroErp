-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il BB del contatto e le quattro funzioni che lo usano al posto delle copie:
--   anagrafiche.fn_crea_contatto        (20261017-13)
--   anagrafiche.fn_crea_soggetto_pf     (20261017-14)
--   anagrafiche.fn_crea_soggetto_pg     (20261017-15)
--   script.fn_crea_utente_tecnico       (20261017-16)
--   dbops.fn_pgtap_crea_soggetto_pg     (20261017-17)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 3).
--
-- ⭐ Il soggetto si COSTRUISCE col builder, che ora scrive il proprio
--   contatto attraverso il BB: e' gia' la prima prova del ritiro.
--
-- Elenco test (plan 13):
--   forma
--    1) INVOKER
--   il caso felice
--    2) il builder ha scritto il contatto di default attraverso il BB
--    3) un contatto di soggetto: nominativo, email, tipo, ruolo NULL
--    4) un contatto di ruolo: porta il ruolo
--    5) una chiave assente resta al DEFAULT della colonna (pec vuota)
--   i rifiuti
--    6) nominativo vuoto: E_CONTATTO_INCOMPLETO
--    7) ... col campo nominativo sul canale COLUMN
--    8) tipo di contatto assente: E_CONTATTO_INCOMPLETO, campo tipo_contatto_id
--    9) chiave estranea: E_CAMPO_NON_AMMESSO
--   10) soggetto NULL: E_SCRIPT_CHIAMATA_NON_VALIDA
--   le copie ritirate
--   11) nessuna delle quattro funzioni scrive piu' anagrafiche.contatti a mano
--   12) ... e tutte e quattro chiamano il BB
--   13) il BB scrive con script.fn_scrivi_riga_da_jsonb
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.colonna_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = COLUMN_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

CREATE TEMP TABLE t_s AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Contatti pgTAP') AS soggetto_id,
       (SELECT t.id FROM config.tipi_contatti t ORDER BY t.id LIMIT 1) AS tipo_id,
       -- ⚠️ Un contatto per (soggetto, tipo) a livello soggetto
       --   (uq_contatti_soggetto_tipo): il primo tipo l'ha gia' preso il
       --   contatto di default del builder.
       (SELECT t.id FROM config.tipi_contatti t ORDER BY t.id OFFSET 1 LIMIT 1) AS tipo2_id;

CREATE TEMP TABLE t_sr AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.soggetto_id, 'FO') AS sr_id FROM t_s s;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'anagrafiche.fn_crea_contatto(uuid, bigint, jsonb)'::regprocedure),
    false,
    '1. il BB e'' INVOKER');

-- ============================================================
-- Il caso felice
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', c.nominativo, c.is_default)
       FROM anagrafiche.contatti c JOIN t_s s ON s.soggetto_id = c.soggetto_id
      WHERE c.soggetto_ruolo_id IS NULL),
    'Referente Contatti pgTAP|t',
    '2. il builder ha scritto il contatto di default, attraverso il BB');

CREATE TEMP TABLE t_c1 AS
SELECT anagrafiche.fn_crea_contatto(
           s.soggetto_id, NULL,
           jsonb_build_object('nominativo', 'Mario Contatto', 'email', 'mario@example.com',
                              'tipo_contatto_id', s.tipo2_id)) AS r
  FROM t_s s;

SELECT is(
    (SELECT format('%s|%s|%s', r ->> 'nominativo', r ->> 'email', r -> 'soggetto_ruolo_id') FROM t_c1),
    'Mario Contatto|mario@example.com|null',
    '3. un contatto di soggetto: nominativo, email, ruolo NULL');

CREATE TEMP TABLE t_c2 AS
SELECT anagrafiche.fn_crea_contatto(
           s.soggetto_id, r.sr_id,
           jsonb_build_object('nominativo', 'Ufficio acquisti', 'tipo_contatto_id', s.tipo_id)) AS r
  FROM t_s s, t_sr r;

SELECT is((SELECT (c.r ->> 'soggetto_ruolo_id')::bigint FROM t_c2 c), (SELECT sr_id FROM t_sr),
          '4. un contatto di ruolo: porta il ruolo');

-- ⚠️ Non is_default: il primo contatto di un ruolo diventa quello di
--   default per opera di un trigger della tabella (il modello, non il BB).
SELECT is((SELECT r -> 'pec' FROM t_c2), 'null'::jsonb,
          '5. una chiave assente resta al DEFAULT della colonna (pec vuota)');

-- ============================================================
-- I rifiuti
-- ============================================================
SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_contatto((SELECT soggetto_id FROM t_s), NULL,
        jsonb_build_object('nominativo', '   ', 'tipo_contatto_id', (SELECT tipo_id FROM t_s)))$$),
    'E_CONTATTO_INCOMPLETO',
    '6. nominativo vuoto: E_CONTATTO_INCOMPLETO');

SELECT is(
    pg_temp.colonna_errore($$SELECT anagrafiche.fn_crea_contatto((SELECT soggetto_id FROM t_s), NULL,
        jsonb_build_object('nominativo', '   ', 'tipo_contatto_id', (SELECT tipo_id FROM t_s)))$$),
    'nominativo',
    '7. ... col campo nominativo sul canale COLUMN');

SELECT is(
    pg_temp.colonna_errore($$SELECT anagrafiche.fn_crea_contatto((SELECT soggetto_id FROM t_s), NULL,
        '{"nominativo": "Senza tipo"}'::jsonb)$$),
    'tipo_contatto_id',
    '8. tipo di contatto assente: E_CONTATTO_INCOMPLETO sul campo tipo_contatto_id');

SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_contatto((SELECT soggetto_id FROM t_s), NULL,
        '{"nominativo": "x", "tipo_contatto_id": 1, "soggetto_id": "00000000-0000-0000-0000-000000000000"}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '9. chiave estranea (anche soggetto_id nei campi): E_CAMPO_NON_AMMESSO');

SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_contatto(NULL, NULL, '{"nominativo": "x", "tipo_contatto_id": 1}'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '10. soggetto NULL: E_SCRIPT_CHIAMATA_NON_VALIDA');

-- ============================================================
-- Le copie ritirate (sul corpo, senza commenti)
-- ============================================================
CREATE TEMP TABLE t_quattro AS
SELECT p.oid::regprocedure AS f
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE (n.nspname, p.proname) IN (('anagrafiche', 'fn_crea_soggetto_pf'), ('anagrafiche', 'fn_crea_soggetto_pg'),
                                  ('script', 'fn_crea_utente_tecnico'), ('dbops', 'fn_pgtap_crea_soggetto_pg'));

SELECT is(
    (SELECT count(*)::int FROM t_quattro WHERE pg_temp.corpo(f) ~* 'INSERT\s+INTO\s+anagrafiche\.contatti'),
    0,
    '11. nessuna delle quattro scrive piu'' anagrafiche.contatti a mano');

SELECT is(
    (SELECT count(*)::int FROM t_quattro WHERE pg_temp.corpo(f) ~ 'anagrafiche\.fn_crea_contatto\('),
    4,
    '12. ... e tutte e quattro chiamano il BB');

SELECT ok(
    pg_temp.corpo('anagrafiche.fn_crea_contatto(uuid, bigint, jsonb)'::regprocedure) ~ 'script\.fn_scrivi_riga_da_jsonb\(',
    '13. il BB scrive con script.fn_scrivi_riga_da_jsonb');

SELECT * FROM finish();

ROLLBACK;
