-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'eliminazione di una versione di listino
--   Il BB delle tabelle che trattengono (20261028-34), la fn_check
--   dell'eliminazione (-36), il ramo DELETE del guard per stato (-37), il
--   DELETE dei componenti in BOZZA (-38), il verbo (-39), la superficie della
--   lista (-40) e la riga ELIMINA_VERSIONE_LISTINO del registro
--   config.azioni_riga (80_data).
--   Brief: brief-modello-documento-vendita §16.11 (opzione a, E-1, E-2, E-3
--   di Tid, 2026-10-28).
--
-- ⭐ TUTTO COSTRUITO: mondo, listino, articoli e contratto dai builder
--   dbops.fn_pgtap_crea_*, versioni, distinta e componenti scritti qui (la
--   forma di vendite/test-fn-resolve-prezzo-listino-v2-bundle-prioritario-v1).
--   Vale anche su un DB ricostruito da zero.
--
-- LE VERSIONI COSTRUITE (oggi = data operativa):
--   V0  2020                 ATTIVA dalla fixture, finita nel 2020
--   VA  oggi     .. oggi+400 BOZZA con il bundle P (F1, F2) e la riga F2,
--                            poi ATTIVA
--   VB  oggi+500 .. oggi+600 BOZZA con il bundle P e la riga F2: si elimina
--   VC  oggi+700 .. oggi+800 BOZZA con la riga F2, citata da un contratto DRAFT
--
-- Elenco test (plan 15):
--   1) il registro: ELIMINA_VERSIONE_LISTINO nomina vista, colonne, check e verbo
--   2) la superficie: «Elimina» acceso su VB (BOZZA)
--   3) la superficie: «Elimina» spento su VA (ATTIVA), col motivo
--   4) ⛔ il verbo su VA: E_LISTINO_VERSIONE_NON_ELIMINABILE
--   5) ⛔ DELETE diretto di un componente di VA: E_RIGA_LISTINO_VERSIONE_CHIUSA
--   6) ...e VA non ha perso niente (1 riga, 2 componenti)
--   7) E-1: un componente di una BOZZA (VB) si cancella
--   8) E-3: la check su VC citata dal contratto: VERSIONE_CITATA, dove vendite.contratti
--   9) la superficie: «Elimina» spento su VC, col motivo
--  10) ⛔ il verbo su VC: E_LISTINO_VERSIONE_CITATA
--  11) ⛔ DELETE diretto di VC: E_LISTINO_VERSIONE_CITATA (guard per stato)
--  12) ...e VC non ha perso niente (versione, 1 riga)
--  13) il verbo su VB: 1 riga e 1 componente cancellati (l'altro l'ha tolto il 7)
--  14) ...e di VB non resta niente
--  15) ⛔ il verbo su VB che non c'e' piu': E_VENDITE_LISTINO_VERSIONE_NOT_FOUND
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo): il builder del mondo lo riapre poi sul
-- suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('elimina versione listino');

CREATE TEMP TABLE t_oggi AS SELECT script.fn_data_operativa() AS d;

-- La versione del builder nasce ATTIVA: la si fa finire nel 2020.
CREATE TEMP TABLE t_lst AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM t_mondo), 'elimina versione listino',
    '2020-01-01'::date, '2020-12-31'::date);

-- Le tre versioni, BOZZA alla nascita.
CREATE TEMP TABLE t_ver AS
WITH v(sigla, dal, al) AS (
    SELECT 'VA', d, d + 400 FROM t_oggi
    UNION ALL SELECT 'VB', d + 500, d + 600 FROM t_oggi
    UNION ALL SELECT 'VC', d + 700, d + 800 FROM t_oggi),
ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al)
    SELECT (SELECT listino_id FROM t_lst), 'PGTAP_ELV_' || v.sigla, v.dal, v.al FROM v
    RETURNING id, codice_versione)
SELECT substr(ins.codice_versione, 11) AS sigla, ins.id FROM ins;

-- Scopo: id di una versione della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.ver(p_sigla text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT id FROM t_ver WHERE sigla = p_sigla;
$fx$;

-- Il bundle: P composito, con F1 e F2 in distinta (tipologia del listino).
CREATE TEMP TABLE t_art AS
SELECT v.sigla,
       dbops.fn_pgtap_crea_articolo('PGTAP-ELV-' || v.sigla || '-' || substr(md5(random()::text), 1, 8), false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_lst),
           p_is_composito         => v.composito) AS id
  FROM (VALUES ('P', true), ('F1', false), ('F2', false)) AS v(sigla, composito);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM t_art WHERE sigla = p_sigla;
$fx$;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
SELECT pg_temp.art('P'), pg_temp.art(f.sigla), 1, '2020-01-01'
  FROM (VALUES ('F1'), ('F2')) AS f(sigla);

-- I componenti del bundle su VA e VB, nella validita' della versione.
INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal, valido_al)
SELECT lv.id, ac.id, ac.prodotto_id, ac.componente_id, 75.00, lv.valido_dal, lv.valido_al
  FROM catalogo.articoli_componenti ac
 CROSS JOIN vendite.listini_versioni lv
 WHERE ac.prodotto_id = pg_temp.art('P')
   AND lv.id IN (pg_temp.ver('VA'), pg_temp.ver('VB'));

-- La riga F2 su tutte e tre.
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT t.id, pg_temp.art('F2'), a.uom_id, 100.00
  FROM t_ver t
 CROSS JOIN catalogo.articoli a
 WHERE a.id = pg_temp.art('F2');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', pg_temp.ver('VA'), 'ATTIVA');

-- Un contratto DRAFT che fissa VC.
CREATE TEMP TABLE t_ctr AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
    'elimina versione listino', 'DRAFT',
    p_billing_account_id => (SELECT billing_account_id FROM t_mondo),
    p_listino_id         => (SELECT listino_id FROM t_lst));

UPDATE vendite.contratti SET listino_versione_id = pg_temp.ver('VC')
 WHERE id = (SELECT contratto_id FROM t_ctr);

-- Scopo: l'inizio del messaggio di un codice, fino al primo segnaposto, per
--   throws_like.
CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT split_part(m.messaggio, '%s', 1) || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it';
$fx$;

-- Scopo: righe e componenti di una versione, `versioni:righe:componenti`.
CREATE OR REPLACE FUNCTION pg_temp.conta(p_id bigint)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT (SELECT count(*) FROM vendite.listini_versioni lv WHERE lv.id = p_id) || ':' ||
         (SELECT count(*) FROM vendite.listini_righe r WHERE r.listino_versione_id = p_id) || ':' ||
         (SELECT count(*) FROM vendite.listini_righe_componenti c WHERE c.listino_versione_id = p_id);
$fx$;

-- ============================================================
-- 1-3) Il registro e la superficie
-- ============================================================
SELECT is(
    (SELECT concat_ws(' ', r.superficie, r.colonna_motivo, r.colonna_motivo_chiave, r.fn_check, r.verbo)
       FROM config.azioni_riga r WHERE r.codice_interno = 'ELIMINA_VERSIONE_LISTINO' AND r.attivo),
    'vendite.vw_listini_versioni_azioni eliminazione_blocco_reason eliminazione_blocco_reason_key '
    'script.fn_check_versione_listino_eliminabile vendite.fn_elimina_versione_listino',
    '1) il registro: ELIMINA_VERSIONE_LISTINO nomina vista, colonne, check e verbo');

SELECT is(
    (SELECT COALESCE(v.eliminazione_blocco_reason, 'ACCESO')
       FROM vendite.vw_listini_versioni_azioni v WHERE v.versione_id = pg_temp.ver('VB')),
    'ACCESO',
    '2) la superficie: «Elimina» acceso su VB (BOZZA)');

SELECT is(
    (SELECT v.eliminazione_blocco_reason || ':' || v.eliminazione_blocco_reason_key
       FROM vendite.vw_listini_versioni_azioni v WHERE v.versione_id = pg_temp.ver('VA')),
    'VERSIONE_NON_IN_BOZZA:vendite.listini.azione_reason.versione_non_in_bozza',
    '3) la superficie: «Elimina» spento su VA (ATTIVA), col motivo');

-- ============================================================
-- 4-7) Fuori dalla bozza no; in bozza i componenti si cancellano
-- ============================================================
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_elimina_versione_listino(%s)$$, pg_temp.ver('VA')),
    pg_temp.msg('E_LISTINO_VERSIONE_NON_ELIMINABILE'),
    '4) il verbo su VA (ATTIVA): E_LISTINO_VERSIONE_NON_ELIMINABILE');

SELECT throws_like(
    format($$DELETE FROM vendite.listini_righe_componenti WHERE id = %s$$,
           (SELECT min(c.id) FROM vendite.listini_righe_componenti c
             WHERE c.listino_versione_id = pg_temp.ver('VA'))),
    pg_temp.msg('E_RIGA_LISTINO_VERSIONE_CHIUSA'),
    '5) DELETE diretto di un componente di VA: E_RIGA_LISTINO_VERSIONE_CHIUSA');

SELECT is(pg_temp.conta(pg_temp.ver('VA')), '1:1:2',
    '6) ...e VA non ha perso niente: la versione, 1 riga, 2 componenti');

SELECT lives_ok(
    format($$DELETE FROM vendite.listini_righe_componenti WHERE id = %s$$,
           (SELECT min(c.id) FROM vendite.listini_righe_componenti c
             WHERE c.listino_versione_id = pg_temp.ver('VB'))),
    '7) E-1: un componente di una BOZZA (VB) si cancella');

-- ============================================================
-- 8-12) Una bozza citata da un documento
-- ============================================================
SELECT is(
    (SELECT (m -> 0 ->> 'reason') || ':' || (m -> 0 -> 'dettaglio' ->> 'dove')
       FROM (SELECT script.fn_check_versione_listino_eliminabile(pg_temp.ver('VC')) AS m) x),
    'VERSIONE_CITATA:["vendite.contratti"]',
    '8) E-3: VC fissata da un contratto: VERSIONE_CITATA, dove vendite.contratti');

SELECT is(
    (SELECT v.eliminazione_blocco_reason || ':' || v.eliminazione_blocco_reason_key
       FROM vendite.vw_listini_versioni_azioni v WHERE v.versione_id = pg_temp.ver('VC')),
    'VERSIONE_CITATA:vendite.listini.azione_reason.versione_citata',
    '9) la superficie: «Elimina» spento su VC, col motivo');

SELECT throws_like(
    format($$SELECT * FROM vendite.fn_elimina_versione_listino(%s)$$, pg_temp.ver('VC')),
    pg_temp.msg('E_LISTINO_VERSIONE_CITATA'),
    '10) il verbo su VC: E_LISTINO_VERSIONE_CITATA, non l''errore della FK');

SELECT throws_like(
    format($$DELETE FROM vendite.listini_versioni WHERE id = %s$$, pg_temp.ver('VC')),
    pg_temp.msg('E_LISTINO_VERSIONE_CITATA'),
    '11) DELETE diretto di VC: E_LISTINO_VERSIONE_CITATA dal guard per stato');

SELECT is(pg_temp.conta(pg_temp.ver('VC')), '1:1:0',
    '12) ...e VC non ha perso niente: la versione, 1 riga');

-- ============================================================
-- 13-15) L'eliminazione
-- ============================================================
SELECT is(
    (SELECT f.versione_id || ':' || f.righe_eliminate || ':' || f.componenti_eliminati
       FROM vendite.fn_elimina_versione_listino(pg_temp.ver('VB')) f),
    pg_temp.ver('VB') || ':1:1',
    '13) il verbo su VB: 1 riga e 1 componente cancellati');

SELECT is(pg_temp.conta(pg_temp.ver('VB')), '0:0:0',
    '14) ...e di VB non resta niente');

SELECT throws_like(
    format($$SELECT * FROM vendite.fn_elimina_versione_listino(%s)$$, pg_temp.ver('VB')),
    pg_temp.msg('E_VENDITE_LISTINO_VERSIONE_NOT_FOUND'),
    '15) il verbo su VB che non c''e'' piu'': E_VENDITE_LISTINO_VERSIONE_NOT_FOUND');

SELECT * FROM finish();
ROLLBACK;
