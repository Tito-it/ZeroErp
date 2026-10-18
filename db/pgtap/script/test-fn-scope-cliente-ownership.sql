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
-- Setup: servono 3 SR cliente distinti per rispettare il vincolo
-- uq_identita_digitali_soggetto_ruolo_attivo (un'identita attiva per SR).
-- ⛔ SI COSTRUISCONO, non si cercano (2026-09-12): fino a quel giorno il file
--   pescava tre clienti «liberi» fra quelli ESISTENTI e, se non li trovava,
--   SALTAVA i test — su un database ricostruito dai changelog era rosso al
--   test 1 e saltato in tutto il resto. Tre soggetti persona giuridica con
--   ruolo CL (`dbops.fn_pgtap_crea_soggetto_pg` + `fn_pgtap_crea_soggetto_ruolo`):
--   alla funzione sotto test basta il soggetto_ruolo, non serve un BA.
--   Niente piu' rami `skip`: i tre SR ci sono sempre.
--
-- Indice test (1..5):
--    1. Precondizione: 3 clienti con SR distinti (costruiti)
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
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('Cliente ownership pgTAP ' || g), 'CL'::character varying) AS sr_id,
       g AS rn
  FROM generate_series(1, 3) AS g;

SELECT ok(
    (SELECT count(*) FROM _t_sr) = 3
    AND (SELECT count(DISTINCT sr_id) FROM _t_sr) = 3
    AND NOT EXISTS (SELECT 1 FROM anagrafiche.identita_digitali id
                     WHERE id.soggetto_ruolo_id IN (SELECT sr_id FROM _t_sr)),
    '1. Precondizione: 3 clienti con SR distinti, costruiti, senza identita'''
);

-- =========================================================
-- 2) Identita inesistente -> false
-- =========================================================
SELECT ok(
    script.fn_scope_cliente_ownership(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.identita_digitali),
        (SELECT sr_id FROM _t_sr WHERE rn = 1)
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
    v_new := anagrafiche.fn_crea_veste_portale(v_au, v_sr, 'CLIENTE_PORTALE', true);

    INSERT INTO _t_id VALUES (1, v_new);
END
$$;

-- idx 2: SHOP_CUSTOMER attiva su SR rn=2 (diverso da rn=1)
DO $$
DECLARE v_sr bigint; v_au int; v_new bigint;
BEGIN
    SELECT sr_id INTO v_sr FROM _t_sr WHERE rn = 2;
    SELECT auth_user_id INTO v_au FROM _t_au WHERE idx = 2;
    v_new := anagrafiche.fn_crea_veste_portale(v_au, v_sr, 'SHOP_CUSTOMER', true);

    INSERT INTO _t_id VALUES (2, v_new);
END
$$;

-- idx 3: CLIENTE_PORTALE inattiva su SR rn=3: serve uno stato "inattiva"
-- senza collidere con altre identita attive sullo stesso SR.
DO $$
DECLARE v_sr bigint; v_au int; v_new bigint;
BEGIN
    SELECT sr_id INTO v_sr FROM _t_sr WHERE rn = 3;
    SELECT auth_user_id INTO v_au FROM _t_au WHERE idx = 3;
    v_new := anagrafiche.fn_crea_veste_portale(v_au, v_sr, 'CLIENTE_PORTALE', false);

    INSERT INTO _t_id VALUES (3, v_new);
END
$$;

-- =========================================================
-- 3) Identita inattiva -> false
-- =========================================================
SELECT ok(
    script.fn_scope_cliente_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 3),
        (SELECT sr_id FROM _t_sr WHERE rn = 3)
    ) = false,
    '3. Identita inattiva -> false (fail-closed)'
);

-- =========================================================
-- 4) CLIENTE_PORTALE attiva su proprio SR -> true
-- =========================================================
SELECT ok(
    script.fn_scope_cliente_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT sr_id FROM _t_sr WHERE rn = 1)
    ) = true,
    '4. CLIENTE_PORTALE attiva su proprio SR -> true'
);

-- =========================================================
-- 5) SHOP_CUSTOMER attiva su proprio SR -> true
-- =========================================================
SELECT ok(
    script.fn_scope_cliente_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 2),
        (SELECT sr_id FROM _t_sr WHERE rn = 2)
    ) = true,
    '5. SHOP_CUSTOMER attiva su proprio SR -> true (ruolo CL condiviso)'
);

-- =========================================================
-- 6) CLIENTE_PORTALE cliente 1 su SR cliente 2 -> false (leak)
-- =========================================================
SELECT ok(
    script.fn_scope_cliente_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT sr_id FROM _t_sr WHERE rn = 2)
    ) = false,
    '6. Identita cliente rn=1 su SR cliente rn=2 -> false (leak test)'
);

SELECT * FROM finish();
ROLLBACK;
