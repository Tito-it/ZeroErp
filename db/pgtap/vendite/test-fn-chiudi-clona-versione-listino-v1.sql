-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: «Chiudi» e «Clona» di una versione di listino
--   La fn_check della chiusura (20261029-01), il verbo «Chiudi» (-02), la
--   fn_check della clonazione (-03), il verbo «Clona» (-04), la superficie
--   della lista (-05), la riga CHIUDI_VERSIONE_LISTINO del registro
--   config.azioni_riga (80_data) e la porta della fine di una ATTIVA (-07 …
--   -09: «Chiudi» la apre, l'UPDATE diretto no).
--   Brief: brief-modello-documento-vendita §16.14 (C-1 = a, C-2 = a, C-3 di
--   Tid, 2026-10-29) e §16.15 (C-4 = a, 2026-10-29).
--
-- ⭐ TUTTO COSTRUITO: mondo, listino e articoli dai builder
--   dbops.fn_pgtap_crea_*, versioni, distinta, righe e componenti scritti qui
--   (la forma di vendite/test-fn-elimina-versione-listino-v1). Vale anche su
--   un DB ricostruito da zero.
--
-- LE VERSIONI COSTRUITE (oggi = data operativa):
--   V0  2020                 ATTIVA dalla fixture, finita nel 2020
--   VA  oggi-10 ..           BOZZA con il bundle P (F1 aperto, F2 che la
--                            distinta chiude a oggi+100), la riga F2 accesa
--                            e la riga F1 spenta; poi ATTIVA
--   VB  oggi+500 .. oggi+600 BOZZA con la riga F2
--
-- Elenco test (plan 17):
--   1) il registro: CHIUDI_VERSIONE_LISTINO nomina vista, colonne, check e verbo
--   2) la superficie: «Chiudi» acceso su VA (ATTIVA)
--   3) la superficie: «Chiudi» spento su VB (BOZZA), col motivo
--   4) la check su VA a ieri: FINE_NEL_PASSATO
--   5) ⛔ il verbo su VA a ieri: E_LISTINO_VERSIONE_FINE_NEL_PASSATO
--   6) ⛔ il verbo su VB: E_LISTINO_VERSIONE_NON_CHIUDIBILE
--   7) il verbo su VA a oggi+30: la fine di prima (nessuna) e quella nuova
--   8) ...VA finisce a oggi+30 ed e' ancora ATTIVA (CHIUSA la scrive il job)
--   9) il verbo su VA senza data: la chiusura si toglie
--  10) il verbo su VA a oggi: oggi e' ammesso
--  11) ⛔ «Clona» VA da prima della sua decorrenza: E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE
--  12) «Clona» VA da oggi+200: 1 riga (la spenta no), 1 componente, 1 saltato (F2 finito)
--  13) ...la copia: BOZZA, stesso listino, le date chieste, il componente da oggi+200
--  14) ...VA non ha perso niente (2 righe, 2 componenti)
--  15) C-1 = a: «Clona» da una BOZZA (VB): 1 riga
--  16) ⛔ «Clona» di una versione che non c'e': E_VENDITE_LISTINO_VERSIONE_NOT_FOUND
--  17) ⛔ C-4: la fine di VA (ATTIVA) con un UPDATE diretto: E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo): il builder del mondo lo riapre poi sul
-- suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('chiudi clona versione listino');

CREATE TEMP TABLE t_oggi AS SELECT script.fn_data_operativa() AS d;

-- Scopo: la data operativa spostata di p_giorni.
CREATE OR REPLACE FUNCTION pg_temp.oggi(p_giorni integer DEFAULT 0)
RETURNS date LANGUAGE sql STABLE AS $fx$
  SELECT d + p_giorni FROM t_oggi;
$fx$;

-- La versione del builder nasce ATTIVA: la si fa finire nel 2020.
CREATE TEMP TABLE t_lst AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM t_mondo), 'chiudi clona versione listino',
    '2020-01-01'::date, '2020-12-31'::date);

-- Le due versioni, BOZZA alla nascita.
CREATE TEMP TABLE t_ver AS
WITH v(sigla, dal, al) AS (
    SELECT 'VA', pg_temp.oggi(-10), NULL::date
    UNION ALL SELECT 'VB', pg_temp.oggi(500), pg_temp.oggi(600)),
ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al)
    SELECT (SELECT listino_id FROM t_lst), 'PGTAP_CCV_' || v.sigla, v.dal, v.al FROM v
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
       dbops.fn_pgtap_crea_articolo('PGTAP-CCV-' || v.sigla || '-' || substr(md5(random()::text), 1, 8), false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_lst),
           p_is_composito         => v.composito) AS id
  FROM (VALUES ('P', true), ('F1', false), ('F2', false)) AS v(sigla, composito);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM t_art WHERE sigla = p_sigla;
$fx$;

-- F1 in distinta senza fine, F2 fino a oggi+100.
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal, valido_al)
VALUES (pg_temp.art('P'), pg_temp.art('F1'), 1, '2020-01-01', NULL),
       (pg_temp.art('P'), pg_temp.art('F2'), 1, '2020-01-01', pg_temp.oggi(100));

-- I componenti del bundle su VA, nel periodo comune a distinta e versione.
INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal, valido_al)
SELECT pg_temp.ver('VA'), ac.id, ac.prodotto_id, ac.componente_id, 75.00,
       pg_temp.oggi(-10), ac.valido_al
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('P');

-- La riga F2 su tutte e due; la riga F1 su VA, spenta.
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT t.id, pg_temp.art('F2'), a.uom_id, 100.00
  FROM t_ver t
 CROSS JOIN catalogo.articoli a
 WHERE a.id = pg_temp.art('F2');

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo, attivo)
SELECT pg_temp.ver('VA'), a.id, a.uom_id, 50.00, false
  FROM catalogo.articoli a
 WHERE a.id = pg_temp.art('F1');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', pg_temp.ver('VA'), 'ATTIVA');

-- Scopo: il messaggio di un codice come pattern LIKE (ogni segnaposto = %),
--   per throws_like: due messaggi che cominciano uguale non si confondono.
CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT replace(m.messaggio, '%s', '%') || '%' FROM config.messaggi_errore m
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
       FROM config.azioni_riga r WHERE r.codice_interno = 'CHIUDI_VERSIONE_LISTINO' AND r.attivo),
    'vendite.vw_listini_versioni_azioni chiusura_blocco_reason chiusura_blocco_reason_key '
    'script.fn_check_versione_listino_chiudibile vendite.fn_programma_chiusura_versione_listino',
    '1) il registro: CHIUDI_VERSIONE_LISTINO nomina vista, colonne, check e verbo');

SELECT is(
    (SELECT COALESCE(v.chiusura_blocco_reason, 'ACCESO')
       FROM vendite.vw_listini_versioni_azioni v WHERE v.versione_id = pg_temp.ver('VA')),
    'ACCESO',
    '2) la superficie: «Chiudi» acceso su VA (ATTIVA)');

SELECT is(
    (SELECT v.chiusura_blocco_reason || ':' || v.chiusura_blocco_reason_key
       FROM vendite.vw_listini_versioni_azioni v WHERE v.versione_id = pg_temp.ver('VB')),
    'VERSIONE_NON_ATTIVA:vendite.listini.azione_reason.versione_non_attiva',
    '3) la superficie: «Chiudi» spento su VB (BOZZA), col motivo');

-- ============================================================
-- 4-10) «Chiudi»
-- ============================================================
SELECT is(
    script.fn_check_versione_listino_chiudibile(pg_temp.ver('VA'), pg_temp.oggi(-1)) -> 0 ->> 'reason',
    'FINE_NEL_PASSATO',
    '4) la check su VA a ieri: FINE_NEL_PASSATO');

SELECT throws_like(
    format($$SELECT * FROM vendite.fn_programma_chiusura_versione_listino(%s, %L)$$,
           pg_temp.ver('VA'), pg_temp.oggi(-1)),
    pg_temp.msg('E_LISTINO_VERSIONE_FINE_NEL_PASSATO'),
    '5) il verbo su VA a ieri: E_LISTINO_VERSIONE_FINE_NEL_PASSATO');

SELECT throws_like(
    format($$SELECT * FROM vendite.fn_programma_chiusura_versione_listino(%s, %L)$$,
           pg_temp.ver('VB'), pg_temp.oggi(550)),
    pg_temp.msg('E_LISTINO_VERSIONE_NON_CHIUDIBILE'),
    '6) il verbo su VB (BOZZA): E_LISTINO_VERSIONE_NON_CHIUDIBILE');

SELECT is(
    (SELECT f.versione_id || ':' || COALESCE(f.valido_al_prima::text, '-') || ':' || f.valido_al_dopo
       FROM vendite.fn_programma_chiusura_versione_listino(pg_temp.ver('VA'), pg_temp.oggi(30)) f),
    pg_temp.ver('VA') || ':-:' || pg_temp.oggi(30),
    '7) il verbo su VA a oggi+30: nessuna fine prima, oggi+30 dopo');

SELECT is(
    (SELECT lv.valido_al || ':' || s.codice_interno
       FROM vendite.listini_versioni lv
       JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
      WHERE lv.id = pg_temp.ver('VA')),
    pg_temp.oggi(30) || ':ATTIVA',
    '8) ...VA finisce a oggi+30 ed e'' ancora ATTIVA');

-- ⛔ Il verbo in un'istruzione sua: una JOIN nella stessa SELECT vedrebbe la
--   versione com'era prima del verbo.
CREATE TEMP TABLE t_riapre AS
SELECT * FROM vendite.fn_programma_chiusura_versione_listino(pg_temp.ver('VA'), NULL);

SELECT is(
    (SELECT r.valido_al_prima || ':' || COALESCE(lv.valido_al::text, 'APERTA')
       FROM t_riapre r
       JOIN vendite.listini_versioni lv ON lv.id = r.versione_id),
    pg_temp.oggi(30) || ':APERTA',
    '9) il verbo su VA senza data: la chiusura a oggi+30 si toglie');

SELECT lives_ok(
    format($$SELECT * FROM vendite.fn_programma_chiusura_versione_listino(%s, %L)$$,
           pg_temp.ver('VA'), pg_temp.oggi(0)),
    '10) il verbo su VA a oggi: oggi e'' ammesso');

-- ============================================================
-- 11-16) «Clona»
-- ============================================================
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_clona_versione_listino(%s, 'PGTAP_CCV_X0', %L)$$,
           pg_temp.ver('VA'), pg_temp.oggi(-20)),
    pg_temp.msg('E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE'),
    '11) «Clona» VA da prima della sua decorrenza: E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE');

CREATE TEMP TABLE t_clone AS
SELECT * FROM vendite.fn_clona_versione_listino(pg_temp.ver('VA'), 'PGTAP_CCV_C1', pg_temp.oggi(200));

SELECT is(
    (SELECT c.righe_copiate || ':' || c.componenti_copiati || ':' || c.componenti_saltati FROM t_clone c),
    '1:1:1',
    '12) «Clona» VA da oggi+200: 1 riga (la spenta no), 1 componente (F1), 1 saltato (F2 finito a oggi+100)');

SELECT is(
    (SELECT concat_ws(' ', s.codice_interno, lv.listino_id = (SELECT listino_id FROM t_lst),
                      lv.valido_dal, COALESCE(lv.valido_al::text, 'APERTA'),
                      (SELECT string_agg((rc.articolo_figlio_id = pg_temp.art('F1'))::text || '@' || rc.valido_dal
                                         || '..' || COALESCE(rc.valido_al::text, ''), ',')
                         FROM vendite.listini_righe_componenti rc WHERE rc.listino_versione_id = lv.id))
       FROM t_clone c
       JOIN vendite.listini_versioni lv ON lv.id = c.versione_id
       JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id),
    concat_ws(' ', 'BOZZA', true, pg_temp.oggi(200), 'APERTA', 'true@' || pg_temp.oggi(200) || '..'),
    '13) ...la copia: BOZZA, stesso listino, le date chieste, il componente F1 da oggi+200');

SELECT is(pg_temp.conta(pg_temp.ver('VA')), '1:2:2',
    '14) ...VA non ha perso niente: la versione, 2 righe, 2 componenti');

SELECT is(
    (SELECT f.righe_copiate || ':' || f.componenti_copiati || ':' || f.componenti_saltati
       FROM vendite.fn_clona_versione_listino(pg_temp.ver('VB'), 'PGTAP_CCV_C2', pg_temp.oggi(500)) f),
    '1:0:0',
    '15) C-1 = a: «Clona» da una BOZZA (VB): 1 riga');

SELECT throws_like(
    format($$SELECT * FROM vendite.fn_clona_versione_listino(%s, 'PGTAP_CCV_X1', %L)$$,
           (SELECT max(id) + 1000 FROM vendite.listini_versioni), pg_temp.oggi(0)),
    pg_temp.msg('E_VENDITE_LISTINO_VERSIONE_NOT_FOUND'),
    '16) «Clona» di una versione che non c''e'': E_VENDITE_LISTINO_VERSIONE_NOT_FOUND');

-- ============================================================
-- 17) La porta della fine
-- ============================================================
SELECT throws_like(
    format($$UPDATE vendite.listini_versioni SET valido_al = %L WHERE id = %s$$,
           pg_temp.oggi(50), pg_temp.ver('VA')),
    pg_temp.msg('E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO'),
    '17) C-4: la fine di VA (ATTIVA) con un UPDATE diretto: E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO');

SELECT * FROM finish();
ROLLBACK;
