-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il BB che risolve la provenienza (script.fn_sorgente_documento e il ponte
--   script.fn_sorgente_documento_da_chiave) e il BB che la scrive
--   (script.fn_sorgente_chiave), con le due funzioni che ora li usano:
--   vendite.fn_get_sorgente_documento_ref e vendite.fn_link_commessa_sorgente.
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto 0. ChangeSet:
--   20261106-11, -12, -13, -14.
--
-- I casi si COSTRUISCONO: una bolla (tipo a chiave id, nata da un ordine) e un
--   preventivo (tipo a chiave uid), in bozza, dai builder del dominio.
--
-- Elenco test (plan 27):
--  il BB che risolve
--   1) bolla per id -> id, uid, numero
--   2) bolla per uid -> la stessa riga
--   3) preventivo per uid -> id, uid, numero
--   4) preventivo per id (la chiave dell'altra specie) -> la stessa riga
--   5) due chiavi che non indicano lo stesso documento -> tutta NULL
--   6) l'uid di una commessa (la tabella non ha uid) -> tutta NULL
--   7) un documento che non c'e' -> una riga, tutta NULL
--   8) senza tipo -> una riga, tutta NULL
--   9) ROWS 1 sulle tre funzioni nuove
--  il ponte per chiave testuale
--  10) la bolla per uid::text e per id::text
--  11) una chiave non canonica (zeri davanti) -> NULL
--  vendite.fn_get_sorgente_documento_ref, ora sul ponte
--  12) il preventivo per id ora si risolve (cambio dichiarato)
--  13) la bolla per uid: id e numero, come prima
--  il BB che scrive
--  14) bolla con l'uid -> (id, NULL)
--  15) bolla con l'id -> (id, NULL)
--  16) preventivo con l'id -> (NULL, uid)
--  17) preventivo con l'uid -> (NULL, uid)
--  18) chiave vuota -> E_SORG_KEY_MISSING
--  19) chiave che non e' ne' id ne' uuid -> E_SORG_FORMATO
--  20) uuid con le maiuscole -> E_SORG_FORMATO (non e' canonico)
--  21) uuid che non trova la bolla -> E_SORG_NORM_NON_RISOLTA
--  22) id che non trova la bolla -> E_SORG_NOT_FOUND
--  23) uuid che non trova il preventivo -> E_SORG_NOT_FOUND
--  24) uuid per una commessa (tabella senza uid) -> E_SORG_NORM_NON_RISOLTA
--  25) tipo assente o inesistente -> E_SORG_CONF
--  vendite.fn_link_commessa_sorgente, ora sul BB che scrive
--  26) l'uid dell'ordine si stocca come id::text
--  27) l'id del preventivo si stocca come uid::text (cambio dichiarato)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(27);

-- Il mondo: una bolla in bozza nata da un ordine, un preventivo in bozza, una
-- commessa sul cliente della bolla. Letti in istruzioni separate.
CREATE TEMP TABLE _d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('PGT-SDC-D', 'DRAFT');
CREATE TEMP TABLE _p AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('PGT-SDC-P', 'DRAFT');
CREATE TEMP TABLE _c AS
SELECT c.commessa_id
  FROM dbops.fn_pgtap_crea_commessa('PGT-SDC-C', NULL, (SELECT billing_account_id FROM _d)) c;

CREATE TEMP TABLE _t AS
SELECT (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA')    AS ddt,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')     AS prev,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA')       AS comm,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA') AS ord;

CREATE TEMP TABLE _num AS
SELECT (SELECT d.numero::text FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM _d))              AS ddt,
       (SELECT p.numero::text FROM vendite.preventivi p WHERE p.id = (SELECT preventivo_id FROM _p)) AS prev;

-- Il codice dell'errore sollevato (il canale CONSTRAINT dell'eccezione).
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text)
RETURNS text AS $fn$
DECLARE v_codice text;
BEGIN
  EXECUTE p_sql;
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_codice, ''), SQLSTATE);
END $fn$ LANGUAGE plpgsql;

-- ===== il BB che risolve =====
SELECT results_eq(
    $$SELECT r.documento_id, r.documento_uid, r.documento_numero
        FROM script.fn_sorgente_documento((SELECT ddt FROM _t), (SELECT ddt_id FROM _d), NULL) r$$,
    $$SELECT ddt_id, ddt_uid, (SELECT ddt FROM _num) FROM _d$$,
    '1) la bolla per id: id, uid e numero in una lettura');

SELECT results_eq(
    $$SELECT r.documento_id, r.documento_uid, r.documento_numero
        FROM script.fn_sorgente_documento((SELECT ddt FROM _t), NULL, (SELECT ddt_uid FROM _d)) r$$,
    $$SELECT ddt_id, ddt_uid, (SELECT ddt FROM _num) FROM _d$$,
    '2) la bolla per uid: la stessa riga');

SELECT results_eq(
    $$SELECT r.documento_id, r.documento_uid, r.documento_numero
        FROM script.fn_sorgente_documento((SELECT prev FROM _t), NULL, (SELECT preventivo_uid FROM _p)) r$$,
    $$SELECT preventivo_id, preventivo_uid, (SELECT prev FROM _num) FROM _p$$,
    '3) il preventivo per uid: id, uid e numero');

SELECT results_eq(
    $$SELECT r.documento_id, r.documento_uid, r.documento_numero
        FROM script.fn_sorgente_documento((SELECT prev FROM _t), (SELECT preventivo_id FROM _p), NULL) r$$,
    $$SELECT preventivo_id, preventivo_uid, (SELECT prev FROM _num) FROM _p$$,
    '4) il preventivo per id: legge la chiave che riceve, la stessa riga');

SELECT results_eq(
    $$SELECT r.documento_id, r.documento_uid, r.documento_numero
        FROM script.fn_sorgente_documento((SELECT ddt FROM _t), (SELECT ddt_id FROM _d), gen_random_uuid()) r$$,
    $$VALUES (NULL::bigint, NULL::uuid, NULL::text)$$,
    '5) id e uid che non indicano lo stesso documento: tutta NULL');

SELECT results_eq(
    $$SELECT r.documento_id, r.documento_uid, r.documento_numero
        FROM script.fn_sorgente_documento((SELECT comm FROM _t), NULL, gen_random_uuid()) r$$,
    $$VALUES (NULL::bigint, NULL::uuid, NULL::text)$$,
    '6) l''uid di una commessa: la tabella non ce l''ha, tutta NULL');

SELECT results_eq(
    $$SELECT r.documento_id, r.documento_uid, r.documento_numero
        FROM script.fn_sorgente_documento((SELECT ddt FROM _t), -1, NULL) r$$,
    $$VALUES (NULL::bigint, NULL::uuid, NULL::text)$$,
    '7) un documento che non c''e'': una riga, tutta NULL');

SELECT results_eq(
    $$SELECT r.documento_id, r.documento_uid, r.documento_numero
        FROM script.fn_sorgente_documento(NULL, (SELECT ddt_id FROM _d), NULL) r$$,
    $$VALUES (NULL::bigint, NULL::uuid, NULL::text)$$,
    '8) senza tipo: una riga, tutta NULL');

SELECT results_eq(
    $$SELECT p.proname::text COLLATE "default", p.prorows::int
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname = 'script'
         AND p.proname IN ('fn_sorgente_documento', 'fn_sorgente_documento_da_chiave', 'fn_sorgente_chiave')
       ORDER BY 1$$,
    $$VALUES ('fn_sorgente_chiave', 1), ('fn_sorgente_documento', 1), ('fn_sorgente_documento_da_chiave', 1)$$,
    '9) le tre funzioni nuove dichiarano ROWS 1');

-- ===== il ponte =====
SELECT results_eq(
    $$SELECT (SELECT r.documento_id FROM script.fn_sorgente_documento_da_chiave(
                  (SELECT ddt FROM _t), (SELECT ddt_uid::text FROM _d)) r),
             (SELECT r.documento_id FROM script.fn_sorgente_documento_da_chiave(
                  (SELECT ddt FROM _t), (SELECT ddt_id::text FROM _d)) r)$$,
    $$SELECT ddt_id, ddt_id FROM _d$$,
    '10) il ponte: la bolla per uid::text e per id::text');

SELECT is(
    (SELECT r.documento_id FROM script.fn_sorgente_documento_da_chiave(
         (SELECT ddt FROM _t), '0' || (SELECT ddt_id::text FROM _d)) r),
    NULL::bigint,
    '11) il ponte: una chiave non canonica (zeri davanti) non si risolve');

-- ===== fn_get_sorgente_documento_ref sul ponte =====
SELECT is(
    (SELECT r.documento_id FROM vendite.fn_get_sorgente_documento_ref(
         (SELECT prev FROM _t), (SELECT preventivo_id::text FROM _p)) r),
    (SELECT preventivo_id FROM _p),
    '12) fn_get_sorgente_documento_ref: il preventivo per id ora si risolve');

SELECT results_eq(
    $$SELECT r.documento_id, r.documento_numero
        FROM vendite.fn_get_sorgente_documento_ref((SELECT ddt FROM _t), (SELECT ddt_uid::text FROM _d)) r$$,
    $$SELECT ddt_id, (SELECT ddt FROM _num) FROM _d$$,
    '13) fn_get_sorgente_documento_ref: la bolla per uid, id e numero come prima');

-- ===== il BB che scrive =====
SELECT results_eq(
    $$SELECT k.sorgente_id, k.sorgente_uid
        FROM script.fn_sorgente_chiave((SELECT ddt FROM _t), (SELECT ddt_uid::text FROM _d)) k$$,
    $$SELECT ddt_id, NULL::uuid FROM _d$$,
    '14) la bolla con l''uid: si scrive (id, NULL)');

SELECT results_eq(
    $$SELECT k.sorgente_id, k.sorgente_uid
        FROM script.fn_sorgente_chiave((SELECT ddt FROM _t), (SELECT ddt_id::text FROM _d)) k$$,
    $$SELECT ddt_id, NULL::uuid FROM _d$$,
    '15) la bolla con l''id: (id, NULL)');

SELECT results_eq(
    $$SELECT k.sorgente_id, k.sorgente_uid
        FROM script.fn_sorgente_chiave((SELECT prev FROM _t), (SELECT preventivo_id::text FROM _p)) k$$,
    $$SELECT NULL::bigint, preventivo_uid FROM _p$$,
    '16) il preventivo con l''id: si scrive (NULL, uid)');

SELECT results_eq(
    $$SELECT k.sorgente_id, k.sorgente_uid
        FROM script.fn_sorgente_chiave((SELECT prev FROM _t), (SELECT preventivo_uid::text FROM _p)) k$$,
    $$SELECT NULL::bigint, preventivo_uid FROM _p$$,
    '17) il preventivo con l''uid: (NULL, uid)');

SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM script.fn_sorgente_chiave(%s, '   ')$$, (SELECT ddt FROM _t))),
    'E_SORG_KEY_MISSING',
    '18) chiave vuota -> E_SORG_KEY_MISSING');

SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM script.fn_sorgente_chiave(%s, 'DDT-42')$$, (SELECT ddt FROM _t))),
    'E_SORG_FORMATO',
    '19) chiave che non e'' ne'' un id ne'' un uuid -> E_SORG_FORMATO');

SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM script.fn_sorgente_chiave(%s, %L)$$,
        (SELECT ddt FROM _t), (SELECT upper(ddt_uid::text) FROM _d))),
    'E_SORG_FORMATO',
    '20) uuid con le maiuscole -> E_SORG_FORMATO (non e'' in forma canonica)');

SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM script.fn_sorgente_chiave(%s, %L)$$, (SELECT ddt FROM _t), gen_random_uuid()::text)),
    'E_SORG_NORM_NON_RISOLTA',
    '21) uuid che non trova la bolla -> E_SORG_NORM_NON_RISOLTA');

SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM script.fn_sorgente_chiave(%s, '999999999999')$$, (SELECT ddt FROM _t))),
    'E_SORG_NOT_FOUND',
    '22) id che non trova la bolla -> E_SORG_NOT_FOUND');

SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM script.fn_sorgente_chiave(%s, %L)$$, (SELECT prev FROM _t), gen_random_uuid()::text)),
    'E_SORG_NOT_FOUND',
    '23) uuid che non trova il preventivo -> E_SORG_NOT_FOUND');

SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM script.fn_sorgente_chiave(%s, %L)$$, (SELECT comm FROM _t), gen_random_uuid()::text)),
    'E_SORG_NORM_NON_RISOLTA',
    '24) uuid per una commessa (tabella senza uid) -> E_SORG_NORM_NON_RISOLTA');

SELECT results_eq(
    $$SELECT pg_temp.codice_errore($q$SELECT * FROM script.fn_sorgente_chiave(NULL, '1')$q$),
             pg_temp.codice_errore($q$SELECT * FROM script.fn_sorgente_chiave(-1, '1')$q$)$$,
    $$VALUES ('E_SORG_CONF', 'E_SORG_CONF')$$,
    '25) tipo assente o inesistente -> E_SORG_CONF');

-- ===== fn_link_commessa_sorgente sul BB che scrive =====
-- Due passi: la riga che la porta scrive si legge in un'istruzione separata.
CREATE TEMP TABLE _l26 AS
SELECT vendite.fn_link_commessa_sorgente(
           (SELECT commessa_id FROM _c), (SELECT ord FROM _t), (SELECT ordine_uid::text FROM _d)) AS link_id;

SELECT is(
    (SELECT cs.sorgente_id FROM vendite.commesse_sorgenti cs WHERE cs.id = (SELECT link_id FROM _l26)),
    (SELECT ordine_id FROM _d),
    '26) fn_link: l''uid dell''ordine si stocca come id, in sorgente_id');

CREATE TEMP TABLE _l27 AS
SELECT vendite.fn_link_commessa_sorgente(
           (SELECT commessa_id FROM _c), (SELECT prev FROM _t), (SELECT preventivo_id::text FROM _p)) AS link_id;

SELECT is(
    (SELECT cs.sorgente_uid FROM vendite.commesse_sorgenti cs WHERE cs.id = (SELECT link_id FROM _l27)),
    (SELECT preventivo_uid FROM _p),
    '27) fn_link: l''id del preventivo si stocca come uid, in sorgente_uid');

SELECT * FROM finish();
ROLLBACK;
