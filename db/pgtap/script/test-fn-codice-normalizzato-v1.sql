-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- script.fn_codice_normalizzato(text) (20261104-32): la forma di un codice
-- dell'operatore, in un posto solo. Richiesta BE brief-be-codice-maiuscolo §6,
-- decisioni Tid 2026-11-04.
--
-- Elenco test (plan 12):
--   1)  la funzione esiste
--   2)  forma: LANGUAGE sql, IMMUTABLE, STRICT, PARALLEL SAFE, INVOKER
--   3)  spazi ai lati e minuscole: ' vite-m8 ' -> 'VITE-M8'
--   4)  ⭐ mappatura Unicode completa: 'straße' -> 'STRASSE' (la collation del
--       database, libc, darebbe 'STRAßE')
--   5)  legatura: 'ﬁne' -> 'FINE'
--   6)  NULL resta NULL (STRICT)
--   7)  stringa vuota resta vuota
--   8)  idempotente: normalizzare un codice normalizzato non lo cambia
--   9)  ⭐ PRESIDIO: le funzioni che cercano o scrivono un codice del
--       perimetro, censite il 2026-11-04, chiamano il BB
--  10)  ⭐ PRESIDIO: nessun'altra funzione ricopia upper(btrim()) sul codice
--  11)  il trigger CODICE_MAIUSCOLO non porta piu' la formula
--  12)  catalogo.ix_uom_tipi_codice_upper e' ritirato (D-3, 20261104-44)
--
-- Scopo:
--  - i valori si provano su letterali COSTRUITI, non sui codici che ci sono;
--  - 9 e 10 presidiano la regola del 2: la sede e' una, le copie sono
--    ritirate. Il corpo si legge senza commenti (la prosa che spiega la
--    formula non e' una copia). ⚠️ Il 9 e' un elenco chiuso: una funzione
--    nuova che cerca per codice si aggiunge qui.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

-- ============================================================
-- La funzione
-- ============================================================
SELECT has_function('script', 'fn_codice_normalizzato', ARRAY['text'],
    '1) script.fn_codice_normalizzato(text) esiste');

SELECT is(
    (SELECT format('%s|%s|%s|%s|%s', l.lanname, p.provolatile, p.proisstrict, p.proparallel, p.prosecdef)
       FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_language l ON l.oid = p.prolang
      WHERE p.oid = 'script.fn_codice_normalizzato(text)'::regprocedure),
    'sql|i|t|s|f',   -- format('%s', boolean) scrive t/f
    '2) LANGUAGE sql, IMMUTABLE, STRICT, PARALLEL SAFE, SECURITY INVOKER');

SELECT is(script.fn_codice_normalizzato(' vite-m8 '), 'VITE-M8',
    '3) senza spazi ai lati, in maiuscolo');

SELECT is(script.fn_codice_normalizzato('straße'), 'STRASSE',
    '4) mappatura Unicode completa: la ß diventa SS');

SELECT is(script.fn_codice_normalizzato('ﬁne'), 'FINE',
    '5) mappatura Unicode completa: la legatura diventa due lettere');

SELECT ok(script.fn_codice_normalizzato(NULL) IS NULL,
    '6) NULL resta NULL');

SELECT is(script.fn_codice_normalizzato('   '), '',
    '7) solo spazi: stringa vuota');

SELECT is(script.fn_codice_normalizzato(script.fn_codice_normalizzato(' Straße-ﬁ ')),
          script.fn_codice_normalizzato(' Straße-ﬁ '),
    '8) idempotente');

-- ============================================================
-- ⭐ I presidi della sede unica
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(f ORDER BY f), ARRAY[]::text[])
       FROM unnest(ARRAY[
              'script.trgfn_codice_maiuscolo()',
              'anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma()',
              'config.fn_scrivi_profilo_accesso(config.tipo_profilo_accesso,character varying,text,jsonb,jsonb,jsonb)',
              'script.fn_crea_utente_tecnico(text,character varying,character varying)',
              'script.fn_riattiva_utente_tecnico(text,character varying)',
              'config.fn_resolve_email_template(character varying,integer,integer,character varying)',
              'vendite.fn_canone_periodi(date,date,character varying,smallint,character varying,date,date)',
              'dbops.fn_pgtap_crea_ddt(bigint,bigint,character varying,bigint,bigint,date)',
              'dbops.fn_pgtap_crea_ddt_da_ordine(text,character varying,bigint,numeric,numeric,uuid,character varying,bigint,numeric,jsonb,date,character varying,date,jsonb)',
              'dbops.fn_pgtap_crea_ddt_riconsegna(bigint,character varying,bigint,numeric,date,character varying)'
            ]) AS f
      WHERE pg_temp.corpo(f::regprocedure) !~ 'script\.fn_codice_normalizzato\s*\('),
    ARRAY[]::text[],
    '9) le funzioni che cercano o scrivono un codice del perimetro chiamano script.fn_codice_normalizzato');

SELECT is(
    (SELECT COALESCE(array_agg(n.nspname || '.' || p.proname ORDER BY 1), ARRAY[]::text[])
       FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND p.prolang = (SELECT l.oid FROM pg_catalog.pg_language l WHERE l.lanname = 'plpgsql')
        AND p.oid <> 'script.fn_codice_normalizzato(text)'::regprocedure
        AND pg_temp.corpo(p.oid::regprocedure)
            ~* 'upper\s*\(\s*btrim\s*\(\s*(coalesce\s*\(\s*)?(new\.)?codice\M'),
    ARRAY[]::text[],
    '10) nessuna funzione plpgsql ricopia upper(btrim(codice)): la forma sta nel BB');

SELECT ok(
    pg_temp.corpo('script.trgfn_codice_maiuscolo()'::regprocedure) !~* 'upper\s*\(',
    '11) il trigger CODICE_MAIUSCOLO non porta piu'' la formula');

SELECT hasnt_index('catalogo', 'uom_tipi', 'ix_uom_tipi_codice_upper',
    '12) catalogo.ix_uom_tipi_codice_upper e'' ritirato: il codice si salva normalizzato');

SELECT * FROM finish();
ROLLBACK;
