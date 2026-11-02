-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: NESSUN «OGGI» PRESO DAL FUSO DELLA SESSIONE — presidio sul catalogo
--       brief-be-db-fe-un-solo-fuso-aziendale §5.1 D-8 (20261009-40..60)
-- pgtap-oggi: escluso — il presidio CERCA CURRENT_DATE & co.: le parole
--   stanno nella sua espressione regolare e nella controprova (test 4)
-- ------------------------------------------------------------
-- Indice test (1..4)
--  1) nessuna funzione (plpgsql, sql, BEGIN ATOMIC) usa CURRENT_DATE & co.
--     nel corpo o nella firma (DEFAULT dei parametri), commenti esclusi
--  2) nessuna vista lo usa
--  3) nessun DEFAULT di colonna lo usa
--  4) il presidio vede davvero: una funzione fabbricata con CURRENT_DATE
--     viene trovata (controprova, altrimenti 1-3 sarebbero verdi a vuoto)
-- ------------------------------------------------------------
-- Scopo:
--  - CURRENT_DATE, LOCALTIMESTAMP, LOCALTIME, now()::date e
--    current_timestamp::date sono il giorno (o l'ora) nel fuso della SESSIONE
--    che esegue: il backend si connette in UTC, psql/Liquibase/pgAgent nel
--    fuso del server. Nel codice del database «oggi» e' il giorno
--    dell'AZIENDA: script.fn_data_operativa() (sede del fuso:
--    script.fn_fuso_operativo). Questo file fa si' che la prossima copia
--    non nasca.
--  - Il presidio guarda il CATALOGO vivo, non i changelog: vede anche cio'
--    che un changeSet scrive in una forma che un grep sui file non prende.
--
-- ⚠️ COSA NON PRESIDIA: un `istante::date` o un `date_trunc` su un
--   timestamptz (il giorno di un istante nel fuso della sessione) non si
--   distingue dal testo da un cast su una colonna `date`, che e' innocuo. Per
--   quelli la regola e' script.fn_giorno_operativo, e il presidio e' la
--   revisione (e la CI col fuso ostile, T-5 del brief).
-- ⚠️ Esclusi gli oggetti delle ESTENSIONI (pg_depend deptype 'e'): pgTAP
--   stesso nomina CURRENT_DATE in public._def_is, e non e' codice nostro.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- La forma vietata, una volta sola per tutto il file. `\m`/`\M` = confine di
-- parola: `fn_current_date_x` non e' CURRENT_DATE.
CREATE TEMP TABLE tmp_oggi_regola AS
SELECT '\mcurrent_date\M|\mlocaltimestamp\M|\mlocaltime\M|\mnow\(\)\s*::\s*date\M|\mcurrent_timestamp\s*::\s*date\M'::text AS re;

-- Il codice di una funzione senza commenti: prima i blocchi /* */, poi le
-- righe `--`. pg_get_functiondef copre anche le BEGIN ATOMIC (prosrc vuoto)
-- e la firma, cioe' i DEFAULT dei parametri.
CREATE TEMP TABLE tmp_oggi_funzioni AS
SELECT p.oid,
       n.nspname || '.' || p.proname AS nome,
       regexp_replace(
         regexp_replace(pg_get_functiondef(p.oid), '/\*.*?\*/', '', 'g'),
         '--[^\n]*', '', 'g') AS codice
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE p.prokind IN ('f', 'p')
   AND n.nspname NOT IN ('pg_catalog', 'information_schema')
   AND n.nspname NOT LIKE 'pg\_%'
   AND NOT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_proc'::regclass
                      AND d.objid = p.oid
                      AND d.deptype = 'e');

-- ============================================================
-- 1-3) Il catalogo vivo
-- ============================================================
SELECT is(
  ARRAY(SELECT f.nome FROM tmp_oggi_funzioni f, tmp_oggi_regola r
         WHERE f.codice ~* r.re ORDER BY 1),
  ARRAY[]::text[],
  '1) nessuna funzione prende «oggi» dal fuso della sessione (usare script.fn_data_operativa)');

SELECT is(
  ARRAY(SELECT n.nspname || '.' || c.relname
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace,
               tmp_oggi_regola r
         WHERE c.relkind IN ('v', 'm')
           AND n.nspname NOT IN ('pg_catalog', 'information_schema')
           AND NOT EXISTS (SELECT 1 FROM pg_depend d
                            WHERE d.classid = 'pg_class'::regclass
                              AND d.objid = c.oid AND d.deptype = 'e')
           AND pg_get_viewdef(c.oid) ~* r.re
         ORDER BY 1),
  ARRAY[]::text[],
  '2) nessuna vista prende «oggi» dal fuso della sessione');

SELECT is(
  ARRAY(SELECT n.nspname || '.' || c.relname || '.' || a.attname
          FROM pg_attrdef ad
          JOIN pg_class c ON c.oid = ad.adrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_attribute a ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum,
               tmp_oggi_regola r
         WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
           AND pg_get_expr(ad.adbin, ad.adrelid) ~* r.re
         ORDER BY 1),
  ARRAY[]::text[],
  '3) nessun DEFAULT di colonna prende «oggi» dal fuso della sessione (DEFAULT script.fn_data_operativa())');

-- ============================================================
-- 4) Controprova: il presidio vede
-- ============================================================
-- ⭐ Un presidio che risponde «zero» va visto rispondere «uno». Si passa alla
--   STESSA pulizia e alla STESSA regola un testo con la forma vietata due
--   volte: in un commento (non deve contare) e nel codice (deve). Niente DDL:
--   il test gira come applicazione.
SELECT is(
  (SELECT count(*)::int
     FROM (SELECT regexp_replace(regexp_replace(
                    E'CREATE FUNCTION x() RETURNS date LANGUAGE sql AS $f$\n'
                    || E'  /* CURRENT_DATE in un blocco */ SELECT CURRENT_DATE -- CURRENT_DATE nel commento\n$f$',
                    '/\*.*?\*/', '', 'g'), '--[^\n]*', '', 'g') AS codice) t,
          tmp_oggi_regola r
    WHERE (SELECT count(*) FROM regexp_matches(t.codice, r.re, 'gi')) = 1),
  1,
  '4) controprova: la scansione trova CURRENT_DATE nel codice, una volta sola (non nei commenti)');

SELECT * FROM finish();
ROLLBACK;
