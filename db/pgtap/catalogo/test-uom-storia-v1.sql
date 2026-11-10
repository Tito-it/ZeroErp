-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la mappatura di un articolo e la conversione generale non riscrivono il
--   passato (catalogo.trgfn_uom_guard_storia).
--
-- Elenco test (plan 21):
--  1) mappatura in vigore: il fattore non si cambia -> E_UOM_STORIA_IMMUTABILE
--  2) mappatura in vigore: l'unita' non si cambia -> E_UOM_STORIA_IMMUTABILE
--  3) mappatura in vigore: l'inizio non si sposta -> E_UOM_STORIA_IMMUTABILE
--  4) mappatura futura: il fattore non si cambia neppure lei -> E_UOM_STORIA_IMMUTABILE
--  5) mappatura in vigore: non si spegne -> E_UOM_STORIA_IN_VIGORE
--  6) mappatura in vigore: non si cancella -> E_UOM_STORIA_IN_VIGORE
--  7) mappatura in vigore: chiusa prima di ieri -> E_UOM_STORIA_CHIUSURA_RETROATTIVA
--  8) mappatura finita: la fine non si cambia -> E_UOM_STORIA_CHIUSA
--  9) le colonne che non fanno la conversione (qty_step, gtin) si cambiano
-- 10) mappatura futura: si spegne
-- 11) mappatura che comincia oggi: si cancella
-- 12) chiudi a ieri e inserisci da oggi: passa
-- 13) dopo: il fattore di ieri e' quello vecchio, quello di oggi il nuovo
-- 14) conversione generale in vigore: il fattore non si cambia -> E_UOM_STORIA_IMMUTABILE
-- 15) conversione generale in vigore: non si cancella -> E_UOM_STORIA_IN_VIGORE
-- 16) conversione generale in vigore: si chiude a ieri
-- 17) conversione generale futura: si cancella
-- 18) la cancellazione di un articolo porta via le sue mappature in vigore
-- 19) un articolo con mappature che hanno giorni passati si spegne (Q31)
-- 20) un'unita' con mappature che hanno giorni passati si spegne (Q31)
-- 21) un'unita' con conversioni generali che hanno giorni passati si spegne (Q31)
--
-- Scopo:
--  - D24 (Q23, Q26, Q28) e D27 (Q29): prima fattore, unita', inizio e attivo si
--    cambiavano sul posto e la riga si cancellava, e catalogo.fn_get_uom_factor
--    rispondeva il valore nuovo anche per le date passate.
--
-- Mondo: unita', conversioni e articoli costruiti; le tipologie per codice_interno.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(21);

CREATE OR REPLACE FUNCTION pg_temp.oggi() RETURNS date LANGUAGE sql STABLE AS
$fx$ SELECT script.fn_data_operativa() $fx$;

-- Scopo: il messaggio intero di un codice, coi segnaposto come jolly, per
--   throws_like. Il solo prefisso non basta: i quattro codici della storia
--   cominciano tutti con «La conversione %s».
CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT '%' || replace(m.messaggio, '%s', '%') || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it'
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.unita(p_codice text, p_tipo text) RETURNS bigint
LANGUAGE sql AS $fx$
    INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id)
    SELECT p_codice, p_codice, t.id FROM catalogo.uom_tipi t WHERE t.codice_interno = p_tipo
    RETURNING id
$fx$;

CREATE TEMP TABLE tmp_us_u AS
SELECT v.k, pg_temp.unita('PGTUS-' || v.k, v.t) AS id
  FROM (VALUES ('G', 'MASSA'), ('KG', 'MASSA'), ('T', 'MASSA'),
               ('CRT', 'IMBALLAGGIO'), ('PAL', 'IMBALLAGGIO'), ('SC', 'IMBALLAGGIO'),
               ('BOX', 'IMBALLAGGIO')) v(k, t);

CREATE OR REPLACE FUNCTION pg_temp.u(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_us_u WHERE k = p $fx$;

CREATE TEMP TABLE tmp_us_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTUS-X', p_uom_id => pg_temp.u('G')) AS x,
       dbops.fn_pgtap_crea_articolo('PGTUS-Y', p_uom_id => pg_temp.u('G')) AS y;

-- Le mappature di X: in vigore (CRT), futura (PAL), da oggi (SC), finita (BOX).
CREATE TEMP TABLE tmp_us_m AS
WITH ins AS (
  INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal, valido_al)
  SELECT (SELECT x FROM tmp_us_art), pg_temp.u(v.k), v.f, pg_temp.oggi() + v.dal, pg_temp.oggi() + v.al
    FROM (VALUES ('CRT', 6, -30, NULL::integer), ('PAL', 100, 5, NULL), ('SC', 4, 0, NULL),
                 ('BOX', 3, -60, -10)) v(k, f, dal, al)
  RETURNING id, uom_id)
SELECT u.k, ins.id FROM ins JOIN tmp_us_u u ON u.id = ins.uom_id;

-- Una mappatura in vigore anche per Y (test 18).
INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal)
SELECT (SELECT y FROM tmp_us_art), pg_temp.u('CRT'), 8, pg_temp.oggi() - 30;

CREATE OR REPLACE FUNCTION pg_temp.m(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_us_m WHERE k = p $fx$;

-- Le conversioni generali: KG -> G in vigore, T -> KG futura.
CREATE TEMP TABLE tmp_us_c AS
WITH ins AS (
  INSERT INTO catalogo.unita_misura_conversioni (uom_from_id, uom_to_id, fattore, valido_dal)
  VALUES (pg_temp.u('KG'), pg_temp.u('G'), 1000, pg_temp.oggi() - 30),
         (pg_temp.u('T'), pg_temp.u('KG'), 1000, pg_temp.oggi() + 5)
  RETURNING id, uom_from_id)
SELECT u.k, ins.id FROM ins JOIN tmp_us_u u ON u.id = ins.uom_from_id;

CREATE OR REPLACE FUNCTION pg_temp.c(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_us_c WHERE k = p $fx$;

-- ============================================================
-- La mappatura
-- ============================================================

-- 1
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET factor_to_base = 12 WHERE id = %s', pg_temp.m('CRT')),
    pg_temp.msg('E_UOM_STORIA_IMMUTABILE'),
    '1) mappatura in vigore: il fattore non si cambia sul posto');

-- 2
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET uom_id = %s WHERE id = %s', pg_temp.u('BOX'), pg_temp.m('CRT')),
    pg_temp.msg('E_UOM_STORIA_IMMUTABILE'),
    '2) mappatura in vigore: l''unita'' non si cambia sul posto');

-- 3
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET valido_dal = %L WHERE id = %s',
           pg_temp.oggi() - 20, pg_temp.m('CRT')),
    pg_temp.msg('E_UOM_STORIA_IMMUTABILE'),
    '3) mappatura in vigore: l''inizio non si sposta');

-- 4
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET factor_to_base = 120 WHERE id = %s', pg_temp.m('PAL')),
    pg_temp.msg('E_UOM_STORIA_IMMUTABILE'),
    '4) mappatura futura: il fattore non si cambia neppure lei (si toglie e si rimette)');

-- 5
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET attivo = false WHERE id = %s', pg_temp.m('CRT')),
    pg_temp.msg('E_UOM_STORIA_IN_VIGORE'),
    '5) mappatura in vigore: non si spegne');

-- 6
SELECT throws_like(
    format('DELETE FROM catalogo.articoli_uom_operativa WHERE id = %s', pg_temp.m('CRT')),
    pg_temp.msg('E_UOM_STORIA_IN_VIGORE'),
    '6) mappatura in vigore: non si cancella');

-- 7
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() - 5, pg_temp.m('CRT')),
    pg_temp.msg('E_UOM_STORIA_CHIUSURA_RETROATTIVA'),
    '7) mappatura in vigore: chiusa prima di ieri, rifiutata');

-- 8
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() + 10, pg_temp.m('BOX')),
    pg_temp.msg('E_UOM_STORIA_CHIUSA'),
    '8) mappatura finita: la fine non si cambia piu''');

-- 9
SELECT lives_ok(
    format('UPDATE catalogo.articoli_uom_operativa SET qty_step = 2, gtin = %L WHERE id = %s',
           '8000000000001', pg_temp.m('CRT')),
    '9) qty_step e gtin non fanno la conversione: si cambiano');

-- 10
SELECT lives_ok(
    format('UPDATE catalogo.articoli_uom_operativa SET attivo = false WHERE id = %s', pg_temp.m('PAL')),
    '10) mappatura futura: si spegne');

-- 11
SELECT lives_ok(
    format('DELETE FROM catalogo.articoli_uom_operativa WHERE id = %s', pg_temp.m('SC')),
    '11) mappatura che comincia oggi (nessun giorno passato): si cancella');

-- 12
SELECT lives_ok(
    format($s$UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s;
              INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal)
              VALUES (%L, %s, 12, %L)$s$,
           pg_temp.oggi() - 1, pg_temp.m('CRT'),
           (SELECT x FROM tmp_us_art), pg_temp.u('CRT'), pg_temp.oggi()),
    '12) chiudi a ieri e inserisci da oggi');

-- 13
SELECT is(
    catalogo.fn_get_uom_factor((SELECT x FROM tmp_us_art), pg_temp.u('CRT'), pg_temp.oggi() - 1)::text
    || '/' ||
    catalogo.fn_get_uom_factor((SELECT x FROM tmp_us_art), pg_temp.u('CRT'), pg_temp.oggi())::text,
    '6.000000/12.000000',
    '13) dopo: ieri il fattore vecchio, oggi il nuovo');

-- ============================================================
-- La conversione generale
-- ============================================================

-- 14
SELECT throws_like(
    format('UPDATE catalogo.unita_misura_conversioni SET fattore = 999 WHERE id = %s', pg_temp.c('KG')),
    pg_temp.msg('E_UOM_STORIA_IMMUTABILE'),
    '14) conversione generale in vigore: il fattore non si cambia sul posto');

-- 15
SELECT throws_like(
    format('DELETE FROM catalogo.unita_misura_conversioni WHERE id = %s', pg_temp.c('KG')),
    pg_temp.msg('E_UOM_STORIA_IN_VIGORE'),
    '15) conversione generale in vigore: non si cancella');

-- 16
SELECT lives_ok(
    format('UPDATE catalogo.unita_misura_conversioni SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() - 1, pg_temp.c('KG')),
    '16) conversione generale in vigore: si chiude a ieri');

-- 17
SELECT lives_ok(
    format('DELETE FROM catalogo.unita_misura_conversioni WHERE id = %s', pg_temp.c('T')),
    '17) conversione generale futura: si cancella');

-- 18
SELECT lives_ok(
    format('DELETE FROM catalogo.articoli WHERE id = %L', (SELECT y FROM tmp_us_art)),
    '18) la cancellazione di un articolo porta via le sue mappature in vigore');

-- ============================================================
-- Lo spegnimento (Q31, 2026-11-10): la mappatura e' storia e non si spegne
-- dal primo giorno in vigore, quindi non puo' bloccare lo spegnimento del suo
-- articolo o della sua unita'; lo stesso la conversione generale per le sue due
-- unita' (le quattro FK sono in dbops.automazione_attivo_eccezioni).
-- ============================================================

-- 19
SELECT lives_ok(
    format('UPDATE catalogo.articoli SET attivo = false WHERE id = %L', (SELECT x FROM tmp_us_art)),
    '19) un articolo con mappature che hanno giorni passati si spegne');

-- 20
SELECT lives_ok(
    format('UPDATE catalogo.unita_misura SET attivo = false WHERE id = %s', pg_temp.u('CRT')),
    '20) un''unita'' con mappature che hanno giorni passati si spegne');

-- 21: KG -> G e' in vigore da 30 giorni (chiusa a ieri dal test 16).
SELECT lives_ok(
    format('UPDATE catalogo.unita_misura SET attivo = false WHERE id = %s', pg_temp.u('KG')),
    '21) un''unita'' con conversioni generali che hanno giorni passati si spegne');

SELECT * FROM finish();
ROLLBACK;
