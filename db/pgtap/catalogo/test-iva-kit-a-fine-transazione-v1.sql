-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'IVA di un kit e dei suoi componenti si giudica a fine transazione
--   (catalogo.trgfn_articoli_guard_iva_bom_attiva, constraint trigger differito),
--   sui legami da oggi in poi.
--
-- Elenco test (plan 7):
--  1) il trigger e' un constraint trigger DEFERRABLE INITIALLY DEFERRED
--  2) in un UPDATE solo, kit e componente cambiano IVA insieme: passa
--  3) in due istruzioni, prima il kit poi il componente, a vincoli differiti:
--     passa al momento del giudizio
--  4) il solo kit: E_BOM_IVA_DISCORDANTE
--  5) il solo componente: E_BOM_IVA_DISCORDANTE
--  6) un legame finito ieri non blocca: il kit cambia IVA da solo
--  7) un kit senza IVA: il messaggio dice «—», non un segnaposto vuoto
--
-- Scopo:
--  - D4: prima il guard era BEFORE riga per riga, e confrontava col valore attuale
--    dell'altro articolo: il cambio d'IVA di un kit non passava in nessun ordine, e
--    contavano anche i legami chiusi. D21: con l'IVA vuota la frase usciva col
--    segnaposto vuoto.
--
-- Mondo: articoli e legami costruiti; due aliquote diverse dal catalogo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE OR REPLACE FUNCTION pg_temp.oggi() RETURNS date LANGUAGE sql STABLE AS
$fx$ SELECT script.fn_data_operativa() $fx$;

CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT split_part(m.messaggio, '%s', 1) || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it'
$fx$;

-- Due aliquote diverse.
CREATE TEMP TABLE tmp_iv AS
SELECT (array_agg(i.id ORDER BY i.id))[1] AS a,
       (array_agg(i.id ORDER BY i.id))[2] AS b
  FROM config.iva i
 WHERE i.attivo
   AND i.aliquota_iva > 0;

-- K con C (legame aperto); H con D (legame finito ieri). Tutti con l'IVA a.
CREATE TEMP TABLE tmp_iv_art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo('PGTAP-IVK-' || v.s,
                                         p_is_composito => v.s IN ('K', 'H')) AS id
  FROM (VALUES ('K'), ('C'), ('H'), ('D')) v(s);

CREATE OR REPLACE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_iv_art WHERE s = p $fx$;

UPDATE catalogo.articoli SET iva_id = (SELECT a FROM tmp_iv)
 WHERE id IN (SELECT id FROM tmp_iv_art);

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal, valido_al)
VALUES (pg_temp.art('K'), pg_temp.art('C'), 1, pg_temp.oggi() - 100, NULL),
       (pg_temp.art('H'), pg_temp.art('D'), 1, pg_temp.oggi() - 100, pg_temp.oggi() - 1);

-- 1
SELECT ok(
    EXISTS (SELECT 1 FROM pg_trigger t
             WHERE t.tgrelid = 'catalogo.articoli'::regclass
               AND t.tgname  = 'trg_articoli_a10_guard_iva_bom_attiva_upd'
               AND t.tgconstraint <> 0
               AND t.tgdeferrable
               AND t.tginitdeferred),
    '1) il guard dell''IVA e'' un constraint trigger differito');

-- 2
SELECT lives_ok(
    format('UPDATE catalogo.articoli SET iva_id = %s WHERE id IN (%L, %L)',
           (SELECT b FROM tmp_iv), pg_temp.art('K'), pg_temp.art('C')),
    '2) un UPDATE solo: kit e componente cambiano IVA insieme');

-- 3
SET CONSTRAINTS catalogo.trg_articoli_a10_guard_iva_bom_attiva_upd DEFERRED;
UPDATE catalogo.articoli SET iva_id = (SELECT a FROM tmp_iv) WHERE id = pg_temp.art('K');
UPDATE catalogo.articoli SET iva_id = (SELECT a FROM tmp_iv) WHERE id = pg_temp.art('C');
SELECT lives_ok(
    'SET CONSTRAINTS catalogo.trg_articoli_a10_guard_iva_bom_attiva_upd IMMEDIATE',
    '3) due istruzioni, prima il kit poi il componente: al giudizio passa');

-- 4
SELECT throws_like(
    format('UPDATE catalogo.articoli SET iva_id = %s WHERE id = %L',
           (SELECT b FROM tmp_iv), pg_temp.art('K')),
    pg_temp.msg('E_BOM_IVA_DISCORDANTE'),
    '4) il solo kit: E_BOM_IVA_DISCORDANTE');

-- 5
SELECT throws_like(
    format('UPDATE catalogo.articoli SET iva_id = %s WHERE id = %L',
           (SELECT b FROM tmp_iv), pg_temp.art('C')),
    pg_temp.msg('E_BOM_IVA_DISCORDANTE'),
    '5) il solo componente: E_BOM_IVA_DISCORDANTE');

-- 6
SELECT lives_ok(
    format('UPDATE catalogo.articoli SET iva_id = %s WHERE id = %L',
           (SELECT b FROM tmp_iv), pg_temp.art('H')),
    '6) un legame finito ieri non blocca: il kit cambia IVA da solo');

-- 7
SELECT throws_like(
    format('UPDATE catalogo.articoli SET iva_id = NULL WHERE id = %L', pg_temp.art('K')),
    '%—%',
    '7) un kit senza IVA: la frase dice «—», non un segnaposto vuoto');

SELECT * FROM finish();
ROLLBACK;
