-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_cliente_ownership
-- Riferimento: §4.9.2 WIP multi-face-auth (helper per RLS su
-- vendite.ordini e simmetrica a fn_scope_fornitore_ownership per
-- cliente portale / shop customer).
--
-- Semantica attesa:
--   - identita inesistente/inattiva -> false (fail-closed)
--   - identita CLIENTE_PORTALE attiva su proprio SR -> true
--   - identita SHOP_CUSTOMER attiva su proprio SR   -> true
--   - identita CLIENTE_PORTALE su SR di altro cliente -> false (leak)
--
-- Setup: serve 3 SR cliente distinti per rispettare il vincolo
-- uq_identita_digitali_soggetto_ruolo_attivo (un'identita attiva per
-- SR). Se il DB ha meno di 3 clienti con SR distinti, i test dipendenti
-- sono skippati.
--
-- Indice test (1..5):
--    1. Precondizione: 3 clienti con SR distinti
--    2. Identita inesistente -> false
--    3. Identita inattiva -> false
--    4. CLIENTE_PORTALE attiva su proprio SR -> true
--    5. SHOP_CUSTOMER attiva su proprio SR -> true
--    6. Identita cliente A su SR cliente B -> false (leak test)
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

SELECT plan(6);

-- =========================================================
-- 1) Precondizione: 3 clienti con SR distinti
-- =========================================================
CREATE TEMP TABLE _t_sr AS
SELECT sr_id,
       ROW_NUMBER() OVER (ORDER BY sr_id) AS rn
  FROM (
      SELECT DISTINCT c.soggetto_ruolo_id AS sr_id
        FROM anagrafiche.clienti c
       WHERE c.soggetto_ruolo_id IS NOT NULL
         AND NOT EXISTS (
             SELECT 1 FROM anagrafiche.identita_digitali id
              WHERE id.soggetto_ruolo_id = c.soggetto_ruolo_id
                AND id.attivo = true
         )
       ORDER BY c.soggetto_ruolo_id
       LIMIT 3
  ) s;

SELECT ok(
    (SELECT count(*) FROM _t_sr) >= 2,
    '1. Precondizione: almeno 2 clienti con SR distinti senza identita attiva'
);

-- =========================================================
-- 2) Identita inesistente -> false
-- =========================================================
SELECT ok(
    script.fn_scope_cliente_ownership(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.identita_digitali),
        COALESCE((SELECT sr_id FROM _t_sr WHERE rn = 1), 1::bigint)
    ) = false,
    '2. Identita inesistente -> false (fail-closed)'
);

-- =========================================================
-- Setup identita per test 3..6
-- =========================================================
CREATE TEMP TABLE _t_au (idx int, auth_user_id int);
DO $$
DECLARE v_i int; v_id int;
BEGIN
    FOR v_i IN 1..3 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined
        )
        VALUES (
            '_pgtap_scope_cli_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', true, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

CREATE TEMP TABLE _t_id (idx int, identita_id bigint);

-- idx 1: CLIENTE_PORTALE attiva su SR rn=1
DO $$
DECLARE v_sr bigint; v_au int; v_new bigint;
BEGIN
    SELECT sr_id INTO v_sr FROM _t_sr WHERE rn = 1;
    SELECT auth_user_id INTO v_au FROM _t_au WHERE idx = 1;
    IF v_sr IS NULL THEN RETURN; END IF;

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_au, 'CLIENTE_PORTALE', true)
    RETURNING id INTO v_new;

    INSERT INTO _t_id VALUES (1, v_new);
END
$$;

-- idx 2: SHOP_CUSTOMER attiva su SR rn=2 (diverso da rn=1)
DO $$
DECLARE v_sr bigint; v_au int; v_new bigint;
BEGIN
    SELECT sr_id INTO v_sr FROM _t_sr WHERE rn = 2;
    SELECT auth_user_id INTO v_au FROM _t_au WHERE idx = 2;
    IF v_sr IS NULL THEN RETURN; END IF;

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_au, 'SHOP_CUSTOMER', true)
    RETURNING id INTO v_new;

    INSERT INTO _t_id VALUES (2, v_new);
END
$$;

-- idx 3: CLIENTE_PORTALE inattiva su SR rn=3 (se disponibile, altrimenti
-- skip): serve uno stato "inattiva" senza collidere con altre identita
-- attive sullo stesso SR. Se ci sono solo 2 clienti liberi, skippiamo
-- test 3 (inattiva).
DO $$
DECLARE v_sr bigint; v_au int; v_new bigint;
BEGIN
    SELECT sr_id INTO v_sr FROM _t_sr WHERE rn = 3;
    SELECT auth_user_id INTO v_au FROM _t_au WHERE idx = 3;
    IF v_sr IS NULL THEN RETURN; END IF;

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_au, 'CLIENTE_PORTALE', false)
    RETURNING id INTO v_new;

    INSERT INTO _t_id VALUES (3, v_new);
END
$$;

-- =========================================================
-- 3) Identita inattiva -> false
-- =========================================================
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_id WHERE idx = 3)
    THEN ok(
        script.fn_scope_cliente_ownership(
            (SELECT identita_id FROM _t_id WHERE idx = 3),
            (SELECT sr_id FROM _t_sr WHERE rn = 3)
        ) = false,
        '3. Identita inattiva -> false (fail-closed)'
    )
    ELSE skip('Meno di 3 clienti con SR liberi: test 3 skippato', 1)
END;

-- =========================================================
-- 4) CLIENTE_PORTALE attiva su proprio SR -> true
-- =========================================================
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_id WHERE idx = 1)
    THEN ok(
        script.fn_scope_cliente_ownership(
            (SELECT identita_id FROM _t_id WHERE idx = 1),
            (SELECT sr_id FROM _t_sr WHERE rn = 1)
        ) = true,
        '4. CLIENTE_PORTALE attiva su proprio SR -> true'
    )
    ELSE skip('Setup cliente rn=1 fallito: test 4 skippato', 1)
END;

-- =========================================================
-- 5) SHOP_CUSTOMER attiva su proprio SR -> true
-- =========================================================
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_id WHERE idx = 2)
    THEN ok(
        script.fn_scope_cliente_ownership(
            (SELECT identita_id FROM _t_id WHERE idx = 2),
            (SELECT sr_id FROM _t_sr WHERE rn = 2)
        ) = true,
        '5. SHOP_CUSTOMER attiva su proprio SR -> true (ruolo CL condiviso)'
    )
    ELSE skip('Setup cliente rn=2 fallito: test 5 skippato', 1)
END;

-- =========================================================
-- 6) CLIENTE_PORTALE cliente 1 su SR cliente 2 -> false (leak)
-- =========================================================
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_id WHERE idx = 1)
     AND EXISTS (SELECT 1 FROM _t_sr WHERE rn = 2)
    THEN ok(
        script.fn_scope_cliente_ownership(
            (SELECT identita_id FROM _t_id WHERE idx = 1),
            (SELECT sr_id FROM _t_sr WHERE rn = 2)
        ) = false,
        '6. Identita cliente rn=1 su SR cliente rn=2 -> false (leak test)'
    )
    ELSE skip('Setup incompleto per leak test: test 6 skippato', 1)
END;

SELECT * FROM finish();
