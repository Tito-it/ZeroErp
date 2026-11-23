-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- script.fn_guard_campi_ammessi (20261123-01): la regola delle porte di
-- scrittura che ricevono i campi in jsonb, e le porte che la usano al posto
-- delle copie (20261123-02 magazzino, -03 anagrafiche, -04 config).
-- Brief: brief-db-magazzino-tutte-le-scritture-dal-verbo, P-5a.
--
-- ⭐ I casi si costruiscono: il guard si chiama coi suoi argomenti, non
--   attraverso una porta che pesca dati.
--
-- Elenco test (plan 13):
--   forma
--    1) INVOKER, void, VOLATILE (scrive il log quando solleva)
--   la regola
--    2) campi ammessi: passa
--    3) campi vuoti: passa, anche con l'elenco NULL
--    4) campi che non sono un oggetto (un array): E_SCRIPT_CHIAMATA_NON_VALIDA
--    5) campi NULL: E_SCRIPT_CHIAMATA_NON_VALIDA (chi non ha campi passa '{}')
--    6) una chiave fuori lista: E_CAMPO_NON_AMMESSO
--    7) ... e il campo viaggia in context.campo (COLUMN_NAME): la prima in
--       ordine alfabetico
--    8) ... e nella frase, al posto del segnaposto
--    9) elenco NULL: nessuna chiave ammessa
--   10) il contesto della porta resta, accanto al campo (dal log: skip
--       dichiarato dove il canale dblink del log e' spento, perche' dentro
--       un blocco EXCEPTION la riga scritta nella transazione si perde)
--   le porte (sul corpo, senza commenti)
--   11) le quindici porte chiamano il guard
--   12) fuori dal guard nessuna funzione solleva E_CAMPO_NON_AMMESSO da se':
--       il codice ha una sede sola (il pannello ha il suo codice)
--   13) il pannello resta sul suo codice, E_PANNELLO_CAMPO_NON_AMMESSO
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);


-- Il campo (context.campo esce in COLUMN_NAME), la frase, il contesto.
CREATE OR REPLACE FUNCTION pg_temp.campo_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = COLUMN_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.frase_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    RETURN SQLERRM;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;


-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', p.prosecdef, p.prorettype::regtype, p.provolatile)
       FROM pg_proc p
      WHERE p.oid = 'script.fn_guard_campi_ammessi(jsonb, text[], text, text, jsonb)'::regprocedure),
    'f|void|v',
    '1. INVOKER, void, VOLATILE');


-- ============================================================
-- La regola
-- ============================================================
SELECT lives_ok(
    $$SELECT script.fn_guard_campi_ammessi('{"a": 1, "b": null}'::jsonb, ARRAY['a', 'b', 'c'],
                                           'script', 'pgtap.porta')$$,
    '2. campi ammessi: passa');

SELECT lives_ok(
    $$SELECT script.fn_guard_campi_ammessi('{}'::jsonb, NULL, 'script', 'pgtap.porta')$$,
    '3. campi vuoti: passa, anche con l''elenco NULL');

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$SELECT script.fn_guard_campi_ammessi('[1]'::jsonb, ARRAY['a'], 'script', 'pgtap.porta')$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '4. campi che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$SELECT script.fn_guard_campi_ammessi(NULL, ARRAY['a'], 'script', 'pgtap.porta')$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '5. campi NULL: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$SELECT script.fn_guard_campi_ammessi('{"a": 1, "zeta": 2}'::jsonb, ARRAY['a'],
                                               'script', 'pgtap.porta')$$),
    'E_CAMPO_NON_AMMESSO',
    '6. una chiave fuori lista: E_CAMPO_NON_AMMESSO');

SELECT is(
    pg_temp.campo_di(
        $$SELECT script.fn_guard_campi_ammessi('{"zeta": 1, "emme": 2, "a": 3}'::jsonb, ARRAY['a'],
                                               'script', 'pgtap.porta')$$),
    'emme',
    '7. il campo in context.campo: la prima chiave estranea in ordine alfabetico');

SELECT ok(
    pg_temp.frase_di(
        $$SELECT script.fn_guard_campi_ammessi('{"emme": 1}'::jsonb, ARRAY['a'],
                                               'script', 'pgtap.porta')$$) LIKE '%emme%'
    AND pg_temp.frase_di(
        $$SELECT script.fn_guard_campi_ammessi('{"emme": 1}'::jsonb, ARRAY['a'],
                                               'script', 'pgtap.porta')$$) NOT LIKE '%\%s%',
    '8. il campo e'' nella frase, al posto del segnaposto');

SELECT is(
    pg_temp.campo_di(
        $$SELECT script.fn_guard_campi_ammessi('{"a": 1}'::jsonb, NULL, 'script', 'pgtap.porta')$$),
    'a',
    '9. elenco NULL: nessuna chiave ammessa');

-- Il contesto della porta resta: il guard aggiunge la sua chiave, non lo
-- sostituisce. Il contesto sta nel log (dbops.error_log), scritto a nome
-- della porta (area, function_name). In un DO: una SELECT nuda stamperebbe
-- il suo risultato in mezzo al flusso TAP.
-- Il canale: il controllo di script/test-canale-log-v1.
SET LOCAL myapp.log_with_dblink = 'on';
SET LOCAL dbops.tx_id = '';
CREATE TEMP TABLE _canale ON COMMIT DROP AS
SELECT dbops.fn_get_or_create_session_tx_id() <> script.uuid_nil() AS operativo;

DO $dieci$
BEGIN
    PERFORM pg_temp.campo_di(
        $$SELECT script.fn_guard_campi_ammessi('{"x": 1}'::jsonb, ARRAY['a'], 'pgtap',
                                               'pgtap.guard_campi_contesto',
                                               jsonb_build_object('codice', 'PGT-GCA'))$$);
END $dieci$;

SELECT CASE WHEN (SELECT operativo FROM _canale)
    THEN is((SELECT e.context ->> 'campo' || '|' || (e.context ->> 'codice')
               FROM dbops.error_log e
              WHERE e.area = 'pgtap'
                AND e.function_name = 'pgtap.guard_campi_contesto'
              ORDER BY e.id DESC
              LIMIT 1),
            'x|PGT-GCA',
            '10. il log e'' della porta, e il suo contesto resta accanto al campo')
    ELSE skip('10. canale di log dblink spento: la riga scritta dentro il blocco EXCEPTION si perde', 1)
END;


-- ============================================================
-- Le porte
-- ============================================================
SELECT is(
    (SELECT array_agg(f ORDER BY f)
       FROM unnest(ARRAY[
                'magazzino.fn_crea_magazzino', 'magazzino.fn_crea_ubicazione',
                'magazzino.fn_crea_lotto', 'magazzino.fn_crea_asset',
                'magazzino.fn_modifica_magazzino', 'magazzino.fn_modifica_ubicazione',
                'magazzino.fn_modifica_lotto',
                'anagrafiche.fn_crea_emittente_fiscale', 'anagrafiche.fn_crea_fornitore',
                'anagrafiche.fn_crea_cliente', 'anagrafiche.fn_crea_billing_account',
                'anagrafiche.fn_crea_contatto', 'anagrafiche.fn_indirizzo_elemento',
                'config.fn_scrivi_profilo_accesso', 'config.fn_imposta_override_oggetti']) AS f
      WHERE pg_temp.corpo(f::regproc::regprocedure) !~ 'script\.fn_guard_campi_ammessi\('),
    NULL,
    '11. le quindici porte chiamano il guard (nessuna lo salta)');

SELECT is(
    (SELECT array_agg(p.oid::regprocedure::text ORDER BY 1)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
        AND p.oid <> 'script.fn_guard_campi_ammessi(jsonb, text[], text, text, jsonb)'::regprocedure
        AND pg_temp.corpo(p.oid::regprocedure) ~ '''E_CAMPO_NON_AMMESSO'''),
    NULL,
    '12. fuori dal guard nessuna funzione solleva E_CAMPO_NON_AMMESSO da se''');

SELECT ok(
    pg_temp.corpo('config.fn_pannello_scrivi(text, bigint, jsonb)'::regprocedure) ~ '''E_PANNELLO_CAMPO_NON_AMMESSO'''
    AND pg_temp.corpo('config.fn_pannello_scrivi(text, bigint, jsonb)'::regprocedure) !~ 'fn_guard_campi_ammessi',
    '13. il pannello resta sul suo codice, E_PANNELLO_CAMPO_NON_AMMESSO');

SELECT * FROM finish();

ROLLBACK;
