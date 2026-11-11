-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- PRESIDIO: i COMMENT di catalogo descrivono l'oggetto, non la sua storia
-- (linee-guida-sql §5d). La famiglia e' riscritta: nessun COMMENT del perimetro porta
--   - il nome o il percorso di un brief;
--   - un marcatore di revisione («rev 2026-…», «rev»);
--   - l'id di un changeSet (AAAAMMGG-NN);
--   - l'hash di un commit (7-12 cifre esadecimali, con almeno una lettera e una cifra).
-- Le date, le sigle di decisione e le misure non entrano: possono stare in una frase
-- lecita, e un presidio che sbaglia insegna a ignorarlo.
--
-- Perimetro: ogni oggetto con COMMENT nello schema catalogo (tabelle, partizioni,
-- colonne, viste, funzioni, trigger, vincoli, indici), piu' i cinque oggetti fuori
-- schema nati col ritiro degli articoli (obsoleto_dal), riscritti insieme:
-- acquisti.ddt_righe.sorgente_tipo_id, script.trgfn_righe_guard_articolo_ammesso,
-- vendite.fn_clona_versione_listino e i due trigger OBSOLETO di vendite.
-- dbops e maintenance hanno il loro presidio (dbops/test-comment-al-presente-v1);
-- il debito NUOVO lo ferma in tutto il database scripts/guardrail_comment_al_presente.py.
--
-- Brief: brief-db-revisione-catalogo, giro 5-A (§17).
--
-- Elenco test (plan 5):
--  1) il perimetro c'e': i cinque oggetti fuori schema hanno un COMMENT
--  2) nessun COMMENT del perimetro nomina un brief
--  3) nessun COMMENT del perimetro porta un marcatore di revisione
--  4) nessun COMMENT del perimetro porta l'id di un changeSet
--  5) nessun COMMENT del perimetro porta l'hash di un commit
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: il test non scrive, ma il preambolo e' uguale per tutti.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

CREATE TEMP TABLE tmp_fuori ON COMMIT DROP AS
SELECT unnest(ARRAY[
    'acquisti.ddt_righe.sorgente_tipo_id',
    'script.trgfn_righe_guard_articolo_ammesso()',
    'vendite.fn_clona_versione_listino(bigint,character varying,pg_catalog.date,pg_catalog.date)',
    'trg_commesse_attivita_a10_onere_articolo_non_obsoleto_ins_upd on vendite.commesse_attivita',
    'trg_listini_kit_a10_articoli_require_non_obsoleto_ins_upd on vendite.listini_kit'
]) AS identity;

CREATE TEMP TABLE tmp_cmt ON COMMIT DROP AS
SELECT i.identity, d.description AS txt
  FROM pg_catalog.pg_description d
  CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classoid, d.objoid, d.objsubid) i
 WHERE i.schema = 'catalogo'
    OR i.identity IN (SELECT f.identity FROM tmp_fuori f);

SELECT is(
    (SELECT count(*)::int FROM tmp_cmt c JOIN tmp_fuori f ON f.identity = c.identity),
    5,
    '1) i cinque oggetti fuori schema sono nel perimetro, col loro COMMENT');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt WHERE txt ~* 'brief'),
    ARRAY[]::text[],
    '2) nessun COMMENT del perimetro nomina un brief');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt WHERE txt ~* '\mrev\M'),
    ARRAY[]::text[],
    '3) nessun COMMENT del perimetro porta un marcatore di revisione');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt WHERE txt ~ '\m20\d{6}-\d{2,3}\M'),
    ARRAY[]::text[],
    '4) nessun COMMENT del perimetro porta l''id di un changeSet');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt WHERE txt ~ '\m(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,12}\M'),
    ARRAY[]::text[],
    '5) nessun COMMENT del perimetro porta l''hash di un commit');

SELECT * FROM finish();
ROLLBACK;
