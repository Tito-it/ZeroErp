-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- PRESIDIO: i COMMENT delle famiglie riscritte descrivono l'oggetto, non la sua
-- storia (linee-guida-sql §5d). Nessun COMMENT del perimetro porta:
--   - il nome o il percorso di un brief;
--   - un marcatore di revisione («rev 2026-…», «rev»);
--   - l'id di un changeSet (AAAAMMGG-NN);
--   - l'hash di un commit (7-12 cifre esadecimali, con almeno una lettera e una cifra).
-- Le date, le sigle di decisione e le misure non entrano: possono stare in una frase
-- lecita, e un presidio che sbaglia insegna a ignorarlo. Si leggono a mano quando una
-- famiglia si riapre.
--
-- Perimetro: ogni oggetto con COMMENT negli schemi della lista _schemi (tabelle,
-- colonne, viste, funzioni, procedure, trigger, vincoli, indici, tipi), piu' gli
-- oggetti fuori schema riscritti con una famiglia (lista _fuori) e le due colonne che
-- dbops.fn_storico_arma_scope scrive su ogni shadow di storico (origine_schema,
-- scope_emittente_fiscale_id). Uno schema entra nella lista quando la sua famiglia e'
-- riscritta; il debito NUOVO lo ferma in tutto il database il guardrail
-- scripts/guardrail_comment_al_presente.py sui changeSet aggiunti.
-- ⚠️ Lo schema di un trigger e di una policy si legge dalla sua tabella:
--    pg_identify_object da' schema NULL a tutti e due, e un filtro su quella colonna
--    non li vede (il 7 e l'8 lo tengono fermo).
--
-- Elenco test (plan 8):
--  1) gli oggetti fuori schema sono nel perimetro, col loro COMMENT
--  2) nessun COMMENT del perimetro nomina un brief
--  3) nessun COMMENT del perimetro porta un marcatore di revisione
--  4) nessun COMMENT del perimetro porta l'id di un changeSet
--  5) nessun COMMENT del perimetro porta l'hash di un commit
--  6) le due colonne generate su ogni shadow di storico non portano nessuna delle
--     quattro marche (il testo sta in dbops.fn_storico_arma_scope)
--  7) i COMMENT dei trigger di dbops e documenti sono nel perimetro
--  8) i COMMENT delle policy di documenti sono nel perimetro
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: il test non scrive, ma il preambolo e' uguale per tutti.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- Gli schemi la cui famiglia di COMMENT e' riscritta.
CREATE TEMP TABLE _schemi ON COMMIT DROP AS
SELECT unnest(ARRAY['dbops', 'maintenance', 'catalogo', 'documenti']) AS nome;

-- Gli oggetti fuori da quegli schemi riscritti con una famiglia: i cinque nati col
-- ritiro degli articoli (obsoleto_dal), riscritti con catalogo.
CREATE TEMP TABLE _fuori ON COMMIT DROP AS
SELECT unnest(ARRAY[
    'acquisti.ddt_righe.sorgente_tipo_id',
    'script.trgfn_righe_guard_articolo_ammesso()',
    'vendite.fn_clona_versione_listino(bigint,character varying,pg_catalog.date,pg_catalog.date)',
    'trg_commesse_attivita_a10_onere_articolo_non_obsoleto_ins_upd on vendite.commesse_attivita',
    'trg_listini_kit_a10_articoli_require_non_obsoleto_ins_upd on vendite.listini_kit'
]) AS identity;

-- Ogni COMMENT, con lo schema dell'oggetto: quello di trigger e policy dalla loro
-- tabella.
CREATE TEMP TABLE _tutti ON COMMIT DROP AS
SELECT COALESCE(i.schema, tn.nspname, pn.nspname) AS schema, i.type, i.identity, d.description AS txt
  FROM pg_catalog.pg_description d
  CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classoid, d.objoid, d.objsubid) i
  LEFT JOIN pg_catalog.pg_trigger t
         ON d.classoid = 'pg_catalog.pg_trigger'::regclass AND t.oid = d.objoid
  LEFT JOIN pg_catalog.pg_class tc     ON tc.oid = t.tgrelid
  LEFT JOIN pg_catalog.pg_namespace tn ON tn.oid = tc.relnamespace
  LEFT JOIN pg_catalog.pg_policy p
         ON d.classoid = 'pg_catalog.pg_policy'::regclass AND p.oid = d.objoid
  LEFT JOIN pg_catalog.pg_class pc     ON pc.oid = p.polrelid
  LEFT JOIN pg_catalog.pg_namespace pn ON pn.oid = pc.relnamespace;

CREATE TEMP TABLE tmp_cmt ON COMMIT DROP AS
SELECT a.schema, a.type, a.identity, a.txt
  FROM _tutti a
 WHERE a.schema IN (SELECT nome FROM _schemi)
    OR a.identity IN (SELECT identity FROM _fuori);

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
    (SELECT count(*)::int FROM tmp_cmt c JOIN _fuori f ON f.identity = c.identity),
    (SELECT count(*)::int FROM _fuori),
    '1) gli oggetti fuori schema sono nel perimetro, col loro COMMENT');

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

SELECT is(
    (SELECT COALESCE(array_agg(identity ORDER BY identity), ARRAY[]::text[])
       FROM tmp_cmt_storico
      WHERE txt ~* 'brief' OR txt ~* '\mrev\M' OR txt ~ '\m20\d{6}-\d{2,3}\M'
         OR txt ~ '\m(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,12}\M'),
    ARRAY[]::text[],
    '6) le colonne di scope generate sulle shadow di storico non portano marche');

-- 7) I trigger sono nel perimetro: dbops e documenti scrivono COMMENT sui loro trigger
--    a mano. Con lo schema letto da pg_identify_object (NULL per un trigger) qui non
--    ce ne sarebbe nessuno, e 2-5 passerebbero senza guardarli.
SELECT is(
    (SELECT COALESCE(array_agg(DISTINCT schema ORDER BY schema), ARRAY[]::text[])
       FROM tmp_cmt WHERE type = 'trigger' AND schema IN ('dbops', 'documenti')),
    ARRAY['dbops', 'documenti']::text[],
    '7) i COMMENT dei trigger di dbops e documenti sono nel perimetro');

-- 8) Le policy, come i trigger: pg_identify_object da' schema NULL anche a loro, e
--    documenti scrive COMMENT sulle policy delle sue tabelle.
SELECT is(
    (SELECT COALESCE(array_agg(DISTINCT schema ORDER BY schema), ARRAY[]::text[])
       FROM tmp_cmt WHERE type = 'policy' AND schema = 'documenti'),
    ARRAY['documenti']::text[],
    '8) i COMMENT delle policy di documenti sono nel perimetro');

SELECT * FROM finish();
ROLLBACK;
