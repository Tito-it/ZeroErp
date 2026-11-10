-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- PRESIDIO: i COMMENT di dbops e maintenance descrivono l'oggetto, non la sua
-- storia (linee-guida-sql §5d). Nessun COMMENT del perimetro porta:
--   - il nome o il percorso di un brief;
--   - un marcatore di revisione («rev 2026-…», «rev»);
--   - l'id di un changeSet (AAAAMMGG-NN);
--   - l'hash di un commit (7-12 cifre esadecimali, con almeno una lettera e una cifra).
-- Le date, le sigle di decisione e le misure non entrano: possono stare in una frase
-- lecita, e un presidio che sbaglia insegna a ignorarlo. Si leggono a mano quando una
-- famiglia si riapre.
--
-- Perimetro: ogni oggetto con COMMENT negli schemi dbops e maintenance (tabelle,
-- colonne, viste, funzioni, procedure, trigger, vincoli, indici, tipi), piu' le due
-- colonne che dbops.fn_storico_arma_scope scrive su ogni shadow di storico
-- (origine_schema, scope_emittente_fiscale_id). Gli altri schemi hanno il loro debito,
-- riscritto per famiglia; il debito NUOVO lo ferma in tutto il database il guardrail
-- scripts/guardrail_comment_al_presente.py sui changeSet aggiunti.
--
-- Brief: brief-db-revisione-dbops, giro 14 (N1, N2).
--
-- Elenco test (plan 5):
--  1) nessun COMMENT del perimetro nomina un brief
--  2) nessun COMMENT del perimetro porta un marcatore di revisione
--  3) nessun COMMENT del perimetro porta l'id di un changeSet
--  4) nessun COMMENT del perimetro porta l'hash di un commit
--  5) le due colonne generate su ogni shadow di storico non portano nessuna delle
--     quattro marche (il testo sta in dbops.fn_storico_arma_scope)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: il test non scrive, ma il preambolo e' uguale per tutti.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

CREATE TEMP TABLE tmp_cmt ON COMMIT DROP AS
SELECT i.schema, i.type, i.identity, d.description AS txt
  FROM pg_catalog.pg_description d
  CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classoid, d.objoid, d.objsubid) i
 WHERE i.schema IN ('dbops', 'maintenance');

CREATE TEMP TABLE tmp_cmt_storico ON COMMIT DROP AS
SELECT i.identity, d.description AS txt
  FROM pg_catalog.pg_description d
  JOIN pg_catalog.pg_class c     ON c.oid = d.objoid AND d.classoid = 'pg_catalog.pg_class'::regclass
  JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = d.objsubid
  CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classoid, d.objoid, d.objsubid) i
 WHERE c.relnamespace = 'storico'::regnamespace
   AND c.relkind IN ('r', 'p')
   AND a.attname IN ('origine_schema', 'scope_emittente_fiscale_id');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt WHERE txt ~* 'brief'),
    ARRAY[]::text[],
    '1) nessun COMMENT di dbops e maintenance nomina un brief');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt WHERE txt ~* '\mrev\M'),
    ARRAY[]::text[],
    '2) nessun COMMENT di dbops e maintenance porta un marcatore di revisione');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt WHERE txt ~ '\m20\d{6}-\d{2,3}\M'),
    ARRAY[]::text[],
    '3) nessun COMMENT di dbops e maintenance porta l''id di un changeSet');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt WHERE txt ~ '\m(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,12}\M'),
    ARRAY[]::text[],
    '4) nessun COMMENT di dbops e maintenance porta l''hash di un commit');

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt_storico
      WHERE txt ~* 'brief' OR txt ~* '\mrev\M' OR txt ~ '\m20\d{6}-\d{2,3}\M'
         OR txt ~ '\m(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,12}\M'),
    ARRAY[]::text[],
    '5) le colonne di scope generate sulle shadow di storico non portano marche');

SELECT * FROM finish();
ROLLBACK;
