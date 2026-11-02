-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.processi e
--   dbops.coda_lavori_tipi, due cataloghi che a runtime NON scrive nessuno —
--   li popola il seed Liquibase, e il ruolo applicativo ha SELECT-only
--   (90_end/20260904-15). Verificato cercando gli scrittori, non dedotto.
--
-- Test: il guard di CLASSE in dbops.fn_accoda_lavoro
-- Brief: brief-db-processi-automatici-identita-e-perimetro §5.3 (fase 4)
--
-- Elenco test (plan 7):
--  1) coda_lavori_tipi ha la colonna processo_codice
--  2) la FK respinge un tipo che dichiara un processo inesistente
--  3) ⛔ un job di DOMINIO accodato come SISTEMA viene rifiutato
--  4) ⛔ e viene rifiutato anche se il default del tipo dice OPERATORE
--       (e' il caso che il CHECK di tabella non prende)
--  5) ✅ lo stesso job accodato come OPERATORE con scope passa
--  6) ✅ un job di MANUTENZIONE come SISTEMA passa: nessun perimetro da avere
--  7) i tipi seedati dichiarano tutti il loro processo
--
-- Scopo:
--  - provare il difetto A dell'analisi COSTRUENDOLO: il run_as_default e' un
--    suggerimento che p_run_as sovrascrive, e prima del 2026-09-04 un lavoro
--    di dominio poteva essere accodato come SISTEMA e girare senza perimetro;
--  - fissare che il guard NON e' un doppione del CHECK di tabella (test 4):
--    quello guarda la coerenza run_as/scope, questo la natura del lavoro;
--  - fissare che la manutenzione resta libera (test 6), altrimenti il guard
--    sarebbe una tassa su tutta la coda invece che una regola sul dominio.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1..2. La colonna e la sua FK
-- ============================================================
SELECT has_column('dbops', 'coda_lavori_tipi', 'processo_codice',
                  'coda_lavori_tipi ha la colonna processo_codice');

SELECT throws_ok(
    $$INSERT INTO dbops.coda_lavori_tipi
          (codice, handler_code, run_as_default, processo_codice)
      VALUES ('PGTAP-TIPO-ORFANO', 'pgtap_handler', 'SISTEMA',
              'PGTAP-PROCESSO-CHE-NON-ESISTE')$$,
    '23503',
    NULL,
    'la FK respinge un tipo che dichiara un processo inesistente'
);

-- ============================================================
-- Fixture: due processi (dominio e manutenzione) e i loro tipi di coda.
-- ⚠️ Il tipo di DOMINIO nasce con run_as_default = OPERATORE, cioe' gia'
--    "giusto": serve a provare che il guard non si accontenta del default,
--    perche' e' p_run_as a decidere davvero.
-- ============================================================
DO $fixture$
BEGIN
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento)
    VALUES (9501, 'PGTAP-CODA-DOMINIO',
            'processo di dominio con un tipo di coda', 'DOMINIO', 'CODA', 'PROGRAMMA'),
           (9502, 'PGTAP-CODA-MANUTENZIONE',
            'processo di manutenzione con un tipo di coda', 'MANUTENZIONE', 'CODA', 'PROGRAMMA');

    INSERT INTO dbops.coda_lavori_tipi
        (codice, handler_code, descrizione, run_as_default, processo_codice)
    VALUES ('PGTAP-TIPO-DOMINIO', 'pgtap_handler_dominio',
            'tipo di prova su processo di dominio', 'OPERATORE', 'PGTAP-CODA-DOMINIO'),
           ('PGTAP-TIPO-MANUTENZIONE', 'pgtap_handler_manut',
            'tipo di prova su processo di manutenzione', 'SISTEMA', 'PGTAP-CODA-MANUTENZIONE');
END
$fixture$;

-- ============================================================
-- 3..4. Il difetto A, costruito
-- ============================================================
-- ⛔ Prima del 2026-09-04 questo passava: `v_run_as := COALESCE(p_run_as,
--   v_tipo.run_as_default)` fa vincere il parametro, e il lavoro sarebbe
--   girato sul canale di sistema, senza perimetro.
SELECT throws_ok(
    $$SELECT dbops.fn_accoda_lavoro(
          p_job_type => 'PGTAP-TIPO-DOMINIO',
          p_run_as   => 'SISTEMA')$$,
    'P0001',
    NULL,
    'un job di DOMINIO accodato come SISTEMA viene rifiutato'
);

-- ⭐ E questo e' il punto che distingue il guard dal CHECK di tabella: il tipo
--   ha run_as_default = OPERATORE, quindi "sulla carta" e' a posto. Il CHECK
--   chk_coda_lavori_run_as_scope sarebbe soddisfatto (SISTEMA + scope NULL):
--   guarda la coerenza fra run_as e scope, non la NATURA del lavoro.
SELECT throws_ok(
    $$SELECT dbops.fn_accoda_lavoro(
          p_job_type => 'PGTAP-TIPO-DOMINIO',
          p_run_as   => 'SISTEMA',
          p_scope    => NULL)$$,
    'P0001',
    NULL,
    'il rifiuto vale anche col default del tipo a OPERATORE (il CHECK non basta)'
);

-- ============================================================
-- 5..6. Cio' che deve continuare a passare
-- ============================================================
SELECT lives_ok(
    $$SELECT dbops.fn_accoda_lavoro(
          p_job_type => 'PGTAP-TIPO-DOMINIO',
          p_run_as   => 'OPERATORE',
          p_scope    => '{"auth_user_id": 1, "username": "pgtap",
                          "identita_id": 1}'::jsonb)$$,
    'lo stesso job accodato come OPERATORE con scope passa'
);

-- ⭐ Il guard e' una regola sul DOMINIO, non una tassa su tutta la coda: un
--   lavoro di manutenzione non ha un perimetro da rispettare, e deve poter
--   girare come SISTEMA senza scope.
SELECT lives_ok(
    $$SELECT dbops.fn_accoda_lavoro(
          p_job_type => 'PGTAP-TIPO-MANUTENZIONE',
          p_run_as   => 'SISTEMA')$$,
    'un job di MANUTENZIONE come SISTEMA passa: nessun perimetro da avere'
);

-- ============================================================
-- 7. Il seed dichiara il processo per tutti i tipi
-- ============================================================
-- Senza, il NOT NULL del changeSet -42 non sarebbe applicabile, e il guard
-- di classe resterebbe muto sui tipi scoperti.
SELECT is_empty(
    $$SELECT codice FROM dbops.coda_lavori_tipi
       WHERE processo_codice IS NULL$$,
    'ogni tipo di coda dichiara il processo a cui appartiene'
);

SELECT * FROM finish();

ROLLBACK;
