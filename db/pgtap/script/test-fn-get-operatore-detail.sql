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
--   I super admin si COSTRUISCONO con
--   dbops.fn_pgtap_crea_operatore_umano(..., p_super_admin := true);
--   pg_temp.disable_other_sa riduce a un solo SA per i casi 2 e 3.
--   Stato accumulato tra i casi (no SAVEPOINT) e rolled-back a fine
--   file.
--
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Il file dava un binding SA a mano a un'identita' OPERATORE
--   «vergine» pescata (pg_temp.mk_admin, copia di quello di
--   test-fn-check-ultimo-super-admin-attivo), e contava sui SA
--   preesistenti per il caso multi-SA. Su un database ricostruito
--   (la CI) i SA sono zero e l'operatore del mondo un binding ce l'ha:
--   il caso 1 rispondeva false e il setup del caso 4 moriva («nessuna
--   identita OPERATORE vergine»). Ora i SA nascono dal percorso di
--   produzione, e i casi non dipendono da chi c'era prima.
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
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
-- Helper: disattiva tutti i binding SA attivi tranne quello passato.
--   Il profilo SA si riconosce dal TIPO, non dal codice.
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
         WHERE pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
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
-- 1) Multi super-admin: se ne costruiscono DUE -> >=2 SA comunque
--    stia il database. can_disable=true sul primo.
-- =========================================================
CREATE TEMP TABLE _t_sa1 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('detail SA 1', p_super_admin := true);

CREATE TEMP TABLE _t_sa2 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('detail SA 2', p_super_admin := true);

-- Il binding SA del primo: e' quello che il caso 2 lascia attivo.
CREATE TEMP TABLE _t_c1 AS
SELECT t.identita_id AS id_id, t.auth_user_id AS au_id, pab.id AS bind_id
  FROM _t_sa1 t
  JOIN config.profili_accesso_bindings pab
    ON pab.identita_digitale_id = t.identita_id
   AND pab.attivo
  JOIN config.profili_accesso pa
    ON pa.id = pab.profilo_accesso_id
   AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso;

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
--    Strategia: costruisco un altro SA (cosi' non e' "ultimo"
--    ed evito interazioni con lo scenario 2/3). Su quell'auth_user
--    setto last_login=now() -> non invitabile.
-- =========================================================
CREATE TEMP TABLE _t_c4 AS
SELECT auth_user_id AS au_id
  FROM dbops.fn_pgtap_crea_operatore_umano('detail SA invito', p_super_admin := true);

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
