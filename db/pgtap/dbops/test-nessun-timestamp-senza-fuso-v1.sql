-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — test STRUTTURALE sul catalogo
--   (pg_attribute, pg_proc): nessuna tabella sotto RLS viene
--   letta, il contesto operatore non cambierebbe nessuna risposta.
-- pgTAP test per Zero ERP
--
-- Il fuso orario e' UNO: nessuna colonna, nessun parametro, nessun RETURNS
--   del progetto e' `timestamp without time zone`.
--   Voce V-3 di valutazione-modello-di-dominio-db (decisione di Tid,
--   2026-09-20: nessuna eccezione, ne' in `ui` ne' in `storico`).
--   ChangeSet: 20260920-02 (ui, 22 colonne), -03 (storico, 8 shadow),
--   -04 (config.parameters/parameter_overrides), -05/-06 (fn as_of),
--   -07 (ritiro di fn_get_iva_override), 20260921-01 (storico.parameters:
--   la NONA shadow, che dbdev non mostrava — l'ha trovata QUESTO test sulla
--   replica CI da zero, ed e' il motivo per cui e' un invariante e non un elenco).
--
-- Elenco test (plan 4):
--  1) ⛔ INVARIANTE: nessuna colonna `timestamp without time zone` fuori dalle
--        due tabelle di Liquibase (public.databasechangelog*)
--  2) ⛔ INVARIANTE: nessuna funzione del progetto con `timestamp without time
--        zone` in firma o in RETURNS (estensioni escluse per dipendenza)
--  3) gemello «esiste»: la lente vede le colonne timestamptz — il test 1 non
--        e' muto per un information_schema vuoto (RLS, ruolo, schema sbagliato)
--  4) script.fn_get_iva_override non esiste piu' (20260920-07): un DROP puo'
--        essere «segnato senza fatto» o ricreato da un runOnChange dimenticato
--
-- ⭐ PERCHE' UN INVARIANTE E NON I 34 NOMI. Il difetto nasce nel DDL
--   (`TIMESTAMP` nudo, che in PostgreSQL e' senza fuso) e rinasce con la
--   prossima tabella scritta cosi'. Un elenco di nomi sanati direbbe che
--   quelle 34 sono a posto; il catalogo dice che NESSUNA e' fuori posto —
--   compresa quella nata domani. Il cancello statico gemello
--   (scripts/guardrail_timestamp_senza_fuso.py) prende il changeSet nuovo
--   prima del migrate; questo prende il DATABASE, qualunque strada abbia
--   preso il difetto per entrarci (baseline, storia vecchia, DDL a mano).
--
-- ⚠️ PERCHE' LE DUE TABELLE DI LIQUIBASE SONO ESCLUSE PER NOME e le
--   estensioni per DIPENDENZA: databasechangelog/databasechangeloglock le
--   crea Liquibase con il suo DDL e non sono del progetto; le funzioni di
--   btree_gist (gbt_ts_*, ts_dist) sono di un'estensione, e su un oggetto di
--   estensione non si fa DDL. Le prime non hanno una dipendenza da cui
--   riconoscerle, le seconde si': pg_depend deptype 'e'.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- ============================================================
-- La lente: colonne e funzioni del progetto con un tipo timestamp
-- ============================================================
-- ⚠️ pg_attribute e non information_schema.columns: la vista standard mostra
--   solo le colonne su cui il ruolo connesso ha un privilegio, e i pgTAP
--   girano come zeroerp_app. Una tabella senza grant all'app sparirebbe
--   dalla lente e il test 1 passerebbe per sottrazione.
CREATE TEMP TABLE _colonne_ts ON COMMIT DROP AS
SELECT n.nspname || '.' || c.relname || '.' || a.attname AS colonna,
       format_type(a.atttypid, a.atttypmod)              AS data_type
  FROM pg_attribute a
  JOIN pg_class c     ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r', 'p', 'v', 'm')
   AND a.attnum > 0 AND NOT a.attisdropped
   AND a.atttypid IN ('timestamp'::regtype, 'timestamptz'::regtype)
   AND n.nspname NOT IN ('pg_catalog', 'information_schema')
   -- ⚠️ le due tabelle di Liquibase non sono del progetto (vedi intestazione)
   AND NOT (n.nspname = 'public'
            AND c.relname IN ('databasechangelog', 'databasechangeloglock'));

CREATE TEMP TABLE _funzioni_ts_nudo ON COMMIT DROP AS
SELECT n.nspname || '.' || p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' AS firma
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
   AND (pg_get_function_arguments(p.oid) ~ 'timestamp without time zone'
        OR pg_get_function_result(p.oid) ~ 'timestamp without time zone')
   -- ⚠️ le funzioni che appartengono a un'ESTENSIONE non sono del progetto
   AND NOT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_proc'::regclass
                      AND d.objid = p.oid
                      AND d.deptype = 'e');

-- ============================================================
-- 1..2. Gli invarianti, con i NOMI nel messaggio di errore
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(colonna, ', ' ORDER BY colonna), '')
       FROM _colonne_ts WHERE data_type = 'timestamp without time zone'),
    '',
    '1) nessuna colonna timestamp without time zone nel progetto (V-3: un fuso solo)'
);

SELECT is(
    (SELECT coalesce(string_agg(firma, ', ' ORDER BY firma), '')
       FROM _funzioni_ts_nudo),
    '',
    '2) nessuna funzione del progetto con timestamp without time zone in firma o RETURNS'
);

-- ============================================================
-- 3. La lente vede: il test 1 non passa per sottrazione
-- ============================================================
SELECT cmp_ok(
    (SELECT count(*) FROM _colonne_ts WHERE data_type = 'timestamp with time zone'),
    '>', 600::bigint,
    '3) la lente vede le colonne timestamptz del progetto (erano 671 nel solo dominio il 20-09)'
);

-- ============================================================
-- 4. Il ritiro di 20260920-07 e' avvenuto davvero
-- ============================================================
SELECT hasnt_function(
    'script', 'fn_get_iva_override', ARRAY['text', 'integer'],
    '4) script.fn_get_iva_override ritirata (rotta dal 2025-10-06, zero chiamanti): 20260920-07'
);

SELECT * FROM finish();
ROLLBACK;
