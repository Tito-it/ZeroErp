-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_is_super_admin filtro ruolo_applicativo='OPERATORE'
-- Riferimento: migration 20260420-11-01 (§13 guida permessi).
--
-- Semantica post 20-04-2026:
--   fn_is_super_admin(auth_user_id) -> true SOLO se esiste un'identita
--   OPERATORE attiva per quell'user con binding SUPER_ADMIN. Un binding
--   su un'identita non-OPERATORE (scenario patologico) non attiva il
--   bypass.
--
-- Strategia: riusa user esistenti nel DB per i casi 2 e 3 (evita la
-- creazione di soggetti ex-novo che collide con CF fissi gia' presenti
-- nel seed). Solo il test 4 crea un'identita nuova su un SR CL libero.
-- Ogni test e' skip-safe se la precondizione non e' disponibile.
--
-- Indice test (1..4):
--    1. Precondizione: cerca fixture esistenti + prepara SR CL libero
--    2. User con OPERATORE + binding SUPER_ADMIN attivo (da seed)
--       -> fn_is_super_admin = true
--    3. User OPERATORE senza binding SUPER_ADMIN -> fn_is_super_admin = false
--    4. User con sola identita CLIENTE_PORTALE + binding SUPER_ADMIN
--       patologico -> fn_is_super_admin = false (filtro OPERATORE)
--
-- BEGIN; + rollback implicito.
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
-- 1) Precondizione: fixture lookup
--    a) user super-admin esistente (seed tid post-cutover o simile)
--    b) user operatore non-super-admin esistente
--    c) 1 SR CL libero (no identita attive) per test 4
--    d) 1 auth_user pool per test 4
-- =========================================================
CREATE TEMP TABLE _t_ctx AS
WITH super_admin_user AS (
    -- Cerco il primo user che ha binding SUPER_ADMIN attivo su
    -- identita OPERATORE attiva (come seed tid).
    SELECT id.auth_user_id
      FROM anagrafiche.identita_digitali       id
      JOIN config.profili_accesso_bindings     pab ON pab.identita_digitale_id = id.id
      JOIN config.profili_accesso              pa  ON pa.id = pab.profilo_accesso_id
     WHERE id.attivo            = true
       AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
       AND pab.attivo           = true
       AND pa.attivo            = true
       AND pa.tipo              = 'SUPER_ADMIN'::config.tipo_profilo_accesso
     ORDER BY id.auth_user_id
     LIMIT 1
), op_non_admin_user AS (
    -- Cerco un user con OPERATORE attiva MA senza binding SUPER_ADMIN.
    SELECT id.auth_user_id
      FROM anagrafiche.identita_digitali id
     WHERE id.attivo            = true
       AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
       AND NOT EXISTS (
           SELECT 1
             FROM config.profili_accesso_bindings pab
             JOIN config.profili_accesso          pa  ON pa.id = pab.profilo_accesso_id
            WHERE pab.identita_digitale_id = id.id
              AND pab.attivo = true
              AND pa.attivo  = true
              AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
       )
     ORDER BY id.auth_user_id
     LIMIT 1
), sr_cl_libero AS (
    SELECT DISTINCT sr.id AS sr_id
      FROM anagrafiche.clienti        c
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
      JOIN anagrafiche.soggetti       s  ON s.id = sr.soggetto_id
     WHERE s.attivo = true
       AND NOT EXISTS (
           SELECT 1 FROM anagrafiche.identita_digitali id
            WHERE id.soggetto_ruolo_id = sr.id
              AND id.attivo = true
       )
     ORDER BY sr.id
     LIMIT 1
)
SELECT
    (SELECT auth_user_id FROM super_admin_user)    AS super_admin_user_id,
    (SELECT auth_user_id FROM op_non_admin_user)   AS op_non_admin_user_id,
    (SELECT sr_id        FROM sr_cl_libero)        AS sr_cl_libero_id;

-- Pool di 1 auth_user per test 4 (identita CLIENTE_PORTALE).
CREATE TEMP TABLE _t_au_pool (idx int, auth_user_id int);
DO $$
DECLARE v_id int;
BEGIN
    INSERT INTO django.auth_user (
        username, password, is_active, is_staff, is_superuser,
        first_name, last_name, email, date_joined
    )
    VALUES (
        '_pgtap_sa_cp_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', false, false, false, '', '', '', now()
    )
    RETURNING id INTO v_id;
    INSERT INTO _t_au_pool (idx, auth_user_id) VALUES (1, v_id);
END
$$;

SELECT ok(
    (SELECT count(*) FROM _t_ctx) = 1,
    '1. Precondizione: fixture lookup completata (super_admin / op_non_admin / SR CL libero — i singoli test skippano se NULL)'
);

-- =========================================================
-- 2) User super-admin esistente -> fn_is_super_admin = true
-- =========================================================
SELECT CASE
    WHEN (SELECT super_admin_user_id FROM _t_ctx) IS NOT NULL THEN
        is(
            script.fn_is_super_admin(
                (SELECT super_admin_user_id FROM _t_ctx)
            ),
            true,
            '2. User OPERATORE con binding SUPER_ADMIN -> fn_is_super_admin=true'
        )
    ELSE skip('Nessun super_admin seedato nel DB: test 2 skippato', 1)
END;

-- =========================================================
-- 3) User OPERATORE senza binding SUPER_ADMIN
--    -> fn_is_super_admin = false
-- =========================================================
SELECT CASE
    WHEN (SELECT op_non_admin_user_id FROM _t_ctx) IS NOT NULL THEN
        is(
            script.fn_is_super_admin(
                (SELECT op_non_admin_user_id FROM _t_ctx)
            ),
            false,
            '3. User OPERATORE senza binding SUPER_ADMIN -> fn_is_super_admin=false'
        )
    ELSE skip('Nessun operatore non-admin nel DB: test 3 skippato', 1)
END;

-- =========================================================
-- 4) User con sola identita CLIENTE_PORTALE + binding SUPER_ADMIN
--    patologico -> fn_is_super_admin = false (filtro OPERATORE).
--    Crea setup on-the-fly se fixture SR CL libero e' disponibile.
-- =========================================================
DO $$
DECLARE
    v_id_digi bigint;
BEGIN
    IF (SELECT sr_cl_libero_id FROM _t_ctx) IS NOT NULL THEN
        v_id_digi := anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 1), (SELECT sr_cl_libero_id FROM _t_ctx), 'CLIENTE_PORTALE'::config.ruolo_applicativo, true);

        -- Binding patologico: SUPER_ADMIN (id 9100) su identita
        -- non-OPERATORE. Tecnicamente ammesso dal modello (no guard
        -- esplicito) — serve a verificare che la fn lo ignori grazie
        -- al filtro ruolo_applicativo = 'OPERATORE'.
        PERFORM config.fn_lega_profilo_identita(9100, v_id_digi);
    END IF;
END
$$;

SELECT CASE
    WHEN (SELECT sr_cl_libero_id FROM _t_ctx) IS NOT NULL THEN
        is(
            script.fn_is_super_admin(
                (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1)
            ),
            false,
            '4. CLIENTE_PORTALE + binding SUPER_ADMIN patologico -> fn_is_super_admin=false (filtro OPERATORE)'
        )
    ELSE skip('Nessun SR CL libero: test 4 skippato', 1)
END;

SELECT * FROM finish();
ROLLBACK;
