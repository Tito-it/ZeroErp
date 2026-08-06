-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_check_ultimo_super_admin_attivo(p_auth_user_id)
--   Predicato per-utente per le capability can_disable /
--   can_demote_super_admin del drawer Operatore (P1 2026-04-29).
--
-- Strategia:
--   Ambiente con SUPER_ADMIN preesistenti (seed 80_data tid).
--   Helper pg_temp.mk_admin() crea un binding SA su un'identita
--   OPERATORE "vergine" (mai avuta un binding) per produrre
--   scenari multi-SA controllati. Lo stato finale viene rolled
--   back dal BEGIN/ROLLBACK implicito a fine file.
--
-- Indice test (1..5):
--   1. NULL/zero -> false (guard parametro non valido)
--   2. Multi super-admin -> false su ciascuno (no lockout)
--   3. Single super-admin -> true sull'unico SA
--   4. Single super-admin -> false su un auth_user NON super-admin
--   5. Auth user inesistente -> false
--
-- Niente SAVEPOINT (azzera il counter pgTAP -> "No tests run!").
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- =========================================================
-- Helper: crea un binding SUPER_ADMIN ad-hoc su un'identita
-- OPERATORE "vergine" (mai avuta un binding). Filtro su
-- NOT EXISTS qualsiasi binding per rispettare uq_profili_accesso_bindings_identita
-- (partial unique WHERE identita_digitale_id IS NOT NULL).
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.mk_admin(OUT id_id bigint, OUT au_id integer, OUT bind_id bigint)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT id.id, id.auth_user_id INTO id_id, au_id
      FROM anagrafiche.identita_digitali id
     WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
       AND id.attivo = true
       AND NOT EXISTS (
           SELECT 1
             FROM config.profili_accesso_bindings pab
            WHERE pab.identita_digitale_id = id.id
       )
     ORDER BY id.id
     LIMIT 1;

    IF id_id IS NULL THEN
        RAISE EXCEPTION 'Setup impossibile: nessuna identita OPERATORE vergine disponibile';
    END IF;

    INSERT INTO config.profili_accesso_bindings
        (profilo_accesso_id, identita_digitale_id, attivo)
    VALUES (
        (SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'),
        id_id,
        true
    )
    RETURNING id INTO bind_id;
END
$$;

-- =========================================================
-- Helper: disattiva tutti i binding SA attivi tranne quello passato.
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.disable_other_sa(p_keep_bind_id bigint)
RETURNS int
LANGUAGE plpgsql
AS $$
DECLARE
    v_b record;
    v_count int := 0;
BEGIN
    FOR v_b IN
        SELECT pab.id
          FROM config.profili_accesso_bindings pab
          JOIN config.profili_accesso          pa
            ON pa.id = pab.profilo_accesso_id
         WHERE pa.codice = 'SUPER_ADMIN'
           AND pab.attivo = true
           AND pab.id <> p_keep_bind_id
    LOOP
        UPDATE config.profili_accesso_bindings
           SET attivo = false
         WHERE id = v_b.id;
        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END
$$;

-- =========================================================
-- 1) Guard parametro: NULL e <=0 -> false
-- =========================================================
SELECT is(
    script.fn_check_ultimo_super_admin_attivo(NULL),
    false,
    '1. NULL -> false (guard fail-closed)'
);

-- =========================================================
-- 2) Multi super-admin: aggiungo 1 SA ad-hoc, ne risultano >=2.
--    Su nessuno dei due deve risultare "ultimo".
-- =========================================================
CREATE TEMP TABLE _t_c2 AS SELECT * FROM pg_temp.mk_admin();

SELECT is(
    script.fn_check_ultimo_super_admin_attivo((SELECT au_id FROM _t_c2)),
    false,
    '2. Multi super-admin (>=2 SA): non e'' l''ultimo -> false'
);

-- =========================================================
-- 3) Single super-admin: disattivo tutti gli altri SA
--    tranne il binding del caso 2 -> auth_user di _t_c2 e' l'unico.
-- =========================================================
SELECT pg_temp.disable_other_sa((SELECT bind_id FROM _t_c2));

SELECT is(
    script.fn_check_ultimo_super_admin_attivo((SELECT au_id FROM _t_c2)),
    true,
    '3. Single super-admin: ultimo SA attivo -> true'
);

-- =========================================================
-- 4) Stesso scenario "single SA": un altro auth_user (non SA)
--    deve ricevere comunque false. Uso un auth_user OPERATORE
--    non-SA esistente.
-- =========================================================
SELECT is(
    script.fn_check_ultimo_super_admin_attivo(
        (SELECT id.auth_user_id
           FROM anagrafiche.identita_digitali id
          WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
            AND id.attivo = true
            AND id.auth_user_id <> (SELECT au_id FROM _t_c2)
            AND NOT EXISTS (
                SELECT 1
                  FROM config.profili_accesso_bindings pab
                  JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
                 WHERE pab.identita_digitale_id = id.id
                   AND pab.attivo = true
                   AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
            )
          LIMIT 1)
    ),
    false,
    '4. Auth user non-SA in scenario single SA -> false'
);

-- =========================================================
-- 5) Auth user inesistente -> false (CTE attivi non lo contiene)
-- =========================================================
SELECT is(
    script.fn_check_ultimo_super_admin_attivo(-99999),
    false,
    '5. Auth user inesistente -> false'
);

SELECT * FROM finish();
ROLLBACK;
