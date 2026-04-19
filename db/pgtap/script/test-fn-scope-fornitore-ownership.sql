-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_fornitore_ownership
-- Riferimento: §4.4 WIP multi-face-auth, policy FORNITORE_OWNERSHIP.
--
-- Semantica attesa:
--   - identita inesistente/inattiva              -> false (fail-closed)
--   - identita FORNITORE_PORTALE, target SR match -> true
--   - identita FORNITORE_PORTALE, target SR diff  -> false (leak test)
--   - identita non-FORNITORE_PORTALE, target coincide -> false (defense-in-depth)
--
-- Indice test (1..7):
--    1. Precondizione: 2 fornitori + 1 cliente in fixture
--    2. Setup: identita FORNITORE_PORTALE attiva su fornitore 1
--              + identita CLIENTE_PORTALE attiva su cliente (per test ruolo)
--    3. Identita inesistente -> false
--    4. FORNITORE_PORTALE, target SR_fo_1 (match) -> true
--    5. FORNITORE_PORTALE, target SR_fo_2 (altro fornitore) -> false (leak)
--    6. CLIENTE_PORTALE, target SR_cl (suo stesso SR) -> false (ruolo sbagliato)
--    7. Disattivo FORNITORE_PORTALE, riprova match -> false (fail-closed su attivo)
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- =========================================================
-- 1) Precondizione: 2 fornitori + 1 cliente
-- =========================================================
CREATE TEMP TABLE _t_sr_fo AS
SELECT sr.id AS sr_id,
       ROW_NUMBER() OVER (ORDER BY f.id) AS rn
  FROM anagrafiche.fornitori f
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.soggetto_ruolo_id
 ORDER BY f.id
 LIMIT 2;

CREATE TEMP TABLE _t_sr_cl AS
SELECT sr.id AS sr_id
  FROM anagrafiche.clienti c
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
 ORDER BY c.id
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_sr_fo) = 2
    AND (SELECT count(*) FROM _t_sr_cl) = 1,
    '1. Precondizione: 2 fornitori + 1 cliente disponibili in fixture'
);

-- =========================================================
-- 2) Setup: 2 auth_user + 2 identita (FORNITORE + CLIENTE)
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
            '_pgtap_scope_fo_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', true, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

-- Identita FORNITORE_PORTALE attiva su fornitore 1 (rn=1)
CREATE TEMP TABLE _t_id (idx int, identita_id bigint);
WITH ins_fo AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT (SELECT sr_id FROM _t_sr_fo WHERE rn = 1),
           (SELECT auth_user_id FROM _t_au WHERE idx = 1),
           'FORNITORE_PORTALE', true
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id)
SELECT 1, id FROM ins_fo;

-- Identita CLIENTE_PORTALE attiva su cliente (ruolo "sbagliato" per test 6)
WITH ins_cl AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT (SELECT sr_id FROM _t_sr_cl),
           (SELECT auth_user_id FROM _t_au WHERE idx = 2),
           'CLIENTE_PORTALE', true
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id)
SELECT 2, id FROM ins_cl;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 2,
    '2. Setup: 2 identita create (FORNITORE_PORTALE + CLIENTE_PORTALE)'
);

-- =========================================================
-- 3) Identita inesistente -> false
-- =========================================================
SELECT ok(
    script.fn_scope_fornitore_ownership(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.identita_digitali),
        (SELECT sr_id FROM _t_sr_fo WHERE rn = 1)
    ) = false,
    '3. Identita inesistente -> false (fail-closed)'
);

-- =========================================================
-- 4) FORNITORE_PORTALE, target SR match -> true
-- =========================================================
SELECT ok(
    script.fn_scope_fornitore_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT sr_id FROM _t_sr_fo WHERE rn = 1)
    ) = true,
    '4. FORNITORE_PORTALE su proprio SR fornitore -> true'
);

-- =========================================================
-- 5) FORNITORE_PORTALE, target SR altro fornitore -> false (leak)
-- =========================================================
SELECT ok(
    script.fn_scope_fornitore_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT sr_id FROM _t_sr_fo WHERE rn = 2)
    ) = false,
    '5. FORNITORE_PORTALE su SR altro fornitore -> false (leak test)'
);

-- =========================================================
-- 6) CLIENTE_PORTALE, target suo stesso SR -> false (ruolo sbagliato)
-- =========================================================
-- Defense-in-depth: la funzione verifica ruolo_applicativo =
-- 'FORNITORE_PORTALE'. Un binding accidentale su identita CLIENTE_PORTALE
-- non deve aprire l'accesso.
SELECT ok(
    script.fn_scope_fornitore_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 2),
        (SELECT sr_id FROM _t_sr_cl)
    ) = false,
    '6. CLIENTE_PORTALE su proprio SR -> false (defense-in-depth ruolo sbagliato)'
);

-- =========================================================
-- 7) Disattivo identita FORNITORE -> match precedente ora false
-- =========================================================
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE id = (SELECT identita_id FROM _t_id WHERE idx = 1);

SELECT ok(
    script.fn_scope_fornitore_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT sr_id FROM _t_sr_fo WHERE rn = 1)
    ) = false,
    '7. FORNITORE_PORTALE disattivato, match SR precedente -> false (fail-closed su attivo)'
);

SELECT * FROM finish();
