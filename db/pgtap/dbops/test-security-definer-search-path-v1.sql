-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — test STRUTTURALE sul catalogo (pg_proc): nessuna
--   tabella sotto RLS viene letta, il contesto operatore non cambierebbe
--   nessuna risposta.
-- pgTAP test per Zero ERP
--
-- Postura di sicurezza delle SECURITY DEFINER: il `search_path`.
--   D5 (riga 3) e D6 di migliorie-generali-da-test-valutazione.md.
--   ChangeSet: 20260912-39..41 (provision-post).
--
-- Elenco test (plan 5):
--  1) ⛔ INVARIANTE: nessuna SECURITY DEFINER del progetto senza `search_path`
--  2) gemello «esiste»: la lente vede le DEFINER — il test 1 non e' muto
--  3) ⭐ le tre di `postgres` (dbops.fn_generate_tx_id,
--        fn_get_or_create_session_tx_id, fn_sync_functions_owner) pinnano
--        ESATTAMENTE pg_catalog, public, pg_temp
--  4) ⛔ DIVIETO (D6-bis, dal 2026-11-03): DEFINER con un path che NON elenca pg_temp
--  5) ⛔ DIVIETO (D6-bis, dal 2026-11-03): DEFINER con `public` PRIMA di pg_catalog
--
-- ⭐ PERCHE' UN INVARIANTE GENERALE E NON TRE NOMI. Fino al 2026-09-12 il
--   `search_path` delle DEFINER era asserito caso per caso (maintenance.fn_job_run_*,
--   due in vendite, una in script): un criterio che nasce quando un difetto ha
--   gia' morso. Le tre di postgres non avevano ancora morso, ed erano gia'
--   violate. Il test 1 guarda il CATALOGO: una DEFINER nuova senza pin esce
--   qui, non quando qualcuno se ne accorge.
--
-- ⚠️ PERCHE' LE ESTENSIONI SONO ESCLUSE. `public.dblink_connect_u` e' SECURITY
--   DEFINER senza search_path, ed e' di dblink: non e' codice del progetto, e
--   un CREATE OR REPLACE su una funzione di estensione non e' una cosa che si
--   fa. Si escludono per DIPENDENZA (pg_depend deptype 'e'), non per nome.
--
-- ⛔ I TEST 4 E 5 ERANO RUBINETTI, dal 2026-11-03 SONO DIVIETI. 18 DEFINER
--   non elencavano pg_temp il 2026-09-12 (17 dal 2026-10-05, 16 dal
--   2026-10-10) — quando non e' elencato PostgreSQL lo cerca per PRIMO per le
--   relazioni, che e' semantica e non stile. Vietarlo allora avrebbe fatto
--   nascere il file rosso; si e' tenuta una soglia che poteva solo calare, e
--   il 2026-11-03 le ultime 16 (e le 4 col path che comincia da public) sono
--   state sanate insieme (20261103-04, -05). Ora una DEFINER nuova che nasce
--   senza pg_temp in coda e' rossa, col suo nome nel messaggio.
--
-- ⚠️ IL PIN NON E' UNA FORMA SOLA, ed e' il motivo per cui il test 3 asserisce
--   la forma solo sulle tre di postgres: una DEFINER il cui percorso tocca
--   un'estensione DEVE avere `public` nel path (dblink, unaccent, geometry),
--   una che non ne tocca fa bene a non averlo. La forma si sceglie guardando
--   i CHIAMATI, non una funzione alla volta (memoria «una DEFINER col
--   search_path blindato accieca la INVOKER che chiama»).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- La lente: le SECURITY DEFINER del progetto, con il loro path
-- ============================================================
CREATE TEMP TABLE _definer ON COMMIT DROP AS
SELECT n.nspname,
       p.proname,
       n.nspname || '.' || p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' AS firma,
       (SELECT split_part(c, '=', 2)
          FROM unnest(p.proconfig) AS c
         WHERE c LIKE 'search_path=%') AS search_path
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE p.prosecdef
   AND n.nspname NOT IN ('pg_catalog', 'information_schema')
   -- ⚠️ le funzioni che appartengono a un'ESTENSIONE non sono del progetto
   AND NOT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_proc'::regclass
                      AND d.objid = p.oid
                      AND d.deptype = 'e');

-- ============================================================
-- 1..2. L'invariante, e la prova che la lente vede
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(firma, ', ' ORDER BY firma), '')
       FROM _definer WHERE search_path IS NULL),
    '',
    '1. ⛔ nessuna SECURITY DEFINER del progetto senza search_path (elenco = i colpevoli)'
);

SELECT cmp_ok(
    (SELECT count(*) FROM _definer), '>', 20::bigint,
    '2. la lente vede le DEFINER del progetto (erano 42 il 2026-09-12): il test 1 non e'' muto'
);

-- ============================================================
-- 3. Le tre di postgres: la forma esatta
-- ============================================================
SELECT is(
    (SELECT string_agg(proname || '=' || coalesce(search_path, '<nessuno>'), ' | ' ORDER BY proname)
       FROM _definer
      WHERE nspname = 'dbops'
        AND proname IN ('fn_generate_tx_id', 'fn_get_or_create_session_tx_id',
                        'fn_sync_functions_owner')),
    'fn_generate_tx_id=pg_catalog, public, pg_temp | '
    'fn_get_or_create_session_tx_id=pg_catalog, public, pg_temp | '
    'fn_sync_functions_owner=pg_catalog, public, pg_temp',
    '3. ⭐ le tre DEFINER di postgres pinnano pg_catalog, public, pg_temp (public: dblink vive li'')'
);

-- ============================================================
-- 4..5. I rubinetti di D6-bis
-- ============================================================
-- ⚠️ Soglie misurate il 2026-09-12 su dbdev. Possono solo CALARE.
--   Test 4: 18 -> 17 il 2026-10-05 (20261005-27). La DEFINER nuova
--   script.fn_get_testata_id_di_riga era nata senza pg_temp e aveva portato il
--   conto a 19: si e' sanata lei, con il gemello da cui aveva copiato la forma
--   (script.fn_get_stato_testata_documento), e la soglia e' scesa di uno.
--   Test 4: 17 -> 16 il 2026-10-10 (20261010-59): sanata
--   anagrafiche.fn_guard_albero_ba_gestore_globale, riscritta per D-5 di
--   brief-db-istanza-nasce-col-ba-residui.
--   Test 4: 16 -> 0 il 2026-11-03 (20261103-04): il rubinetto e' chiuso e
--   diventa un DIVIETO, con l'elenco dei colpevoli come il test 1.
SELECT is(
    (SELECT coalesce(string_agg(firma || ' [' || search_path || ']', ', ' ORDER BY firma), '')
       FROM _definer
      WHERE search_path IS NOT NULL
        AND search_path NOT LIKE '%pg_temp%'),
    '',
    '4. ⛔ nessuna DEFINER con un search_path che non elenca pg_temp: non elencato, PostgreSQL lo cerca PER PRIMO per le relazioni (D6-bis, chiuso il 2026-11-03)'
);

-- ⚠️ Test 5: 5 -> 4 il 2026-10-15 (20261015-03, provision-post): sanata
--   maintenance.fn_job_run_log_failure, riscritta per D-5 di
--   brief-db-ruoli-di-sistema. ⚠️ Vale DOPO il provision-post: e' li' che
--   quel changeSet si applica (la funzione e' di un superuser).
--   Test 5: 4 -> 0 il 2026-11-03 (20261103-04 e, per script.fn_log_error_only
--   che e' di postgres, 20261103-05 con la proprieta' presa in prestito): divieto.
SELECT is(
    (SELECT coalesce(string_agg(firma || ' [' || search_path || ']', ', ' ORDER BY firma), '')
       FROM _definer
      WHERE search_path LIKE 'public,%'),
    '',
    '5. ⛔ nessuna DEFINER con public PRIMA di pg_catalog nel path scritto: si scrive pg_catalog in testa (D6-bis, chiuso il 2026-11-03)'
);

SELECT * FROM finish();
ROLLBACK;
