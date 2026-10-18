-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_ba_ownership_via_fattura
-- Riferimento: §4.9.3 WIP multi-face-auth (helper per RLS su
-- vendite.fatture_scadenze e altre tabelle collegate a vendite.fatture
-- senza billing_account_id diretto).
--
-- Semantica attesa:
--   - fattura inesistente -> false (fail-closed)
--   - identita attiva il cui SR coincide col SR del BA della fattura -> true
--   - identita attiva su fattura di altro cliente -> false (leak test)
--   - identita inattiva -> false
--
-- Dipende da: presenza di almeno una fattura con billing_account_id
-- popolato nel DB. In assenza, i test di leak sono skippati.
--
-- Indice test (1..5):
--    1. Fattura inesistente -> false (sempre testabile)
--    2. Identita attiva del cliente della fattura -> true
--    3. Identita di altro cliente -> false (leak test)
--    4. Identita inattiva dello stesso cliente -> false
--    5. Ambiente senza fattura: accounting plan
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

SELECT plan(4);

-- =========================================================
-- 1) Fattura inesistente -> false (sempre testabile)
-- =========================================================
SELECT ok(
    script.fn_scope_ba_ownership_via_fattura(
        1::bigint,
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM vendite.fatture)
    ) = false,
    '1. Fattura inesistente -> false (fail-closed)'
);

-- =========================================================
-- Setup per test 2..4: trova una fattura e 2 SR cliente distinti,
-- crea 3 identita (attiva stesso cliente, attiva altro cliente,
-- inattiva stesso cliente).
-- Se precondizione mancante -> skip 3 tests.
-- =========================================================
CREATE TEMP TABLE _t_setup (
    fattura_id  bigint,
    sr_fattura  bigint,
    sr_altro    bigint,
    id_attiva   bigint,
    id_altro    bigint,
    id_inattiva bigint,
    is_ready    boolean
);

DO $pgtap$
DECLARE
    v_fat_id   bigint;
    v_sr_fat   bigint;
    v_sr_alt   bigint;
    v_au_1     int;
    v_au_2     int;
    v_au_3     int;
    v_id_1     bigint;
    v_id_2     bigint;
    v_id_3     bigint;
BEGIN
    SELECT f.id, ba.soggetto_ruolo_id
      INTO v_fat_id, v_sr_fat
      FROM vendite.fatture              f
      JOIN anagrafiche.billing_account  ba ON ba.id = f.billing_account_id
     ORDER BY f.id
     LIMIT 1;

    IF v_fat_id IS NULL THEN
        INSERT INTO _t_setup (is_ready) VALUES (false);
        RETURN;
    END IF;

    SELECT c.soggetto_ruolo_id
      INTO v_sr_alt
      FROM anagrafiche.clienti c
     WHERE c.soggetto_ruolo_id IS NOT NULL
       AND c.soggetto_ruolo_id <> v_sr_fat
     LIMIT 1;

    IF v_sr_alt IS NULL THEN
        INSERT INTO _t_setup (is_ready) VALUES (false);
        RETURN;
    END IF;

    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_bf_1_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au_1;

    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_bf_2_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au_2;

    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_bf_3_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au_3;

    BEGIN
        v_id_1 := anagrafiche.fn_crea_veste_portale(v_au_1, v_sr_fat, 'CLIENTE_PORTALE', true);
    EXCEPTION WHEN unique_violation THEN
        -- SR gia' ha una identita attiva: fallback inattiva e skip test 2
        v_id_1 := NULL;
    END;

    BEGIN
        v_id_2 := anagrafiche.fn_crea_veste_portale(v_au_2, v_sr_alt, 'CLIENTE_PORTALE', true);
    EXCEPTION WHEN unique_violation THEN
        v_id_2 := NULL;
    END;

    BEGIN
        v_id_3 := anagrafiche.fn_crea_veste_portale(v_au_3, v_sr_fat, 'CLIENTE_PORTALE', false);
    EXCEPTION WHEN unique_violation THEN
        v_id_3 := NULL;
    END;

    INSERT INTO _t_setup (fattura_id, sr_fattura, sr_altro, id_attiva, id_altro, id_inattiva, is_ready)
    VALUES (v_fat_id, v_sr_fat, v_sr_alt, v_id_1, v_id_2, v_id_3, true);
END
$pgtap$;

-- =========================================================
-- 2) Identita attiva del cliente fattura -> true
-- =========================================================
SELECT CASE
    WHEN (SELECT is_ready AND id_attiva IS NOT NULL FROM _t_setup)
    THEN ok(
        script.fn_scope_ba_ownership_via_fattura(
            (SELECT id_attiva FROM _t_setup),
            (SELECT fattura_id FROM _t_setup)
        ) = true,
        '2. Identita attiva del cliente della fattura -> true'
    )
    ELSE skip('Setup non completo (nessuna fattura / cliente / vincolo UNIQUE): test 2 skippato', 1)
END;

-- =========================================================
-- 3) Identita altro cliente -> false (leak test)
-- =========================================================
SELECT CASE
    WHEN (SELECT is_ready AND id_altro IS NOT NULL FROM _t_setup)
    THEN ok(
        script.fn_scope_ba_ownership_via_fattura(
            (SELECT id_altro FROM _t_setup),
            (SELECT fattura_id FROM _t_setup)
        ) = false,
        '3. Identita di altro cliente -> false (leak test)'
    )
    ELSE skip('Setup non completo: test 3 skippato', 1)
END;

-- =========================================================
-- 4) Identita inattiva dello stesso cliente -> false
-- =========================================================
SELECT CASE
    WHEN (SELECT is_ready AND id_inattiva IS NOT NULL FROM _t_setup)
    THEN ok(
        script.fn_scope_ba_ownership_via_fattura(
            (SELECT id_inattiva FROM _t_setup),
            (SELECT fattura_id FROM _t_setup)
        ) = false,
        '4. Identita inattiva del cliente fattura -> false (fail-closed)'
    )
    ELSE skip('Setup non completo: test 4 skippato', 1)
END;

SELECT * FROM finish();
