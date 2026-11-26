-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_utente_di_sessione, l'utente della richiesta letto da una
--   sede sola, e il presidio che tiene la lettura in quella sede.
--   Brief: brief-db-revisione-ui (§3.6-sexies, giro 8; Q60 (a)).
--
-- ⭐ Il contesto dell'operatore e' lo sfondo: i casi cambiano
--   app.current_user_id con set_config(..., true) e lo leggono subito.
-- ⭐ Il presidio legge il catalogo (pg_proc, pg_views): conta i lettori
--   «cattivi», quelli che leggono la GUC da se', e li nomina. Le esenzioni
--   sono un elenco chiuso, ciascuna col motivo; un'esenzione che non legge
--   piu' la GUC (o non esiste) e' rossa anche lei, cosi' l'elenco non resta
--   largo dopo che il debito e' chiuso.
--
-- Elenco test (plan 17):
--   La forma
--    1) script.fn_utente_di_sessione(text) esiste e risponde integer
--    2) STABLE, INVOKER
--   Le risposte
--    3) GUC vuota: NULL
--    4) un id: l'intero
--    5) il massimo di integer: l'intero
--   I valori rifiutati, tutti con E_SCRIPT_CHIAMATA_NON_VALIDA
--    6) non numerico
--    7) zero
--    8) zeri in testa
--    9) oltre il massimo di integer
--   10) segno
--   11) spazio
--   12) la frase nomina la funzione che legge (p_chi)
--   13) ... e senza p_chi il BB stesso
--   Il presidio
--   14) ⭐ nessuna funzione legge app.current_user_id da se', fuori dall'elenco
--       chiuso delle esenzioni
--   15) ⭐ nessuna vista legge app.current_user_id da se'
--   16) ogni esenzione esiste e legge ancora la GUC
--   17) ⭐ nessuna policy RLS legge app.current_user_id da se' (giro 8b)
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Fixture
-- ============================================================
-- Il messaggio dell'errore sollevato da un'istruzione, o NULL se non solleva.
-- text: l'istruzione da eseguire e il messaggio, non il riflesso di una colonna
CREATE FUNCTION pg_temp.messaggio(p_sql text)
  RETURNS text LANGUAGE plpgsql AS $f$
BEGIN
  EXECUTE p_sql;
  RETURN NULL;
EXCEPTION WHEN OTHERS THEN
  RETURN SQLERRM;
END
$f$;

-- Le esenzioni: chi legge app.current_user_id senza leggerlo come id
--   dell'utente. Elenco chiuso. (magazzino era esente fino a 20261123-26,
--   dbops.fn_storico_arma_scope fino a 20261123-27: tutti e due leggono dal BB.)
CREATE TEMP TABLE _esenti (oggetto text PRIMARY KEY, motivo text NOT NULL);
INSERT INTO _esenti VALUES
  ('script.fn_utente_di_sessione',
   'il BB: la sede della lettura'),
  ('anagrafiche.fn_provisiona_dati_di_sviluppo',
   'salva e ripristina il testo della GUC, non lo legge come id'),
  ('dbops.fn_pgtap_articolo_correggi_struttura',
   'salva e ripristina il testo della GUC, non lo legge come id');

-- I lettori della GUC sul catalogo: funzioni e procedure, dal testo intero
--   (pg_get_functiondef: anche i corpi BEGIN ATOMIC, che prosrc non ha) senza
--   i commenti di riga (i guard di script citano la lettura nell'esempio
--   d'uso, e non la eseguono). Nome qualificato a mano: regprocedure dipende
--   dal search_path.
CREATE TEMP TABLE _lettori AS
SELECT DISTINCT n.nspname || '.' || p.proname AS oggetto
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
 WHERE p.prokind IN ('f', 'p')
   AND n.nspname NOT IN ('pg_catalog', 'information_schema')
   AND n.nspname NOT LIKE 'pg\_temp\_%'
   AND regexp_replace(pg_catalog.pg_get_functiondef(p.oid), '--[^\n]*', '', 'g')
         ~ 'current_setting\(\s*''app\.current_user_id''';

-- ============================================================
-- 1-2) La forma
-- ============================================================
SELECT function_returns('script', 'fn_utente_di_sessione', ARRAY['text'], 'integer',
    '1) script.fn_utente_di_sessione(text) risponde integer');
SELECT is((SELECT p.provolatile::text || '|' || p.prosecdef::text
             FROM pg_catalog.pg_proc p
            WHERE p.oid = 'script.fn_utente_di_sessione(text)'::regprocedure),
    's|false',
    '2) STABLE, INVOKER');

-- ============================================================
-- 3-5) Le risposte
-- ============================================================
SELECT set_config('app.current_user_id', '', true);
SELECT is(script.fn_utente_di_sessione('pgtap'), NULL::integer,
    '3) GUC vuota: NULL');

SELECT set_config('app.current_user_id', '42', true);
SELECT is(script.fn_utente_di_sessione('pgtap'), 42,
    '4) un id: l''intero');

SELECT set_config('app.current_user_id', '2147483647', true);
SELECT is(script.fn_utente_di_sessione('pgtap'), 2147483647,
    '5) il massimo di integer: l''intero');

-- ============================================================
-- 6-13) I valori rifiutati
-- ============================================================
SELECT set_config('app.current_user_id', 'non-un-id', true);
SELECT is(dbops.fn_pgtap_codice_errore($$ SELECT script.fn_utente_di_sessione('pgtap') $$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA', '6) non numerico: E_SCRIPT_CHIAMATA_NON_VALIDA, non il 22P02');

SELECT set_config('app.current_user_id', '0', true);
SELECT is(dbops.fn_pgtap_codice_errore($$ SELECT script.fn_utente_di_sessione('pgtap') $$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA', '7) zero: nessun utente ha id 0');

SELECT set_config('app.current_user_id', '042', true);
SELECT is(dbops.fn_pgtap_codice_errore($$ SELECT script.fn_utente_di_sessione('pgtap') $$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA', '8) zeri in testa');

SELECT set_config('app.current_user_id', '2147483648', true);
SELECT is(dbops.fn_pgtap_codice_errore($$ SELECT script.fn_utente_di_sessione('pgtap') $$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA', '9) oltre il massimo di integer');

SELECT set_config('app.current_user_id', '-5', true);
SELECT is(dbops.fn_pgtap_codice_errore($$ SELECT script.fn_utente_di_sessione('pgtap') $$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA', '10) segno');

SELECT set_config('app.current_user_id', ' 42', true);
SELECT is(dbops.fn_pgtap_codice_errore($$ SELECT script.fn_utente_di_sessione('pgtap') $$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA', '11) spazio');

SELECT set_config('app.current_user_id', 'non-un-id', true);
SELECT ok(pg_temp.messaggio($$ SELECT script.fn_utente_di_sessione('pgtap.chi_legge') $$)
            LIKE '%pgtap.chi_legge%',
    '12) la frase nomina la funzione che legge (p_chi)');
SELECT ok(pg_temp.messaggio($$ SELECT script.fn_utente_di_sessione() $$)
            LIKE '%script.fn_utente_di_sessione%',
    '13) ... e senza p_chi il BB stesso');

-- ============================================================
-- 14-16) Il presidio
-- ============================================================
SELECT is((SELECT string_agg(l.oggetto, ', ' ORDER BY l.oggetto)
             FROM _lettori l
            WHERE NOT EXISTS (SELECT 1 FROM _esenti e WHERE e.oggetto = l.oggetto)),
    NULL,
    '14) ⭐ nessuna funzione legge app.current_user_id da se'': passa da script.fn_utente_di_sessione');

SELECT is((SELECT string_agg(v.schemaname || '.' || v.viewname, ', ' ORDER BY 1)
             FROM pg_catalog.pg_views v
            WHERE v.schemaname NOT IN ('pg_catalog', 'information_schema')
              AND v.definition ~ 'current_setting\(\s*''app\.current_user_id'''),
    NULL,
    '15) ⭐ nessuna vista legge app.current_user_id da se''');

SELECT is((SELECT string_agg(e.oggetto, ', ' ORDER BY e.oggetto)
             FROM _esenti e
            WHERE NOT EXISTS (SELECT 1 FROM _lettori l WHERE l.oggetto = e.oggetto)),
    NULL,
    '16) ogni esenzione esiste e legge ancora la GUC: l''elenco non resta largo');

-- Le policy dal catalogo (pg_policy), con le espressioni deparsate: nessuna
--   esenzione. Una policy nuova passa l'utente a script.fn_utente_di_sessione.
SELECT is((SELECT string_agg(n.nspname || '.' || c.relname || '.' || p.polname, ', ' ORDER BY 1)
             FROM pg_catalog.pg_policy p
             JOIN pg_catalog.pg_class c ON c.oid = p.polrelid
             JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE coalesce(pg_catalog.pg_get_expr(p.polqual, p.polrelid), '') || ' '
                  || coalesce(pg_catalog.pg_get_expr(p.polwithcheck, p.polrelid), '')
                  ~ 'current_setting\(\s*''app\.current_user_id'''),
    NULL,
    '17) ⭐ nessuna policy RLS legge app.current_user_id da se'': passa da script.fn_utente_di_sessione');

SELECT * FROM finish();
ROLLBACK;
