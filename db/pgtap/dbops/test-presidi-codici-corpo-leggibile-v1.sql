-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — il file legge il catalogo di PostgreSQL (pg_proc) attraverso le viste
--   dbops dei codici, e chiama script.fn_get_contatti con il soggetto NULL, che rifiuta prima di
--   leggere un dato. Un contesto operatore non cambierebbe una riga del risultato.
-- pgtap-runner: owner
-- pgtap-runner-motivo: i test 3..8 CREANO uno schema di prova e funzioni sql (in transazione, poi
--   annullata), perche' un perimetro si prova costruendo i casi. E' DDL: il ruolo applicativo non
--   ne fa. Stesso criterio di dbops/test-punti-canale-campo-v1.
-- pgTAP test per Zero ERP
--
-- I presidi dei codici leggono ogni corpo leggibile, plpgsql e sql (Q15).
-- Brief: brief-db-revisione-dbops, giro 12 (§31).
--
-- Il perimetro e' il modello: una funzione LANGUAGE sql puo' sollevare un codice, nominare una
-- fn_check_*, costruire un bersaglio, come una plpgsql. Il caso che l'ha mostrato:
-- script.fn_get_contatti, sql, sollevava un codice obsoleto da una CTE che non girava mai.
--
-- Elenco test (plan 11):
--  1) dbops.fn_corpo_leggibile: plpgsql e sql si', c e internal no
--  2) dbops.fn_corpo_leggibile(NULL) e' falso, non NULL
--  3) ⭐ vw_codici_errore_da_dichiarare vede il codice di una funzione sql e di una sql BEGIN ATOMIC
--  4) ⭐ vw_punti_canale_campo legge il canale di quelle due chiamate
--  5) ⭐ vw_funzioni_check_codici risale da una sql BEGIN ATOMIC alla check sql e al suo codice
--  6) ⭐ vw_punti_primo_motivo vede il primo motivo sollevato a mano da una funzione sql
--  7) ⭐ vw_bersagli_non_dichiarati vede il tipo di un bersaglio costruito da una sql BEGIN ATOMIC
--     (prosrc vuoto: il prefiltro lo lascia passare)
--  8) vw_codici_errore_forme_condizione resta sul plpgsql, per decisione: i codici sql non ci sono
--  9) ⭐ script.fn_get_contatti(NULL) e' rifiutato con E_CONTATTI_SOGGETTO_OBBLIGATORIO
-- 10) ... e cosi' il suo chiamante script.fn_get_contatto_default(NULL)
-- 11) ⛔ nessuna chiamata diretta a fn_log_and_raise_error, in nessun corpo leggibile, solleva un
--     codice letterale fuori dalla grammatica E_ (la forma che la rinomina di agosto non aveva visto)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: il file non scrive dati di dominio, ma il preambolo e' uguale per tutti
--   (guardrail_pgtap_preambolo): un vincolo differito scatterebbe al COMMIT, che qui non arriva.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);


-- ============================================================
-- Il building block
-- ============================================================
SELECT is(
    (SELECT string_agg(l.lanname || '=' || dbops.fn_corpo_leggibile(l.oid)::text, ', ' ORDER BY l.lanname)
       FROM pg_language l WHERE l.lanname IN ('c', 'internal', 'plpgsql', 'sql')),
    'c=false, internal=false, plpgsql=true, sql=true',
    '1) fn_corpo_leggibile: plpgsql e sql si'', c e internal no');

SELECT is(dbops.fn_corpo_leggibile(NULL), false,
    '2) fn_corpo_leggibile(NULL) e'' falso');

-- ============================================================
-- I casi costruiti: uno schema di prova, funzioni sql
-- ============================================================
CREATE SCHEMA pgtap_giro12;

-- una sql col corpo testuale: solleva un codice, canale 'parametro'
CREATE FUNCTION pgtap_giro12.fn_solleva_sql(p_x integer) RETURNS void LANGUAGE sql AS $f$
  SELECT script.fn_log_and_raise_error('database', 'fn_solleva_sql', 'E_PGTAP_G12_SQL',
         jsonb_build_object('parametro', 'p_x'), NULL::uuid, VARIADIC ARRAY[]::text[])
   WHERE p_x IS NULL;
$f$;

-- una sql BEGIN ATOMIC (prosrc vuoto): solleva un codice, canale 'campo'
CREATE FUNCTION pgtap_giro12.fn_solleva_atomic(p_x integer) RETURNS void LANGUAGE sql
BEGIN ATOMIC
  SELECT script.fn_log_and_raise_error('database', 'fn_solleva_atomic', 'E_PGTAP_G12_ATOMIC',
         jsonb_build_object('campo', 'x'), NULL::uuid, VARIADIC ARRAY[]::text[])
   WHERE p_x IS NULL;
END;

-- una check scritta in sql, che nomina un motivo
CREATE FUNCTION pgtap_giro12.fn_check_prova(p_x integer) RETURNS jsonb LANGUAGE sql AS $f$
  SELECT CASE WHEN p_x IS NULL
              THEN jsonb_build_array(jsonb_build_object('codice', 'E_PGTAP_G12_MOTIVO'))
              ELSE jsonb_build_array() END;
$f$;

-- una sql BEGIN ATOMIC che nomina la check
CREATE FUNCTION pgtap_giro12.fn_usa_check_atomic(p_x integer) RETURNS boolean LANGUAGE sql
BEGIN ATOMIC
  SELECT jsonb_array_length(pgtap_giro12.fn_check_prova(p_x)) = 0;
END;

-- una sql che solleva a mano il primo motivo della check
CREATE FUNCTION pgtap_giro12.fn_primo_motivo_sql(p_x integer) RETURNS void LANGUAGE sql AS $f$
  SELECT script.fn_log_and_raise_error('database', 'fn_primo_motivo_sql',
         pgtap_giro12.fn_check_prova(p_x) -> 0 ->> 'codice', '{}'::jsonb, NULL::uuid,
         VARIADIC ARRAY[]::text[])
   WHERE jsonb_array_length(pgtap_giro12.fn_check_prova(p_x)) > 0;
$f$;

-- una sql BEGIN ATOMIC che costruisce un bersaglio verso un tipo che il catalogo non dichiara
CREATE FUNCTION pgtap_giro12.fn_bersaglio_atomic() RETURNS jsonb LANGUAGE sql
BEGIN ATOMIC
  SELECT jsonb_build_object('bersaglio', jsonb_build_object('tipo', 'PGTAP_G12_TIPO_ASSENTE', 'id', 1));
END;

SELECT is(
    (SELECT string_agg(v.codice || ' ' || v.funzioni, ', ' ORDER BY v.codice)
       FROM dbops.vw_codici_errore_da_dichiarare v WHERE v.codice LIKE 'E_PGTAP_G12_%'),
    'E_PGTAP_G12_ATOMIC pgtap_giro12.fn_solleva_atomic, E_PGTAP_G12_MOTIVO pgtap_giro12.fn_check_prova, E_PGTAP_G12_SQL pgtap_giro12.fn_solleva_sql',
    '3) vw_codici_errore_da_dichiarare vede i codici delle funzioni sql, BEGIN ATOMIC compresa');

SELECT is(
    (SELECT string_agg(v.codice || ' ' || v.via || ' ' || v.canale || ' ' || v.chiave, ', ' ORDER BY v.codice)
       FROM dbops.vw_punti_canale_campo v
      WHERE v.funzione IN ('pgtap_giro12.fn_solleva_sql', 'pgtap_giro12.fn_solleva_atomic')),
    'E_PGTAP_G12_ATOMIC DIRETTO IN_CHIAMATA campo, E_PGTAP_G12_SQL DIRETTO IN_CHIAMATA parametro',
    '4) vw_punti_canale_campo legge il canale delle chiamate sql');

SELECT is(
    (SELECT string_agg(v.check_schema || '.' || v.check_funzione || ' ' || v.codice, ', ')
       FROM dbops.vw_funzioni_check_codici v WHERE v.funzione = 'pgtap_giro12.fn_usa_check_atomic'),
    'pgtap_giro12.fn_check_prova E_PGTAP_G12_MOTIVO',
    '5) vw_funzioni_check_codici risale da una sql BEGIN ATOMIC alla check sql e al suo codice');

SELECT is(
    (SELECT string_agg(v.check_funzione || ' ' || v.codice, ', ')
       FROM dbops.vw_punti_primo_motivo v WHERE v.funzione = 'pgtap_giro12.fn_primo_motivo_sql'),
    'fn_check_prova E_PGTAP_G12_MOTIVO',
    '6) vw_punti_primo_motivo vede il primo motivo sollevato a mano da una funzione sql');

SELECT is(
    (SELECT v.motivo || ' ' || v.funzioni
       FROM dbops.vw_bersagli_non_dichiarati v WHERE v.tipo = 'PGTAP_G12_TIPO_ASSENTE'),
    'ASSENTE pgtap_giro12.fn_bersaglio_atomic',
    '7) vw_bersagli_non_dichiarati vede il bersaglio di una sql BEGIN ATOMIC');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_codici_errore_forme_condizione v WHERE v.codice LIKE 'E_PGTAP_G12_%'),
    '8) vw_codici_errore_forme_condizione resta sul plpgsql: i codici sql non ci sono');

-- ============================================================
-- script.fn_get_contatti: il soggetto obbligatorio lo e' davvero
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT * FROM script.fn_get_contatti(NULL::uuid)$$),
    'E_CONTATTI_SOGGETTO_OBBLIGATORIO',
    '9) fn_get_contatti(NULL) e'' rifiutato');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT * FROM script.fn_get_contatto_default(NULL::uuid)$$),
    'E_CONTATTI_SOGGETTO_OBBLIGATORIO',
    '10) fn_get_contatto_default(NULL) e'' rifiutato');

-- ============================================================
-- Il sistema: la grammatica del codice sollevato
-- ============================================================
SELECT is(
    (SELECT string_agg(DISTINCT n.nspname || '.' || p.proname || ' ' || m.m[1], ', ')
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
       CROSS JOIN LATERAL regexp_matches(dbops.fn_corpo_funzione(p.oid) COLLATE "C",
            'fn_log_and_raise_error\s*\(\s*''[^'']*''\s*,\s*[^,]+,\s*''([A-Za-z][A-Za-z0-9_]*)''', 'g') m(m)
      WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND dbops.fn_corpo_leggibile(p.prolang)
        AND (p.prosrc LIKE '%fn_log_and_raise_error%' OR p.prosqlbody IS NOT NULL)
        AND m.m[1] !~ '^E_[A-Z0-9_]+$'),
    NULL,
    '11) nessuna chiamata diretta solleva un codice letterale fuori dalla grammatica E_');

SELECT * FROM finish();
ROLLBACK;
