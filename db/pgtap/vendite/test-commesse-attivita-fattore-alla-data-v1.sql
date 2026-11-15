-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un'attivita' di commessa senza fattore prende quello alla data
--   dell'attivita', non 1 (vendite.trgfn_attivita_fattore_alla_data,
--   script.fn_fattore_uom_alla_data).
--
-- Elenco test (plan 7):
--  1) nessun DEFAULT sul fattore di commesse_attivita e attivita_fatturabili
--  2) la madre vendite.fn_upsert_commessa_attivita: p_factor_to_base senza 1 per difetto
--  3) attivita' nell'unita' base, senza fattore: 1
--  4) cambia l'unita' operativa in una mappata: il fattore della mappatura alla data
--  5) cambia l'unita' operativa in una senza conversione -> E_UOM_MISSING
--  6) il fattore scritto si rispetta (la fotografia)
--  7) il rifiuto: il codice e il campo dell'unita' sui canali dell'errore
--
-- Scopo:
--  - D26 (Q30): prima il fattore mancante valeva 1 (DEFAULT della colonna, del
--    parametro della madre, COALESCE), e 3 cartoni passavano come 3 pezzi.
--
-- Mondo: una commessa costruita, un'attivita' costruita; unita' e mappatura del test.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE tmp_cf_c AS SELECT * FROM dbops.fn_pgtap_crea_commessa('fattore alla data');

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_cf_c));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE OR REPLACE FUNCTION pg_temp.oggi() RETURNS date LANGUAGE sql STABLE AS
$fx$ SELECT script.fn_data_operativa() $fx$;

-- Scopo: il messaggio intero di un codice, coi segnaposto come jolly, per throws_like.
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

CREATE TEMP TABLE tmp_cf_u AS
SELECT pg_temp.unita('PGTCF-CRT', 'IMBALLAGGIO') AS crt,
       pg_temp.unita('PGTCF-PAL', 'IMBALLAGGIO') AS pal;

-- L'articolo dell'attivita' e' quello del builder; la sua mappatura in cartoni.
CREATE TEMP TABLE tmp_cf_a AS
SELECT x.attivita_id AS id, x.articolo_id
  FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_cf_c)) x;

INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal)
SELECT a.articolo_id, u.crt, 6, pg_temp.oggi() - 3650 FROM tmp_cf_a a, tmp_cf_u u;

-- Scopo: il codice (canale CONSTRAINT) e il campo (canale COLUMN) dell'errore di
--   un'istruzione; NULL se non fallisce.
CREATE OR REPLACE FUNCTION pg_temp.errore(p_sql text) RETURNS jsonb LANGUAGE plpgsql AS $fx$
DECLARE v_codice text; v_campo text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME, v_campo = COLUMN_NAME;
    RETURN jsonb_build_object('codice', v_codice, 'campo', v_campo);
END $fx$;

CREATE OR REPLACE FUNCTION pg_temp.fattore() RETURNS numeric LANGUAGE sql STABLE AS
$fx$ SELECT ca.factor_to_base FROM vendite.commesse_attivita ca WHERE ca.id = (SELECT id FROM tmp_cf_a) $fx$;

-- 1
SELECT ok(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = 'vendite' AND column_name = 'factor_to_base'
                   AND table_name IN ('commesse_attivita', 'attivita_fatturabili')
                   AND column_default IS NOT NULL),
    '1) nessun DEFAULT sul fattore di commesse_attivita e attivita_fatturabili');

-- 2
SELECT ok(
    pg_get_function_arguments('vendite.fn_upsert_commessa_attivita'::regproc)
        LIKE '%p_factor_to_base numeric DEFAULT NULL::numeric%',
    '2) la madre: p_factor_to_base senza 1 per difetto');

-- 3
SELECT is(pg_temp.fattore(), 1::numeric,
    '3) attivita'' nell''unita'' base, senza fattore: 1');

-- 4
UPDATE vendite.commesse_attivita SET uom_operativa_id = (SELECT crt FROM tmp_cf_u)
 WHERE id = (SELECT id FROM tmp_cf_a);
SELECT is(pg_temp.fattore(), 6::numeric,
    '4) cambia l''unita'' operativa in una mappata: il fattore della mappatura alla data');

-- 5
SELECT throws_like(
    format('UPDATE vendite.commesse_attivita SET uom_operativa_id = %s WHERE id = %s',
           (SELECT pal FROM tmp_cf_u), (SELECT id FROM tmp_cf_a)),
    pg_temp.msg('E_UOM_MISSING'),
    '5) cambia l''unita'' operativa in una senza conversione: E_UOM_MISSING');

-- 6
UPDATE vendite.commesse_attivita SET factor_to_base = 7 WHERE id = (SELECT id FROM tmp_cf_a);
SELECT is(pg_temp.fattore(), 7::numeric,
    '6) il fattore scritto si rispetta');

-- 7
SELECT is(
    pg_temp.errore(format('UPDATE vendite.commesse_attivita SET uom_operativa_id = %s, factor_to_base = NULL WHERE id = %s',
                          (SELECT pal FROM tmp_cf_u), (SELECT id FROM tmp_cf_a))),
    '{"codice": "E_UOM_MISSING", "campo": "uom_operativa_id"}'::jsonb,
    '7) il rifiuto: il codice sul canale CONSTRAINT e il campo uom_operativa_id su COLUMN');

SELECT * FROM finish();
ROLLBACK;
