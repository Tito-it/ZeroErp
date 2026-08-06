-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_operatore_detail(p_auth_user_id) — capability
--   Drawer Operatore P1 2026-04-29. Verifica i 6 campi capability:
--     can_invite, invite_reason
--     can_disable, disable_reason
--     can_demote_super_admin, demote_reason
--   I campi anagrafici sono ereditati dalla query inline pre-esistente
--   (gia' coperta in produzione) -> qui si verificano solo le capability.
--
-- Strategia:
--   Riusa il pattern mk_admin/disable_other_sa di
--   test-fn-check-ultimo-super-admin-attivo.sql (ogni file pgTAP ha
--   il proprio pg_temp namespace). Stato accumulato tra i casi
--   (no SAVEPOINT) e rolled-back a fine file.
--
-- Indice test (1..4):
--   1. Multi super-admin -> can_disable=true sull'auth_user SA target
--   2. Single super-admin -> can_disable=false + disable_reason valorizzata
--   3. Demote bloccato (single SA) -> can_demote_super_admin=false
--                                       + demote_reason valorizzata
--   4. Invite con last_login -> can_invite=false + invite_reason
--                                contiene 'login'
--
-- Niente SAVEPOINT (azzera il counter pgTAP).
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- =========================================================
-- Helper: aggiunge un binding SA su un'identita OPERATORE vergine
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
-- Helper: disattiva tutti i binding SA attivi tranne quello passato
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
-- 1) Multi super-admin: aggiungo 1 SA ad-hoc -> >=2 SA in totale.
--    can_disable=true sul nuovo SA.
-- =========================================================
CREATE TEMP TABLE _t_c1 AS SELECT * FROM pg_temp.mk_admin();

SELECT is(
    (SELECT can_disable
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c1))),
    true,
    '1. Multi super-admin: can_disable=true (esiste un altro SA, no lockout)'
);

-- =========================================================
-- 2) Single super-admin: disattivo tutti gli altri binding SA.
--    Ora _t_c1 e' l'unico SA -> can_disable=false + reason valorizzata.
-- =========================================================
SELECT pg_temp.disable_other_sa((SELECT bind_id FROM _t_c1));

SELECT is(
    (SELECT (NOT can_disable) AND disable_reason ILIKE '%lockout%'
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c1))),
    true,
    '2. Single super-admin: can_disable=false + disable_reason cita lockout'
);

-- =========================================================
-- 3) Demote bloccato (stesso scenario): l'unico SA non puo'
--    perdere il binding. can_demote_super_admin=false +
--    demote_reason valorizzata (e diversa da disable_reason).
-- =========================================================
SELECT is(
    (SELECT (can_demote_super_admin = false)
            AND demote_reason ILIKE '%binding%'
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c1))),
    true,
    '3. Demote bloccato: can_demote_super_admin=false + demote_reason cita "binding"'
);

-- =========================================================
-- 4) Invite con last_login: forzo last_login NOT NULL su un user
--    che altrimenti sarebbe invitabile. can_invite=false e
--    invite_reason cita 'login'.
--
--    Strategia: aggiungo un altro SA ad-hoc (cosi' non e' "ultimo"
--    ed evito interazioni con lo scenario 2/3). Su quell'auth_user
--    setto last_login=now() -> non invitabile.
-- =========================================================
CREATE TEMP TABLE _t_c4 AS SELECT * FROM pg_temp.mk_admin();

-- Forzo email valorizzata + last_login != NULL: cosi' fn_check_operatore_invitabile
-- supera tutti i guard precedenti e fallisce specificatamente sul last_login.
UPDATE django.auth_user
   SET email      = COALESCE(NULLIF(email, ''), 'pgtap+invite@example.com'),
       last_login = now()
 WHERE id = (SELECT au_id FROM _t_c4);

SELECT is(
    (SELECT (NOT can_invite) AND invite_reason ILIKE '%login%'
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c4))),
    true,
    '4. Invite con last_login: can_invite=false + invite_reason cita "login"'
);

SELECT * FROM finish();
ROLLBACK;
