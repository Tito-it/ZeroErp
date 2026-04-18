-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_ba_ownership
-- Riferimento: §4.4 WIP multi-face-auth, policy BA_OWNERSHIP.
--
-- Semantica attesa:
--   - identita inesistente/inattiva -> false (fail-closed)
--   - BA appartiene al soggetto_ruolo dell'identita -> true
--   - BA appartiene a un altro soggetto_ruolo -> false (leak test)
--
-- Indice test (1..6):
--    1. Precondizione: due billing_account di clienti distinti
--    2. Setup: identita CLIENTE_PORTALE attiva per cliente 1
--              + identita CLIENTE_PORTALE inattiva per cliente 2
--    3. Identita inesistente -> false
--    4. Identita inattiva -> false
--    5. Identita cliente 1 su BA cliente 1 -> true
--    6. Identita cliente 1 su BA cliente 2 -> false (leak test)
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

-- =========================================================
-- 1) Precondizione: 2 BA di clienti distinti
-- =========================================================
-- Un cliente puo' avere piu' BA; serve UN BA per cliente distinto,
-- altrimenti il leak test (caso 6) diventa banale. DISTINCT ON garantisce
-- che per ogni sr_id (cliente) venga selezionato un solo BA (il minimo).
CREATE TEMP TABLE _t_bas AS
WITH primi_ba_per_cliente AS (
    SELECT DISTINCT ON (ba.soggetto_ruolo_id)
           ba.id                AS ba_id,
           ba.soggetto_ruolo_id AS sr_id
      FROM anagrafiche.billing_account ba
      JOIN anagrafiche.clienti c
        ON c.soggetto_ruolo_id = ba.soggetto_ruolo_id
     WHERE ba.soggetto_ruolo_id IS NOT NULL
     ORDER BY ba.soggetto_ruolo_id, ba.id
)
SELECT ba_id,
       sr_id,
       ROW_NUMBER() OVER (ORDER BY sr_id) AS rn
  FROM primi_ba_per_cliente
 LIMIT 2;

SELECT ok(
    (SELECT count(*) FROM _t_bas) = 2
    AND (SELECT count(DISTINCT sr_id) FROM _t_bas) = 2,
    '1. Precondizione: 2 BA di clienti con soggetti_ruoli distinti'
);

-- =========================================================
-- 2) Setup: 2 auth_user + 2 identita CLIENTE_PORTALE
-- =========================================================
CREATE TEMP TABLE _t_au (idx int, auth_user_id int);
DO $$
DECLARE v_i int; v_id int;
BEGIN
    FOR v_i IN 1..2 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined
        )
        VALUES (
            '_pgtap_scope_ba_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', true, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

-- Identita attiva per cliente 1 (rn=1)
CREATE TEMP TABLE _t_id (idx int, identita_id bigint);
WITH ins_a AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT b.sr_id, (SELECT auth_user_id FROM _t_au WHERE idx = 1),
           'CLIENTE_PORTALE', true
      FROM _t_bas b WHERE b.rn = 1
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id)
SELECT 1, id FROM ins_a;

-- Identita inattiva per cliente 2 (rn=2)
WITH ins_i AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT b.sr_id, (SELECT auth_user_id FROM _t_au WHERE idx = 2),
           'CLIENTE_PORTALE', false
      FROM _t_bas b WHERE b.rn = 2
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id)
SELECT 2, id FROM ins_i;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 2,
    '2. Setup: 2 identita CLIENTE_PORTALE create (1 attiva, 1 inattiva)'
);

-- =========================================================
-- 3) Identita inesistente -> false
-- =========================================================
SELECT ok(
    script.fn_scope_ba_ownership(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.identita_digitali),
        (SELECT ba_id FROM _t_bas WHERE rn = 1)
    ) = false,
    '3. Identita inesistente -> false (fail-closed)'
);

-- =========================================================
-- 4) Identita inattiva -> false
-- =========================================================
SELECT ok(
    script.fn_scope_ba_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 2),
        (SELECT ba_id FROM _t_bas WHERE rn = 2)
    ) = false,
    '4. Identita inattiva -> false (fail-closed)'
);

-- =========================================================
-- 5) Identita cliente 1 su BA cliente 1 -> true
-- =========================================================
SELECT ok(
    script.fn_scope_ba_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT ba_id FROM _t_bas WHERE rn = 1)
    ) = true,
    '5. Identita attiva cliente 1 su BA cliente 1 -> true'
);

-- =========================================================
-- 6) Identita cliente 1 su BA cliente 2 -> false (leak test)
-- =========================================================
-- Il BA del cliente 2 deve essere invisibile all'identita del cliente 1.
SELECT ok(
    script.fn_scope_ba_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT ba_id FROM _t_bas WHERE rn = 2)
    ) = false,
    '6. Identita cliente 1 su BA cliente 2 -> false (leak test: cliente A non vede BA di cliente B)'
);

SELECT * FROM finish();
