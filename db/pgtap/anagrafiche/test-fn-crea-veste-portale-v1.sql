-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La veste dei portali:
--   anagrafiche.fn_crea_veste_portale   (20261018-39)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 6).
--
-- ⭐ Il caso si COSTRUISCE: un cliente e un fornitore dai builder, due
--   operatori umani dal builder (persone: la natura della credenziale ammette
--   le vesti esterne; un utente tecnico no).
-- ⚠️ I guard della tabella (coerenza veste/ruolo, unicita', natura) hanno i
--   loro pgTAP, che scrivono la tabella a mano apposta: qui si prova che il BB
--   li attraversa, non che li ripete.
--
-- Elenco test (plan 9):
--   forma
--    1) INVOKER
--   il caso felice
--    2) una veste del portale clienti spenta, sul ruolo cliente
--    3) una veste dello shop accesa, sullo stesso ruolo
--    4) una veste del portale fornitori, sul ruolo fornitore
--   i rifiuti del BB
--    5) la veste OPERATORE: E_SCRIPT_CHIAMATA_NON_VALIDA (ha le sue madri)
--    6) attivo NULL: E_SCRIPT_CHIAMATA_NON_VALIDA (nessun default)
--   i guard della tabella, attraverso il BB
--    7) il portale clienti su un ruolo fornitore: rifiutato dal guard di coerenza
--   la copia del backend
--    8) il BB scrive con script.fn_scrivi_riga_da_jsonb
--    9) nessuna funzione DB scrive una veste esterna a mano
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

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

CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

CREATE TEMP TABLE t_m AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(dbops.fn_pgtap_crea_soggetto_pg('Veste cliente pgTAP'), 'CL')   AS sr_cl,
       dbops.fn_pgtap_crea_soggetto_ruolo(dbops.fn_pgtap_crea_soggetto_pg('Veste fornitore pgTAP'), 'FO') AS sr_fo;

CREATE TEMP TABLE t_u AS
SELECT (SELECT o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('Veste pgTAP 1', false) o) AS au1,
       (SELECT o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('Veste pgTAP 2', false) o) AS au2;

CREATE TEMP TABLE t_v AS
SELECT anagrafiche.fn_crea_veste_portale(u.au1, m.sr_cl, 'CLIENTE_PORTALE', false)   AS v_cp,
       anagrafiche.fn_crea_veste_portale(u.au1, m.sr_cl, 'SHOP_CUSTOMER', true)      AS v_shop,
       anagrafiche.fn_crea_veste_portale(u.au2, m.sr_fo, 'FORNITORE_PORTALE', false) AS v_fp
  FROM t_m m, t_u u;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'anagrafiche.fn_crea_veste_portale(integer, bigint, config.ruolo_applicativo, boolean)'::regprocedure),
    false,
    '1. il BB e'' INVOKER');

-- ============================================================
-- Il caso felice
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', i.ruolo_applicativo, i.attivo, i.soggetto_ruolo_id = m.sr_cl)
       FROM t_v v JOIN anagrafiche.identita_digitali i ON i.id = v.v_cp, t_m m),
    'CLIENTE_PORTALE|f|t',
    '2. una veste del portale clienti spenta, sul ruolo cliente');

SELECT is(
    (SELECT format('%s|%s', i.ruolo_applicativo, i.attivo)
       FROM t_v v JOIN anagrafiche.identita_digitali i ON i.id = v.v_shop),
    'SHOP_CUSTOMER|t',
    '3. una veste dello shop accesa, sullo stesso ruolo');

SELECT is(
    (SELECT format('%s|%s', i.ruolo_applicativo, i.soggetto_ruolo_id = m.sr_fo)
       FROM t_v v JOIN anagrafiche.identita_digitali i ON i.id = v.v_fp, t_m m),
    'FORNITORE_PORTALE|t',
    '4. una veste del portale fornitori, sul ruolo fornitore');

-- ============================================================
-- I rifiuti del BB
-- ============================================================
SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_veste_portale(
        (SELECT au2 FROM t_u), (SELECT sr_cl FROM t_m), 'OPERATORE', true)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '5. la veste OPERATORE: E_SCRIPT_CHIAMATA_NON_VALIDA (ha le sue madri)');

SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_veste_portale(
        (SELECT au2 FROM t_u), (SELECT sr_cl FROM t_m), 'CLIENTE_PORTALE', NULL)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '6. attivo NULL: E_SCRIPT_CHIAMATA_NON_VALIDA (nessun default)');

-- ============================================================
-- I guard della tabella, attraverso il BB
-- ============================================================
SELECT isnt(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_veste_portale(
        (SELECT au2 FROM t_u), (SELECT sr_fo FROM t_m), 'CLIENTE_PORTALE', false)$$),
    NULL,
    '7. il portale clienti su un ruolo fornitore: lo rifiuta il guard di coerenza');

-- ============================================================
-- Le copie
-- ============================================================
SELECT ok(
    pg_temp.corpo('anagrafiche.fn_crea_veste_portale(integer, bigint, config.ruolo_applicativo, boolean)'::regprocedure)
        ~ 'script\.fn_scrivi_riga_da_jsonb\(',
    '8. il BB scrive con script.fn_scrivi_riga_da_jsonb');

SELECT is(
    (SELECT string_agg(p.oid::regprocedure::text, ', ')
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND p.prokind = 'f'
        AND pg_temp.corpo(p.oid::regprocedure) ~* 'INSERT\s+INTO\s+anagrafiche\.identita_digitali'
        AND pg_temp.corpo(p.oid::regprocedure) ~ '(CLIENTE_PORTALE|FORNITORE_PORTALE|SHOP_CUSTOMER)'),
    NULL,
    '9. nessuna funzione DB scrive una veste esterna a mano');

SELECT * FROM finish();

ROLLBACK;
