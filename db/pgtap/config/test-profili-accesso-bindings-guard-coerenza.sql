-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
--    4. CHECK xor: INSERT con 0 colonne -> throws
--    5. CHECK xor: INSERT con 2 colonne (uo + ruolo) -> throws
--    6. Guard: REPARTO + unita_organizzativa_id -> lives_ok
--    7. Guard: REPARTO + ruolo_applicativo -> throws (tipo binding incoerente)
--    8. Guard: PORTALE + ruolo_applicativo -> lives_ok
--    9. Guard: PORTALE + unita_organizzativa_id -> throws
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

BEGIN;
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
    NULL, NULL,
    '4. CHECK xor: 0 colonne valorizzate -> throws (chk_profili_accesso_bindings_xor)'
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
    (SELECT uo_id FROM _t_uo LIMIT 1)),
    NULL, NULL,
    '5. CHECK xor: 2 colonne valorizzate -> throws'
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
    NULL, NULL,
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
    NULL, NULL,
    '9. Guard: PORTALE + unita_organizzativa_id -> throws (tipo binding incoerente)'
);

SELECT * FROM finish();
