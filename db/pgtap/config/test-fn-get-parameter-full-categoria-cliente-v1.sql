-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Step 1.2 — nuovo overload script.fn_get_parameter_full a 7 parametri
--       con livello categoria_cliente nella cascata.
--       Migration: 20260515-08
--
-- Cascata testata: user -> categoria_cliente -> group -> emittente
--                  -> function -> default
-- ⚠️ Dal 2026-11-09 (brief-db-revisione-dbops, giro 13, Q10) il livello «sessione»
--   e' uscito dal modello: niente colonna session_key, niente p_session_key. I test
--   4 e 5 che lo provavano ora provano emittente su function e che il livello
--   non c'e' piu'.
--
-- Indice test (1..9):
--   1) user vince su tutto (user + categoria + group + emittente presenti)
--   2) categoria_cliente vince su group (CASO CHIAVE del refactor)
--   3) group vince su emittente
--   4) emittente vince su function
--   5) il livello sessione non c'e' piu': ne' la colonna ne' il parametro della firma
--   6) function vince su default
--   7) fallback a default (nessun override)
--   8) p_categoria_cliente_id=NULL skippa il livello (cade su group)
--   9) parametro inesistente solleva ERRORE_PARAMETRI_TABELLA (P0001)
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

-- ============================================================
-- Setup: parametro di test + fixtures dai dati esistenti
-- ============================================================

-- Parametro dedicato al test.
-- id calcolato come MAX(id)+1000 per evitare collisioni con la sequenza
-- (che potrebbe non essere allineata con i dati seed).
-- 2026-10-25 (brief-db-parametri-senza-override): config.parameters.ammette_override
-- e' NOT NULL senza DEFAULT, un parametro dichiara la sua famiglia.
-- 2026-10-31 (brief-db-liste-datatable-grezze-secondo-giro, D-5): idem tipo_valore.
INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
SELECT MAX(id) + 1000,
       'TEST_FN_CASCATA_CAT_CLI_20260515',
       'LIVELLO_DEFAULT',
       'Parametro temporaneo per test cascata categoria_cliente',
       true,
       'TESTO'
  FROM config.parameters;

-- Raccoglie id delle entita' necessarie dalla fixture esistente.
CREATE TEMP TABLE tmp_cascata_ctx AS
SELECT
    (SELECT id FROM config.parameters
      WHERE code = 'TEST_FN_CASCATA_CAT_CLI_20260515')           AS param_id,
    (SELECT id FROM django.auth_user   ORDER BY id LIMIT 1)      AS user_id,
    (SELECT id FROM django.auth_group  ORDER BY id LIMIT 1)      AS group_id,
    (SELECT id FROM anagrafiche.emittenti_fiscali
      WHERE attivo = true ORDER BY id LIMIT 1)                   AS emittente_id,
    (SELECT id FROM anagrafiche.categorie_clienti
      WHERE attivo = true ORDER BY id LIMIT 1)                   AS categoria_id;

-- Inserisce un override per ogni livello della cascata.
-- La UNIQUE v4 su (parameter_id, emittente, user, group, categoria, session, function)
-- e' rispettata: ogni riga ha esattamente UNA dimensione valorizzata.
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_user_id)
SELECT param_id, 'LIVELLO_USER', user_id FROM tmp_cascata_ctx;

INSERT INTO config.parameter_overrides (parameter_id, overridden_value, categoria_cliente_id)
SELECT param_id, 'LIVELLO_CATEGORIA', categoria_id FROM tmp_cascata_ctx;

-- Group level: solo se esiste almeno un gruppo Django (tabella potrebbe essere vuota).
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_group_id)
SELECT param_id, 'LIVELLO_GROUP', group_id FROM tmp_cascata_ctx
 WHERE group_id IS NOT NULL;

INSERT INTO config.parameter_overrides (parameter_id, overridden_value, emittente_fiscale_id)
SELECT param_id, 'LIVELLO_EMITTENTE', emittente_id FROM tmp_cascata_ctx;

INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
VALUES (
    (SELECT param_id FROM tmp_cascata_ctx),
    'LIVELLO_FUNCTION',
    'test_function_cascata_20260515'
);

-- ============================================================
-- 1) user vince su tutto
-- ============================================================
SELECT is(
    script.fn_get_parameter_full(
        'TEST_FN_CASCATA_CAT_CLI_20260515',
        p_django_user_id       => (SELECT user_id     FROM tmp_cascata_ctx),
        p_categoria_cliente_id => (SELECT categoria_id FROM tmp_cascata_ctx),
        p_group_ids            => ARRAY[(SELECT group_id FROM tmp_cascata_ctx)],
        p_emittente_fiscale_id => (SELECT emittente_id FROM tmp_cascata_ctx)
    ),
    'LIVELLO_USER',
    '1) user vince su categoria + group + emittente'
);

-- ============================================================
-- 2) categoria_cliente vince su group (CASO CHIAVE del refactor)
-- ============================================================
SELECT is(
    script.fn_get_parameter_full(
        'TEST_FN_CASCATA_CAT_CLI_20260515',
        p_categoria_cliente_id => (SELECT categoria_id FROM tmp_cascata_ctx),
        p_group_ids            => ARRAY[(SELECT group_id FROM tmp_cascata_ctx)],
        p_emittente_fiscale_id => (SELECT emittente_id FROM tmp_cascata_ctx)
    ),
    'LIVELLO_CATEGORIA',
    '2) categoria_cliente vince su group e emittente (nessun user override)'
);

-- ============================================================
-- 3) group vince su emittente
-- ============================================================
SELECT CASE
    WHEN (SELECT group_id FROM tmp_cascata_ctx) IS NULL
    THEN skip('3) Nessun gruppo Django disponibile — test saltato')
    ELSE is(
        script.fn_get_parameter_full(
            'TEST_FN_CASCATA_CAT_CLI_20260515',
            p_group_ids            => ARRAY[(SELECT group_id FROM tmp_cascata_ctx)],
            p_emittente_fiscale_id => (SELECT emittente_id FROM tmp_cascata_ctx),
            p_categoria_cliente_id => NULL
        ),
        'LIVELLO_GROUP',
        '3) group vince su emittente (nessun user, nessuna categoria)'
    )
END;

-- ============================================================
-- 4) emittente vince su function
-- ============================================================
SELECT is(
    script.fn_get_parameter_full(
        'TEST_FN_CASCATA_CAT_CLI_20260515',
        p_emittente_fiscale_id => (SELECT emittente_id FROM tmp_cascata_ctx),
        p_function_name        => 'test_function_cascata_20260515',
        p_categoria_cliente_id => NULL
    ),
    'LIVELLO_EMITTENTE',
    '4) emittente vince su function (nessun user/categoria/group)'
);

-- ============================================================
-- 5) il livello sessione non c'e' piu' (Q10)
-- ============================================================
SELECT is(
    (SELECT count(*)::integer FROM pg_attribute a
      WHERE a.attrelid = 'config.parameter_overrides'::regclass
        AND a.attname = 'session_key' AND NOT a.attisdropped)
    + (SELECT count(*)::integer FROM pg_proc p
        WHERE p.oid = 'script.fn_get_parameter_full'::regproc
          AND pg_get_function_identity_arguments(p.oid) ~ 'session'),
    0,
    '5) il livello sessione non c''e'' piu'': ne'' la colonna ne'' il parametro della firma'
);

-- ============================================================
-- 6) function vince su default
-- ============================================================
SELECT is(
    script.fn_get_parameter_full(
        'TEST_FN_CASCATA_CAT_CLI_20260515',
        p_function_name        => 'test_function_cascata_20260515',
        p_categoria_cliente_id => NULL
    ),
    'LIVELLO_FUNCTION',
    '6) function vince su default'
);

-- ============================================================
-- 7) fallback a default (nessun override applicabile)
-- ============================================================
SELECT is(
    script.fn_get_parameter_full(
        'TEST_FN_CASCATA_CAT_CLI_20260515',
        p_categoria_cliente_id => NULL
    ),
    'LIVELLO_DEFAULT',
    '7) fallback a default quando nessun override applicabile'
);

-- ============================================================
-- 8) p_categoria_cliente_id=NULL skippa il livello, cade su group
-- ============================================================
SELECT CASE
    WHEN (SELECT group_id FROM tmp_cascata_ctx) IS NULL
    THEN skip('8) Nessun gruppo Django disponibile — test saltato')
    ELSE is(
        script.fn_get_parameter_full(
            'TEST_FN_CASCATA_CAT_CLI_20260515',
            p_categoria_cliente_id => NULL,
            p_group_ids            => ARRAY[(SELECT group_id FROM tmp_cascata_ctx)]
        ),
        'LIVELLO_GROUP',
        '8) categoria_cliente NULL skippa il livello, group prende il controllo'
    )
END;

-- ============================================================
-- 9) parametro inesistente -> raise ERRORE_PARAMETRI_TABELLA
-- ============================================================
SELECT throws_ok(
    $$SELECT script.fn_get_parameter_full(
        'PARAM_INESISTENTE_XYZ_20260515',
        p_categoria_cliente_id => NULL
    )$$,
    'P0001',
    NULL,
    '9) parametro inesistente solleva errore P0001'
);

SELECT * FROM finish();
ROLLBACK;
