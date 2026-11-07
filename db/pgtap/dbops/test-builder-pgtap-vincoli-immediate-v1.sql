-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un builder pgTAP che chiude i vincoli lo dice nel COMMENT.
-- ChangeSet: 20261108-09 (i quattro COMMENT che non lo dicevano)
-- Brief: brief-db-sorgente-documento-e-riga §8.11 «Gli smoke»
--
-- I builder dbops.fn_pgtap_* chiudono la propria unita' di lavoro con
-- SET CONSTRAINTS ALL IMMEDIATE, e l'impostazione resta per il resto della
-- transazione: uno smoke che dopo il builder esegue un verbo vero vede scattare
-- a meta' verbo un guard che al commit sarebbe differito, e deve riaprire la
-- finestra. Lo deve sapere dal catalogo, non leggendo il corpo.
--
-- Elenco test (plan 2):
--   1) gemello «esiste»: ci sono builder che chiudono i vincoli (il test 2 non
--      passa a vuoto)
--   2) ogni funzione dbops.fn_pgtap_* che scrive SET CONSTRAINTS ALL IMMEDIATE
--      lo dichiara nel COMMENT (la parola IMMEDIATE)
--
-- ⭐ Il perimetro e' DERIVATO dal corpo, senza elenco: un builder nuovo che
--   chiude i vincoli senza dirlo e' rosso qui dal primo giorno.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(2);

CREATE TEMP TABLE _builder AS
SELECT p.proname::text AS nome,
       coalesce(obj_description(p.oid, 'pg_proc'), '') AS commento
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'dbops'
   AND p.proname LIKE 'fn\_pgtap\_%'
   AND p.prosrc ~* 'SET\s+CONSTRAINTS\s+ALL\s+IMMEDIATE';

SELECT ok(
    (SELECT count(*) FROM _builder) >= 20,
    '1) ci sono builder pgTAP che chiudono i vincoli: il test 2 ha un perimetro');

SELECT is(
    (SELECT coalesce(string_agg(b.nome, ', ' ORDER BY b.nome), '')
       FROM _builder b
      WHERE b.commento !~ 'IMMEDIATE'),
    '',
    '2) ogni builder che chiude i vincoli lo dichiara nel COMMENT (IMMEDIATE)');

SELECT * FROM finish();
ROLLBACK;
