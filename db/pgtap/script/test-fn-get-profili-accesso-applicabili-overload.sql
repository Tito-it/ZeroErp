-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_profili_accesso_applicabili - regressione
-- overload 1-arg (risolto con migration 20260421-01).
--
-- Contesto:
--   La migration 20260419-50 creava la fn con signature (integer).
--   La 20260420-11-02 aggiunge la 2-arg (integer, ruolo_applicativo
--   DEFAULT NULL) via CREATE OR REPLACE, che NON rimpiazza la 1-arg
--   perche' OR REPLACE agisce solo su stessa firma. Risultato:
--   coesistenza di due overload -> rischio "function name is not
--   unique" in scenari con coercion/EXECUTE.
--   La 20260421-01 droppa la 1-arg. Questo test blocca l'eventuale
--   re-introduzione accidentale della 1-arg + verifica che le
--   chiamate legacy 1-arg continuino a funzionare via DEFAULT NULL.
--
-- Indice test (1..5):
--    1. Esiste una sola signature di fn_get_profili_accesso_applicabili
--    2. La signature unica ha 2 argomenti con DEFAULT sul secondo
--    3. Chiamata 1-arg su auth_user orfano -> eseguibile, zero righe,
--       no errore "function not unique"
--    4. Chiamata 2-arg esplicita (NULL) equivalente alla 1-arg (count)
--    5. Chiamata 2-arg con ruolo specifico filtra correttamente
--       (CLIENTE_PORTALE su auth_user orfano -> zero righe)
--
-- BEGIN; + ROLLBACK finale.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- =========================================================
-- 1) Esiste una sola signature di fn_get_profili_accesso_applicabili
-- =========================================================
-- Post-drop 20260421-01 deve restare solo la 2-arg. Due signature
-- indicano regressione dell'overload.
SELECT is(
    (SELECT COUNT(*)::int
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname = 'fn_get_profili_accesso_applicabili'),
    1,
    '1. Una sola signature di fn_get_profili_accesso_applicabili in pg_proc'
);

-- =========================================================
-- 2) La signature ha 2 argomenti con DEFAULT sul secondo
-- =========================================================
-- Verifica che la signature unica sia la 2-arg canonica (non la
-- 1-arg ricomparsa per sbaglio).
-- ⚠️ Si confrontano gli OID dei tipi, non la firma RESA come stringa.
--   `pg_get_function_identity_arguments` qualifica il tipo con lo schema solo se
--   quello schema NON e' nel search_path: l'owner legge
--   «config.ruolo_applicativo», l'utente applicativo — che ha `config` nel
--   search_path — legge «ruolo_applicativo». Stessa funzione, due stringhe:
--   l'asserzione dipendeva dallo stato di sessione invece che dalla cosa da
--   verificare. Gli OID non hanno questo problema, e il letterale a destra e'
--   qualificato quindi risolve sempre allo stesso tipo.
--   ⚠️ `::oidvector` e non `oid[]`: proargtypes e' a base ZERO e un ARRAY a base
--   uno, e il confronto fra i due e' falso anche con gli stessi elementi.
--   La sotto-select resta scalare apposta: se riapparisse un overload, PostgreSQL
--   solleverebbe «more than one row» — che e' proprio cio' che il test presidia.
SELECT is(
    (SELECT p.proargtypes
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname = 'fn_get_profili_accesso_applicabili'),
    ARRAY['integer'::regtype::oid,
          'config.ruolo_applicativo'::regtype::oid]::oidvector,
    '2. Signature canonica: 2 arg (integer, config.ruolo_applicativo)'
);

-- =========================================================
-- 3) Chiamata 1-arg su auth_user orfano -> eseguibile
-- =========================================================
-- Creo un auth_user senza identita (orfano). La chiamata 1-arg deve
-- risolversi sulla 2-arg con DEFAULT NULL, ritornare 0 righe e NON
-- sollevare "function name is not unique".
CREATE TEMP TABLE _t_au_orfano AS
WITH ins AS (
    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_overload_1arg_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id AS auth_user_id
)
SELECT auth_user_id FROM ins;

SELECT is(
    (SELECT COUNT(*)::int
       FROM script.fn_get_profili_accesso_applicabili(
           (SELECT auth_user_id FROM _t_au_orfano)
       )),
    0,
    '3. Chiamata 1-arg legacy su auth_user orfano -> 0 righe (risolve 2-arg DEFAULT NULL)'
);

-- =========================================================
-- 4) Chiamata 2-arg esplicita (NULL) equivalente alla 1-arg
-- =========================================================
-- Il count di 1-arg e 2-arg-NULL deve essere identico: invariante di
-- backward compat dopo il drop della 1-arg standalone.
SELECT is(
    (SELECT COUNT(*)::int
       FROM script.fn_get_profili_accesso_applicabili(
           (SELECT auth_user_id FROM _t_au_orfano)
       )),
    (SELECT COUNT(*)::int
       FROM script.fn_get_profili_accesso_applicabili(
           (SELECT auth_user_id FROM _t_au_orfano),
           NULL::config.ruolo_applicativo
       )),
    '4. Equivalenza fn(x) == fn(x, NULL) - backward compat 1-arg'
);

-- =========================================================
-- 5) Chiamata 2-arg con ruolo specifico su auth_user orfano -> 0 righe
-- =========================================================
-- Verifica che il parametro p_ruolo_applicativo sia effettivamente
-- passabile (non solo il DEFAULT) e che filtri.
SELECT is(
    (SELECT COUNT(*)::int
       FROM script.fn_get_profili_accesso_applicabili(
           (SELECT auth_user_id FROM _t_au_orfano),
           'CLIENTE_PORTALE'::config.ruolo_applicativo
       )),
    0,
    '5. Chiamata 2-arg con p_ruolo_applicativo=CLIENTE_PORTALE su orfano -> 0 righe'
);

SELECT * FROM finish();
ROLLBACK;
