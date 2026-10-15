-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il blocco manuale diventa un atto con un verbo (D-L3-j) e la
--   postura del Lotto 3 — cio' che l'app esegue e cio' che non puo'
--   eseguire. Le TRE sedi della postura (loop ci_apply 20260205-41,
--   forward 90_end, provision_zeroerp.sql (fase post)) le tiene allineate questo file:
--   su un database ricostruito da zero, se una sede manca, qui e' rosso.
--   Brief: brief-db-magazzino-lotto-3-scarico-da-ddt, sezioni 3 (D-L3-j) e 4 (P-12).
--
-- Elenco test (plan 14):
--    1) fn_apri_blocco: un attesso APERTO, quantita' firmata -5, per chi e perche'
--    2) fn_libera_blocco: CHIUSA, con data di chiusura e la nota di chi libera
--    3) liberare due volte -> E_MAG_BLOCCO_GIA_CHIUSO
--    4) liberare un blocco che non c'e' -> E_MAG_BLOCCO_NON_TROVATO
--    5) aprire senza l'azione blocca_merce -> E_PERMESSO_NEGATO
--    6) l'app non scrive movimenti_attesi: INSERT revocato
--    7) ...UPDATE revocato
--    8) ...e lo dice anche il comportamento: UPDATE ... WHERE false -> 42501
--    9) l'app esegue il verbo della bolla (vendite.fn_cambia_stato_ddt)
--   10) l'app esegue il verbo del trasferimento interno
--   11) l'app esegue i due verbi del blocco
--   12) l'app NON esegue il posting interno della bolla (vendite.fn_posta_ddt:
--       stava in magazzino fino al 2026-10-01, brief-db-magazzino-registro-anello-interno)
--   13) l'app NON esegue la utility di storno
--   14) i verbi del Lotto 3 sono SECURITY DEFINER, le operazioni interne pure
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _az), 'blocca_merce'); END $az$;

CREATE TEMP TABLE _fix (mag bigint, art uuid, blocco bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_b bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L3B-MAG', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L3B-ART', true, false, false);
    v_b   := magazzino.fn_apri_blocco(v_mag, v_art, 5, NULL, 'riservati alla fiera');
    INSERT INTO _fix VALUES (v_mag, v_art, v_b);
END $fix$;

-- 1) aperto
SELECT is(
    (SELECT (a.stato, trim_scale(a.qta), a.nota)::text FROM magazzino.movimenti_attesi a WHERE a.id = (SELECT blocco FROM _fix)),
    '(APERTA,-5,"riservati alla fiera")',
    '1) il blocco nasce APERTO, con la quantita'' firmata e il perche''');

-- 2) liberato
DO $l$ BEGIN PERFORM magazzino.fn_libera_blocco((SELECT blocco FROM _fix), 'fiera annullata'); END $l$;
SELECT ok(
    (SELECT a.stato = 'CHIUSA' AND a.data_chiusura IS NOT NULL AND a.meta ->> 'nota_liberazione' = 'fiera annullata'
       FROM magazzino.movimenti_attesi a WHERE a.id = (SELECT blocco FROM _fix)),
    '2) liberato: CHIUSA, con la data e la nota di chi libera (M-3: si libera con un atto)');

-- 3-4)
SELECT throws_like(
    format('SELECT magazzino.fn_libera_blocco(%s, %L)', (SELECT blocco FROM _fix), 'di nuovo'),
    '%già stato liberato%',
    '3) liberare due volte: E_MAG_BLOCCO_GIA_CHIUSO');
SELECT throws_like(
    'SELECT magazzino.fn_libera_blocco(999999999999, ''nessuno'')',
    '%non trovato%',
    '4) un blocco che non c''e'': E_MAG_BLOCCO_NON_TROVATO');

-- 5) un altro operatore, senza l'azione
CREATE TEMP TABLE _az2 AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az2)); END $ctx$;
SELECT throws_like(
    format('SELECT magazzino.fn_apri_blocco(%s, %L, 1, NULL, %L)', (SELECT mag FROM _fix), (SELECT art FROM _fix), 'senza permesso'),
    '%Non hai i permessi%',
    '5) aprire un blocco senza blocca_merce: E_PERMESSO_NEGATO (la prima riga del verbo)');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;

-- 6-8) movimenti_attesi in sola lettura per l'app
SELECT ok(NOT has_table_privilege('zeroerp_app', 'magazzino.movimenti_attesi', 'INSERT'),
    '6) l''app non ha INSERT su movimenti_attesi: apre il verbo');
SELECT ok(NOT has_table_privilege('zeroerp_app', 'magazzino.movimenti_attesi', 'UPDATE'),
    '7) l''app non ha UPDATE su movimenti_attesi: libera il verbo');
SELECT throws_ok(
    'UPDATE magazzino.movimenti_attesi SET id = id WHERE false',
    '42501', NULL,
    '8) come app, UPDATE ... WHERE false risponde 42501 (il permesso prima delle righe)');

-- 9-13) chi esegue che cosa. Per nome, tutti gli overload: la firma la dice il catalogo.
SELECT ok(
    (SELECT bool_and(has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')) AND count(*) = 1
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_cambia_stato_ddt'),
    '9) l''app esegue vendite.fn_cambia_stato_ddt');
SELECT ok(
    (SELECT bool_and(has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')) AND count(*) = 1
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino' AND p.proname = 'fn_posta_trasferimento'),
    '10) l''app esegue magazzino.fn_posta_trasferimento');
SELECT ok(
    (SELECT bool_and(has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')) AND count(*) = 2
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino' AND p.proname IN ('fn_apri_blocco', 'fn_libera_blocco')),
    '11) l''app esegue i due verbi del blocco');
SELECT ok(
    (SELECT NOT bool_or(has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')) AND count(*) = 1
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_posta_ddt'),
    '12) l''app NON esegue vendite.fn_posta_ddt: ci arriva solo dal verbo della bolla');
SELECT ok(
    (SELECT NOT bool_or(has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')) AND count(*) = 1
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino' AND p.proname = 'fn_storna_movimenti_sorgente'),
    '13) l''app NON esegue la utility di storno');

-- 14) DEFINER: i verbi scrivono dove l'app non scrive, le operazioni interne sono loro figlie
SELECT is(
    (SELECT string_agg(n.nspname || '.' || p.proname || '=' || p.prosecdef::text, ',' ORDER BY n.nspname, p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE (n.nspname, p.proname) IN (('vendite', 'fn_cambia_stato_ddt'), ('vendite', 'fn_posta_ddt'),
                                       ('magazzino', 'fn_posta_trasferimento'), ('magazzino', 'fn_storna_movimenti_sorgente'),
                                       ('magazzino', 'fn_apri_blocco'), ('magazzino', 'fn_libera_blocco'))),
    'magazzino.fn_apri_blocco=true,magazzino.fn_libera_blocco=true,'
    'magazzino.fn_posta_trasferimento=true,magazzino.fn_storna_movimenti_sorgente=true,'
    'vendite.fn_cambia_stato_ddt=true,vendite.fn_posta_ddt=true',
    '14) verbi e operazioni interne del Lotto 3: tutti SECURITY DEFINER');

SELECT * FROM finish();
ROLLBACK;
