-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test:
--   - CHECK chk_profili_accesso_bindings_xor (esattamente 1 colonna NOT NULL)
--   - config.trgfn_profili_accesso_bindings_guard_coerenza (tipo profilo
--     coerente con tipo binding)
-- Riferimento: §4.3.4 + §4.3 guard coerenza WIP multi-face-auth.
--
-- Indice test (1..9):
--    1. Precondizione: unita_organizzativa disponibile
--    2. Setup: profilo test tipo REPARTO
--    3. Setup: profilo test tipo PORTALE
--    4. Guard (NON il CHECK): INSERT con 0 colonne -> throws P0001
--       ⚠️ i trigger BEFORE ROW girano prima dei CHECK: qui intercetta il guard
--    5. CHECK xor: INSERT con 2 colonne (uo + ruolo) -> throws 23514
--       (unica asserzione che raggiunge davvero chk_profili_accesso_bindings_xor)
--    6. Guard: REPARTO + unita_organizzativa_id -> lives_ok
--    7. Guard: REPARTO + ruolo_applicativo -> throws (tipo binding incoerente)
--    8. Guard: PORTALE + ruolo_applicativo -> lives_ok
--    9. Guard: PORTALE + unita_organizzativa_id -> throws
--
-- BEGIN; + rollback implicito a fine file.
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

SELECT plan(9);

-- =========================================================
-- 1) Setup: 2 unita_organizzative dedicate al test
-- =========================================================
-- La migrazione §4.3.5 ha gia' creato bindings REPARTO per tutte le UO
-- esistenti con permessi configurati: riusare quelle UO viola l'indice
-- parziale UNIQUE uq_profili_accesso_bindings_uo. Creo UO dedicate con
-- codice univoco (md5 clock_timestamp). Rollback implicito a fine file.
CREATE TEMP TABLE _t_uo AS
WITH ins AS (
    INSERT INTO config.unita_organizzative (
        codice, codice_interno, descrizione, attivo
    )
    VALUES
        ('_PGTAP_UO_1_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
         '_PGTAP_CI_1_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
         'UO test pgTAP bindings guard 1', true),
        ('_PGTAP_UO_2_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
         '_PGTAP_CI_2_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
         'UO test pgTAP bindings guard 2', true)
    RETURNING id
)
SELECT id AS uo_id FROM ins;

SELECT ok(
    (SELECT count(*) FROM _t_uo) = 2,
    '1. Setup: 2 unita_organizzative dedicate al test create'
);

-- =========================================================
-- 2) Setup: profilo test di tipo REPARTO
-- =========================================================
-- Uso un codice univoco con md5 per non collidere con profili esistenti
-- (la migrazione §4.3.5 ha gia' creato profili REPARTO_*).
CREATE TEMP TABLE _t_profilo_rep AS
WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES (
        'REPARTO',
        '_PGTAP_REP_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
        'Profilo REPARTO di test pgTAP (guard bindings)',
        true
    )
    RETURNING id
)
SELECT id AS profilo_id FROM ins;

SELECT ok(
    (SELECT profilo_id FROM _t_profilo_rep) IS NOT NULL,
    '2. Setup: profilo REPARTO di test creato'
);

-- =========================================================
-- 3) Setup: profilo test di tipo PORTALE
-- =========================================================
CREATE TEMP TABLE _t_profilo_por AS
WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES (
        'PORTALE',
        '_PGTAP_POR_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
        'Profilo PORTALE di test pgTAP (guard bindings)',
        true
    )
    RETURNING id
)
SELECT id AS profilo_id FROM ins;

SELECT ok(
    (SELECT profilo_id FROM _t_profilo_por) IS NOT NULL,
    '3. Setup: profilo PORTALE di test creato'
);

-- =========================================================
-- 4) CHECK xor: 0 colonne valorizzate -> throws
-- =========================================================
SELECT throws_ok(
    format($sql$
        INSERT INTO config.profili_accesso_bindings
            (profilo_accesso_id, unita_organizzativa_id, identita_digitale_id, ruolo_applicativo)
        VALUES (%s, NULL, NULL, NULL)
    $sql$,
    (SELECT profilo_id FROM _t_profilo_rep)),
    -- ⚠️ QUESTA ASSERZIONE NON COLLAUDA IL CHECK, e non lo ha mai fatto: il
    -- nome che portava era sbagliato. In PostgreSQL i trigger BEFORE ROW girano
    -- PRIMA dei vincoli CHECK, quindi con zero colonne valorizzate su un profilo
    -- REPARTO e' il guard a intercettare (manca unita_organizzativa_id), e
    -- `chk_profili_accesso_bindings_xor` non viene mai raggiunto. Misurato:
    -- SQLSTATE P0001, non 23514. Chi collauda davvero il CHECK e' l'asserzione 5.
    -- Con `NULL` come atteso non si vedeva: prima del fix qui arrivava 22023,
    -- il crash di format(), e passava lo stesso.
    -- Brief: brief-db-pgtap-runner-rls-baseline §13.
    'P0001', NULL,
    '4. Guard (non il CHECK): 0 colonne valorizzate -> throws E_PROFILO_ACCESSO_BINDING_INCOERENTE'
);

-- =========================================================
-- 5) CHECK xor: 2 colonne valorizzate (uo + ruolo) -> throws
-- =========================================================
SELECT throws_ok(
    format($sql$
        INSERT INTO config.profili_accesso_bindings
            (profilo_accesso_id, unita_organizzativa_id, identita_digitale_id, ruolo_applicativo)
        VALUES (%s, %s, NULL, 'CLIENTE_PORTALE')
    $sql$,
    (SELECT profilo_id FROM _t_profilo_rep),
    (SELECT uo_id FROM _t_uo ORDER BY uo_id LIMIT 1)),
    -- '23514' = violazione di CHECK. Questa e' l'UNICA asserzione che raggiunge
    -- davvero `chk_profili_accesso_bindings_xor`, e il motivo e' preciso: con
    -- unita_organizzativa_id valorizzato il guard REPARTO e' soddisfatto e lascia
    -- passare, cosi' il CHECK sull'xor puo' finalmente scattare. Misurato.
    '23514', NULL,
    '5. CHECK xor: 2 colonne valorizzate -> throws (chk_profili_accesso_bindings_xor)'
);

-- =========================================================
-- 6) Guard: REPARTO + unita_organizzativa_id -> lives_ok
-- =========================================================
SELECT lives_ok(
    format($sql$
        INSERT INTO config.profili_accesso_bindings
            (profilo_accesso_id, unita_organizzativa_id, identita_digitale_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, NULL, NULL, true)
    $sql$,
    (SELECT profilo_id FROM _t_profilo_rep),
    (SELECT uo_id FROM _t_uo LIMIT 1)),
    '6. Guard: REPARTO + unita_organizzativa_id -> INSERT ok'
);

-- =========================================================
-- 7) Guard: REPARTO + ruolo_applicativo -> throws (tipo binding incoerente)
-- =========================================================
SELECT throws_ok(
    format($sql$
        INSERT INTO config.profili_accesso_bindings
            (profilo_accesso_id, unita_organizzativa_id, identita_digitale_id, ruolo_applicativo, attivo)
        VALUES (%s, NULL, NULL, 'CLIENTE_PORTALE', true)
    $sql$,
    (SELECT profilo_id FROM _t_profilo_rep)),
    -- ⚠️ 'P0001' e non NULL: e' lo SQLSTATE con cui script.fn_log_and_raise_error
    -- solleva OGNI errore di dominio. Con NULL questa asserzione chiedeva solo
    -- «solleva qualcosa», e per mesi si e' accontentata del crash interno
    -- «numero di argomenti non sufficiente per format()» — il guard non e' MAI
    -- arrivato a dire la sua ragione, e il test restava verde.
    -- Corretto insieme al changeSet 20260806-12.
    -- Brief: brief-db-pgtap-runner-rls-baseline §13.
    'P0001', NULL,
    '7. Guard: REPARTO + ruolo_applicativo -> throws (E_PROFILO_ACCESSO_BINDING_INCOERENTE)'
);

-- =========================================================
-- 8) Guard: PORTALE + ruolo_applicativo -> lives_ok
-- =========================================================
SELECT lives_ok(
    format($sql$
        INSERT INTO config.profili_accesso_bindings
            (profilo_accesso_id, unita_organizzativa_id, identita_digitale_id, ruolo_applicativo, attivo)
        VALUES (%s, NULL, NULL, 'API_CLIENT', true)
    $sql$,
    (SELECT profilo_id FROM _t_profilo_por)),
    '8. Guard: PORTALE + ruolo_applicativo -> INSERT ok'
);

-- =========================================================
-- 9) Guard: PORTALE + unita_organizzativa_id -> throws
-- =========================================================
-- Devo usare una uo diversa per evitare conflitti UNIQUE con test 6.
-- Se non ci sono 2 uo disponibili, riuso la stessa (test 6 ha gia' creato
-- il binding, quindi UNIQUE non-attivo qui; ma il guard sparera' prima
-- del conflitto UNIQUE, quindi OK).
SELECT throws_ok(
    format($sql$
        INSERT INTO config.profili_accesso_bindings
            (profilo_accesso_id, unita_organizzativa_id, identita_digitale_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, NULL, NULL, true)
    $sql$,
    (SELECT profilo_id FROM _t_profilo_por),
    (SELECT uo_id FROM _t_uo ORDER BY uo_id DESC LIMIT 1)),
    -- 'P0001' = errore di dominio, non un crash interno. Vedi la nota all'asserzione 7.
    'P0001', NULL,
    '9. Guard: PORTALE + unita_organizzativa_id -> throws (tipo binding incoerente)'
);

SELECT * FROM finish();
