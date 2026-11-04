-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: il building block «il corpo di una funzione, senza i commenti»
--       dbops.fn_testo_senza_commenti · dbops.fn_corpo_funzione
--       e i due strumenti che lo usano, dbops.fn_find_function_usage e
--       dbops.fn_search_column_usage.
--
-- ChangeSet: 20_code/dbops/20261104-20 (il building block), 20261104-21 … -29
--            (le viste che lo leggono), 20261104-30/-31 (i due strumenti)
-- Brief: brief-db-revisione-dbops, D14 + D15 + D54 (giro 1)
--
-- ⛔ IL DIFETTO CHE CHIUDE. Nove viste e due strumenti cercavano nei corpi un
--   codice, una tabella scritta, un valore, e ognuno toglieva i commenti a modo
--   suo, senza rispettare i letterali; e tutti leggevano prosrc, che per una
--   funzione SQL BEGIN ATOMIC e' vuoto. I casi qui sotto sono quelli che le
--   copie sbagliavano: si COSTRUISCONO, non si cercano nel codice di oggi.
--
-- Elenco test (plan 15):
--   IL TESTO
--    1 : un `--` dentro un letterale resta, il commento di riga vero esce
--    2 : un commento a blocco su piu' righe esce, col codice che nomina
--    3 : ⭐ DUE commenti a blocco: il codice FRA i due resta (la trappola
--        greedy: un'alternativa al primo livello e' sempre greedy)
--    4 : un letterale E'…' con \' non desincronizza il resto
--    5 : un identificatore "a--b" resta intero
--    6 : senza testo, NULL
--   IL CORPO
--    7 : plpgsql: e' il suo prosrc senza i commenti
--    8 : ⭐ BEGIN ATOMIC: il corpo c'e' (prosrc e' vuoto) ...
--    9 : ... ed e' qualificato anche con un search_path che contiene lo schema
--   10 : un oid che non e' una funzione: NULL
--   IL PRESIDIO SUL TESTO
--   11 : ⛔ nessuna vista e nessuna funzione passa prosrc a una regexp_*: chi
--        cerca nei corpi passa dal building block (la copia non torna)
--   GLI STRUMENTI
--   12 : ⭐ fn_search_column_usage trova la colonna in un VINCOLO (conbin non la
--        nominava: rispondeva sempre vuoto — D54)
--   13 : fn_search_column_usage trova la colonna nel corpo di una BEGIN ATOMIC
--   14 : fn_find_function_usage trova un chiamante BEGIN ATOMIC
--   15 : fn_find_function_usage non conta una chiamata rimasta in un commento
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;. Le funzioni di prova stanno in
-- pg_temp, la tabella di prova e' temporanea: il ROLLBACK le porta via.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file legge solo il catalogo, ma il preambolo e' un
-- contratto (guardrail_pgtap_preambolo) e il test gira come l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- 1-6. Il testo
-- ============================================================
SELECT is(dbops.fn_testo_senza_commenti($t$a := 'x--y'; -- via 'E_COMMENTO'$t$),
          $t$a := 'x--y'; $t$,
          '1. un -- dentro un letterale resta; il commento di riga vero esce, col codice che nomina');

SELECT is(dbops.fn_testo_senza_commenti($t$b := 1; /* 'E_BLOCCO'
   su due righe */ c := 2;$t$),
          $t$b := 1;  c := 2;$t$,
          '2. un commento a blocco su piu'' righe esce, col codice che nomina');

SELECT is(dbops.fn_testo_senza_commenti($t$/* uno */ d := 'E_FRA_I_DUE'; /* due */$t$),
          $t$ d := 'E_FRA_I_DUE'; $t$,
          '3. due commenti a blocco: il codice FRA i due resta (un /\*.*?\*/ in alternativa sarebbe greedy e lo mangerebbe)');

SELECT is(dbops.fn_testo_senza_commenti($t$e := E'a\'b -- dentro'; f := 2; -- fuori$t$),
          $t$e := E'a\'b -- dentro'; f := 2; $t$,
          '4. un letterale E''…'' con \'' non desincronizza: il -- dentro resta, quello fuori esce');

SELECT is(dbops.fn_testo_senza_commenti($t$g := "col--x"; h := '/* non e'' un commento */';$t$),
          $t$g := "col--x"; h := '/* non e'' un commento */';$t$,
          '5. un identificatore "a--b" e un /* dentro un letterale restano interi');

SELECT is(dbops.fn_testo_senza_commenti(NULL), NULL,
          '6. senza testo, NULL');

-- ============================================================
-- 7-10. Il corpo
-- ============================================================
CREATE FUNCTION pg_temp.fn_pgtap_corpo_plpgsql() RETURNS void
LANGUAGE plpgsql AS $f$
BEGIN
    -- un commento di riga
    PERFORM 1; /* e uno a blocco */
END
$f$;

CREATE FUNCTION pg_temp.fn_pgtap_corpo_atomic() RETURNS bigint
LANGUAGE sql
BEGIN ATOMIC
    SELECT count(*) FROM dbops.presidi;
END;

SELECT is(dbops.fn_corpo_funzione('pg_temp.fn_pgtap_corpo_plpgsql()'::regprocedure),
          dbops.fn_testo_senza_commenti(
              (SELECT prosrc FROM pg_proc WHERE oid = 'pg_temp.fn_pgtap_corpo_plpgsql()'::regprocedure)),
          '7. plpgsql: il corpo e'' il suo prosrc senza i commenti');

SELECT ok((SELECT prosrc = '' FROM pg_proc WHERE oid = 'pg_temp.fn_pgtap_corpo_atomic()'::regprocedure)
          AND dbops.fn_corpo_funzione('pg_temp.fn_pgtap_corpo_atomic()'::regprocedure) ~ '\mFROM\s+dbops\.presidi\M',
          '8. BEGIN ATOMIC: prosrc e'' vuoto, e il corpo c''e'' lo stesso (da prosqlbody)');

-- ⚠️ Con dbops nel search_path pg_get_function_sqlbody stamperebbe `presidi`:
--   il building block fissa pg_catalog e qualifica tutto, per chiunque chiami.
SET LOCAL search_path = dbops, public;
SELECT ok(dbops.fn_corpo_funzione('pg_temp.fn_pgtap_corpo_atomic()'::regprocedure) ~ '\mdbops\.presidi\M',
          '9. il corpo di una BEGIN ATOMIC e'' qualificato anche quando lo schema e'' nel search_path del chiamante');
RESET search_path;

SELECT is(dbops.fn_corpo_funzione('pg_class'::regclass::oid), NULL,
          '10. un oid che non e'' una funzione: NULL');

-- ============================================================
-- 11. Il presidio sul testo
-- ============================================================
-- ⛔ Togliere i commenti da prosrc con una regex propria, o tagliarlo a righe,
--   e' la copia che il building block ha ritirato. Si guarda il testo delle
--   viste e il corpo delle funzioni (senza commenti: una menzione in prosa non
--   e' una lettura). Un prefiltro come `prosrc LIKE …` o `prosrc ~ …` resta
--   ammesso: e' un sovrainsieme economico, non una lettura del corpo.
SELECT is_empty(
    $$SELECT 'vista ' || n.nspname || '.' || c.relname
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE c.relkind IN ('v', 'm')
         AND n.nspname NOT IN ('pg_catalog', 'information_schema')
         AND pg_get_viewdef(c.oid) ~ 'regexp_\w+\(\s*\(?\s*(\w+\.)?prosrc\M'
      UNION ALL
      SELECT 'funzione ' || p.oid::regprocedure::text
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
         AND dbops.fn_corpo_funzione(p.oid) ~ 'regexp_\w+\(\s*\(?\s*(\w+\.)?prosrc\M'$$,
    '11. nessuna vista e nessuna funzione passa prosrc a una regexp_*: chi cerca nei corpi passa da dbops.fn_corpo_funzione');

-- ============================================================
-- 12-15. Gli strumenti
-- ============================================================
CREATE TEMP TABLE pgtap_corpo_prova (
    colonna_pgtap_corpo_unica integer
        CONSTRAINT chk_pgtap_corpo_prova CHECK (colonna_pgtap_corpo_unica > 0)
) ON COMMIT DROP;

CREATE FUNCTION pg_temp.fn_pgtap_legge_colonna_atomic() RETURNS bigint
LANGUAGE sql
BEGIN ATOMIC
    SELECT count(colonna_pgtap_corpo_unica) FROM pgtap_corpo_prova;
END;

CREATE FUNCTION pg_temp.fn_pgtap_bersaglio_uso() RETURNS integer
LANGUAGE sql AS $f$ SELECT 1 $f$;

CREATE FUNCTION pg_temp.fn_pgtap_chiamante_atomic() RETURNS integer
LANGUAGE sql
BEGIN ATOMIC
    SELECT pg_temp.fn_pgtap_bersaglio_uso();
END;

CREATE FUNCTION pg_temp.fn_pgtap_chiamante_in_commento() RETURNS void
LANGUAGE plpgsql AS $f$
BEGIN
    /* un giorno: PERFORM pg_temp.fn_pgtap_bersaglio_uso(); */
    NULL;
END
$f$;

SELECT is((SELECT string_agg(object_name, ', ')
             FROM dbops.fn_search_column_usage('colonna_pgtap_corpo_unica')
            WHERE object_type = 'constraint'),
          'chk_pgtap_corpo_prova',
          '12. fn_search_column_usage trova la colonna nel vincolo: la definizione la nomina, conbin no (D54)');

SELECT ok(EXISTS (SELECT 1 FROM dbops.fn_search_column_usage('colonna_pgtap_corpo_unica')
                   WHERE object_type = 'function' AND object_name = 'fn_pgtap_legge_colonna_atomic'),
          '13. fn_search_column_usage trova la colonna nel corpo di una funzione SQL BEGIN ATOMIC');

SELECT ok(EXISTS (SELECT 1 FROM dbops.fn_find_function_usage('fn_pgtap_bersaglio_uso')
                   WHERE object_type = 'function' AND object_name = 'fn_pgtap_chiamante_atomic()'),
          '14. fn_find_function_usage trova un chiamante SQL BEGIN ATOMIC');

SELECT ok(NOT EXISTS (SELECT 1 FROM dbops.fn_find_function_usage('fn_pgtap_bersaglio_uso')
                       WHERE object_name = 'fn_pgtap_chiamante_in_commento()'),
          '15. fn_find_function_usage non conta una chiamata rimasta in un commento');

SELECT * FROM finish();
ROLLBACK;
