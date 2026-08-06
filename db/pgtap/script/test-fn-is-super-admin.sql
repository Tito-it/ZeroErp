-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_is_super_admin
-- Riferimento: §4.6.B.1 WIP multi-face-auth (ADMIN come profilo).
--
-- Semantica attesa:
--   - NULL auth_user -> false
--   - Identita inesistente -> false
--   - Identita attiva + binding SUPER_ADMIN attivo -> true
--   - Identita attiva + binding inattivo -> false
--   - Identita inattiva + binding attivo -> false
--   - Profilo SUPER_ADMIN inattivo -> false
--   - Identita fuori finestra temporale -> false
--
-- Pattern: uso CLIENTE_PORTALE su cliente esistente per evitare il guard
-- PF pura sugli operatori (il test non dipende dal ruolo applicativo).
--
-- Indice test (1..8):
--    1. Setup: 3 auth_user + 3 identita CLIENTE_PORTALE su clienti distinti
--    2. fn_is_super_admin(NULL) -> false
--    3. fn_is_super_admin su auth_user senza identita -> false
--    4. Identita attiva + binding attivo -> true
--    5. Identita attiva + nessun binding -> false
--    6. Identita inattiva + binding attivo -> false
--    7. Binding disattivato -> false
--    8. Identita con valido_al scaduto -> false
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- =========================================================
-- 1) Setup: 3 BA di clienti distinti + 3 auth_user + 3 identita
-- =========================================================
CREATE TEMP TABLE _t_srs AS
WITH primi_sr AS (
    SELECT DISTINCT ON (ba.soggetto_ruolo_id) ba.soggetto_ruolo_id AS sr_id
      FROM anagrafiche.billing_account ba
     WHERE ba.soggetto_ruolo_id IS NOT NULL
     ORDER BY ba.soggetto_ruolo_id, ba.id
)
SELECT sr_id,
       ROW_NUMBER() OVER (ORDER BY sr_id) AS rn
  FROM primi_sr
 LIMIT 3;

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
            '_pgtap_isa_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', true, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

CREATE TEMP TABLE _t_id (idx int, identita_id bigint);

-- Identita 1: attiva, aperta (per caso 4, 7)
WITH ins AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT s.sr_id, a.auth_user_id, 'CLIENTE_PORTALE', true
      FROM _t_srs s JOIN _t_au a ON a.idx = s.rn
     WHERE s.rn = 1
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id) SELECT 1, id FROM ins;

-- Identita 2: attiva, nessun binding (caso 5)
WITH ins AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT s.sr_id, a.auth_user_id, 'CLIENTE_PORTALE', true
      FROM _t_srs s JOIN _t_au a ON a.idx = s.rn
     WHERE s.rn = 2
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id) SELECT 2, id FROM ins;

-- Identita 3: INATTIVA (caso 6)
WITH ins AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT s.sr_id, a.auth_user_id, 'CLIENTE_PORTALE', false
      FROM _t_srs s JOIN _t_au a ON a.idx = s.rn
     WHERE s.rn = 3
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id) SELECT 3, id FROM ins;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 3,
    '1. Setup: 3 identita CLIENTE_PORTALE create (2 attive, 1 inattiva)'
);

-- =========================================================
-- 2) fn_is_super_admin(NULL) -> false
-- =========================================================
SELECT ok(
    script.fn_is_super_admin(NULL) = false,
    '2. fn_is_super_admin(NULL) -> false (fail-closed)'
);

-- =========================================================
-- 3) auth_user senza identita -> false
-- =========================================================
SELECT ok(
    script.fn_is_super_admin(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM django.auth_user)
    ) = false,
    '3. auth_user inesistente (no identita) -> false'
);

-- =========================================================
-- 4) Identita attiva + binding SUPER_ADMIN attivo -> true
-- =========================================================
INSERT INTO config.profili_accesso_bindings
    (profilo_accesso_id, identita_digitale_id, attivo)
VALUES (9100, (SELECT identita_id FROM _t_id WHERE idx = 1), true);

SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1)
    ) = true,
    '4. Identita attiva + binding SUPER_ADMIN attivo -> true'
);

-- =========================================================
-- 5) Identita attiva senza binding -> false
-- =========================================================
SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 2)
    ) = false,
    '5. Identita attiva senza binding SUPER_ADMIN -> false'
);

-- =========================================================
-- 6) Identita inattiva + binding attivo -> false
-- =========================================================
INSERT INTO config.profili_accesso_bindings
    (profilo_accesso_id, identita_digitale_id, attivo)
VALUES (9100, (SELECT identita_id FROM _t_id WHERE idx = 3), true);

SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 3)
    ) = false,
    '6. Identita inattiva + binding attivo -> false (fail-closed)'
);

-- =========================================================
-- 7) Binding disattivato -> false
-- =========================================================
UPDATE config.profili_accesso_bindings
   SET attivo = false
 WHERE identita_digitale_id = (SELECT identita_id FROM _t_id WHERE idx = 1)
   AND profilo_accesso_id = 9100;

SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1)
    ) = false,
    '7. Binding disattivato (attivo=false) -> false'
);

-- Riattivo per caso 8
UPDATE config.profili_accesso_bindings
   SET attivo = true
 WHERE identita_digitale_id = (SELECT identita_id FROM _t_id WHERE idx = 1)
   AND profilo_accesso_id = 9100;

-- =========================================================
-- 8) Identita fuori finestra (valido_al scaduto) -> false
-- =========================================================
-- NOTA: chk_identita_digitali_date impone valido_al >= valido_dal.
-- Per simulare finestra scaduta aggiorno ENTRAMBE le date:
-- valido_dal 30 giorni fa, valido_al ieri (coerente col CHECK).
UPDATE anagrafiche.identita_digitali
   SET valido_dal = CURRENT_DATE - 30,
       valido_al  = CURRENT_DATE - 1
 WHERE id = (SELECT identita_id FROM _t_id WHERE idx = 1);

SELECT ok(
    script.fn_is_super_admin(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1)
    ) = false,
    '8. Identita con valido_al scaduto -> false'
);

SELECT * FROM finish();
ROLLBACK;
