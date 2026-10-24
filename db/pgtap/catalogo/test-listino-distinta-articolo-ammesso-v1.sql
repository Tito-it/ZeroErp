-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Quali articoli ammettono una riga di versione di listino e un legame di
-- distinta: la stessa check per tipo di riga dei documenti, un guard per
-- tabella, e i guard per regola ritirati.
-- Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-2, D-3, D-4; §9.3.4)
-- ChangeSet: 20261013-59 -> -61
--
-- ⭐ TUTTO COSTRUITO: cliente, listino, articoli; nessuna riga letta dai dati
--   (salvo il vocabolario: aliquote IVA e tipologie di listino).
--
-- Elenco test (plan 20):
--  Versione di listino: la check (script.fn_check_articolo_riga, LISTINO_VERSIONE)
--   1) articolo della tipologia del listino: ammesso
--   2) solo componente (D-3): SOLO_COMPONENTE
--   3) composito: COMPOSITO_COME_BUNDLE (nella versione entra coi componenti)
--   4) senza tipologia: TIPOLOGIA_MANCANTE
--   5) tipologia diversa: TIPOLOGIA_INCOMPATIBILE
--  Versione di listino: il guard su vendite.listini_righe
--   6) solo componente rifiutato
--   7) composito rifiutato
--   8) senza tipologia rifiutato
--   9) articolo della tipologia: ammesso
--  Distinta: la check (ARTICOLO, padre)
--  10) componente semplice con l'IVA del padre: ammesso
--  11) il padre stesso: COMPONENTE_PADRE
--  12) un composito: COMPONENTE_COMPOSITO (D-4)
--  13) IVA diversa: IVA_DISCORDANTE
--  14) senza padre: E_PARAMETRO_INVALIDO
--  Distinta: il guard su catalogo.articoli_componenti
--  15) componente composito rifiutato
--  16) IVA diversa rifiutata
--  17) il padre come componente di se stesso: rifiutato col codice, prima del CHECK
--  18) componente semplice: ammesso
--  19) un legame spento non si giudica
--  Il ritiro
--  20) i quattro guard per regola non ci sono piu'
-- ------------------------------------------------------------

BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('listino distinta articolo ammesso');

CREATE TEMP TABLE _listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _mondo), 'listino distinta articolo ammesso');

CREATE TEMP TABLE _iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1)          AS uno,
       (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id OFFSET 1 LIMIT 1) AS due;

-- Listino: A (tipologia del listino), S (solo componente), K (composito),
-- N (senza tipologia), D (un'altra tipologia).
-- Distinta: P padre composito; C1 semplice con l'IVA del padre; C2 composito;
-- C3 con un'altra IVA. La struttura nasce col builder (A-10); N resta senza
-- tipologia, D prende la prima diversa da quella del listino.
CREATE TEMP TABLE _art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGT-LDA-' || v.sigla, false,
           p_listino_tipologia_id => CASE
               WHEN v.sigla IN ('A', 'S', 'K') THEN (SELECT tipologia_id FROM _listino)
               WHEN v.sigla = 'D' THEN (SELECT lt.id FROM config.listini_tipologie lt
                                         WHERE lt.id <> (SELECT tipologia_id FROM _listino)
                                         ORDER BY lt.id LIMIT 1)
           END,
           p_is_composito       => v.sigla IN ('K', 'P', 'C2'),
           p_is_solo_componente => v.sigla = 'S') AS id
  FROM (VALUES ('A'), ('S'), ('K'), ('N'), ('D'), ('P'), ('C1'), ('C2'), ('C3')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM _art WHERE sigla = p_sigla;
$fx$;

UPDATE catalogo.articoli SET iva_id = (SELECT uno FROM _iva)
 WHERE id IN (pg_temp.art('P'), pg_temp.art('C1'), pg_temp.art('C2'));
UPDATE catalogo.articoli SET iva_id = (SELECT due FROM _iva) WHERE id = pg_temp.art('C3');

-- Scopo: il primo motivo (reason) della check per la versione, o 'AMMESSO'.
CREATE OR REPLACE FUNCTION pg_temp.listino(p_sigla text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT COALESCE(script.fn_check_articolo_riga(
           'LISTINO_VERSIONE', (SELECT listino_versione_id FROM _listino), pg_temp.art(p_sigla))
           -> 0 ->> 'reason', 'AMMESSO');
$fx$;

-- Scopo: il primo motivo della check per la distinta di P, o 'AMMESSO'.
CREATE OR REPLACE FUNCTION pg_temp.distinta(p_sigla text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT COALESCE(script.fn_check_articolo_riga(
           'ARTICOLO', NULL, pg_temp.art(p_sigla), NULL, NULL, pg_temp.art('P'))
           -> 0 ->> 'reason', 'AMMESSO');
$fx$;

-- Scopo: l'INSERT di una riga di listino, come testo.
CREATE OR REPLACE FUNCTION pg_temp.riga_listino(p_sigla text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT format($$INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
                  SELECT %s, a.id, a.uom_id, 10 FROM catalogo.articoli a WHERE a.id = %L$$,
                (SELECT listino_versione_id FROM _listino), pg_temp.art(p_sigla));
$fx$;

-- Scopo: l'INSERT di un legame di distinta sotto P, come testo.
CREATE OR REPLACE FUNCTION pg_temp.legame(p_sigla text, p_attivo boolean DEFAULT true)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT format($$INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal, attivo)
                  VALUES (%L, %L, 1, '2020-01-01', %L)$$,
                pg_temp.art('P'), pg_temp.art(p_sigla), p_attivo);
$fx$;

-- ============================================================
-- Versione di listino: la check (1-5)
-- ============================================================
SELECT is(pg_temp.listino('A'), 'AMMESSO', '1) listino: articolo della tipologia del listino, ammesso');
SELECT is(pg_temp.listino('S'), 'SOLO_COMPONENTE', '2) listino: solo componente (D-3)');
SELECT is(pg_temp.listino('K'), 'COMPOSITO_COME_BUNDLE', '3) listino: composito, entra come bundle');
SELECT is(pg_temp.listino('N'), 'TIPOLOGIA_MANCANTE', '4) listino: articolo senza tipologia');
SELECT is(pg_temp.listino('D'), 'TIPOLOGIA_INCOMPATIBILE', '5) listino: tipologia diversa');

-- ============================================================
-- Versione di listino: il guard (6-9)
-- ============================================================
SELECT throws_like(pg_temp.riga_listino('S'), '%solo come componente%',
    '6) listini_righe: solo componente rifiutato');
SELECT throws_like(pg_temp.riga_listino('K'), '%prezzo diretto%',
    '7) listini_righe: composito rifiutato (E_LISTINO_RIGA_COMPOSITO_VIETATO)');
SELECT throws_like(pg_temp.riga_listino('N'), '%privo di listino_tipologia_id%',
    '8) listini_righe: articolo senza tipologia rifiutato');
SELECT lives_ok(pg_temp.riga_listino('A'), '9) listini_righe: articolo della tipologia ammesso');

-- ============================================================
-- Distinta: la check (10-14)
-- ============================================================
SELECT is(pg_temp.distinta('C1'), 'AMMESSO', '10) distinta: componente semplice con l''IVA del padre, ammesso');
SELECT is(pg_temp.distinta('P'), 'COMPONENTE_PADRE', '11) distinta: il padre stesso');
SELECT is(pg_temp.distinta('C2'), 'COMPONENTE_COMPOSITO', '12) distinta: un composito (D-4)');
SELECT is(pg_temp.distinta('C3'), 'IVA_DISCORDANTE', '13) distinta: IVA diversa dal padre');
SELECT throws_like(
    format($$SELECT script.fn_check_articolo_riga('ARTICOLO', NULL, %L)$$, pg_temp.art('C1')),
    '%p_articolo_padre_id%',
    '14) distinta senza padre: E_PARAMETRO_INVALIDO');

-- ============================================================
-- Distinta: il guard (15-19)
-- ============================================================
SELECT throws_like(pg_temp.legame('C2'), '%a sua volta un articolo composito%',
    '15) articoli_componenti: componente composito rifiutato');
SELECT throws_like(pg_temp.legame('C3'), '%IVA%',
    '16) articoli_componenti: IVA diversa dal padre rifiutata');
SELECT throws_like(pg_temp.legame('P'), '%propria distinta%',
    '17) articoli_componenti: il padre come componente, rifiutato col codice prima del CHECK');
SELECT lives_ok(pg_temp.legame('C1'), '18) articoli_componenti: componente semplice ammesso');
SELECT lives_ok(pg_temp.legame('C2', false), '19) articoli_componenti: un legame spento non si giudica');

-- ============================================================
-- Il ritiro (20)
-- ============================================================
SELECT ok(
    to_regprocedure('vendite.trgfn_listini_righe_guard_tipologia()') IS NULL
    AND to_regprocedure('vendite.trgfn_listini_righe_guard_no_composito()') IS NULL
    AND to_regprocedure('catalogo.trgfn_articoli_componenti_guard_un_livello()') IS NULL
    AND to_regprocedure('catalogo.trgfn_articoli_componenti_guard_iva()') IS NULL,
    '20) i quattro guard per regola non ci sono piu''');

SELECT * FROM finish();
ROLLBACK;
