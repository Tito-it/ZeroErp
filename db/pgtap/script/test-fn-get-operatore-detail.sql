-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- Indice test (1..7):
--   1. Multi super-admin -> can_disable=true sull'auth_user SA target
--   2. Single super-admin -> can_disable=false + ULTIMO_SUPER_ADMIN e la
--      chiave del disabilita
--   3. Demote bloccato (single SA) -> can_demote_super_admin=false
--      + ULTIMO_SUPER_ADMIN e la chiave del demote (diversa da quella del 2)
--   4. Invite su veste gia' ATTIVA -> can_invite=false + VESTE_GIA_ATTIVA
--                                e la sua chiave (rev 2026-09-25: la regola
--                                unica dell'invito, D-8 — last_login non
--                                decide piu'; 20260925-43)
--   5. veste_attiva = true per la veste accesa (rev 20260925-54, R-9)
--   6. ⭐ veste attiva + una copia spenta: UNA riga, e mostra l'attiva
--   7. ⭐ due vesti spente: UNA riga, veste_attiva=false, e l'invito non e'
--      offerto (motivo di fn_check_operatore_invitabile, rev -53)
--   8. la data di fine del rapporto (rev 20261007-27): con due SA senza
--      scadenza (c1, c4) can_set_valido_al=true, motivo e chiave NULL; e
--      anche per l'operatore non SA
--   9. il rapporto di c4 riceve una data di fine (permesso: c1 non scade):
--      ora c1 e' l'ultimo senza scadenza -> can_set_valido_al=false,
--      ULTIMO_SUPER_ADMIN e la chiave PROPRIA della data di fine
--  10. c4, che una data di fine ce l'ha gia': can_set_valido_al=true,
--      motivo e chiave NULL (il campo resta modificabile, anche per toglierla)
--
-- ⭐ Rev 20260927-02 (brief-db-blocco-login-per-credenziale §16): i motivi
--   sono CODICI con la chiave i18n (*_reason + *_reason_key), non frasi. I
--   casi pinnano la coppia; prima pinnavano parole delle frasi (ILIKE).
--   Casi 1 e 4 anche i NULL: ammessa => motivo e chiave vuoti.
--
-- ⭐ Rev 20261007-27 (brief-db-veste-utilizzabile §10): la terna della data
--   di fine del rapporto (can_set_valido_al, valido_al_reason,
--   valido_al_reason_key). Dal giro 2 «ultimo SUPER_ADMIN» vuol dire «ultimo
--   SENZA SCADENZA» (-17), e il guard -20 rifiuta la data di fine sul suo
--   rapporto: il drawer deve saperlo prima. Casi 8-10 in coda, sullo stato
--   lasciato dal 7 (SA attivi: c1 e c4, entrambi senza date di fine).
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

SELECT plan(10);

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
    (SELECT can_disable || '|' || (disable_reason IS NULL AND disable_reason_key IS NULL
                                   AND demote_reason IS NULL AND demote_reason_key IS NULL)
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c1))),
    'true|true',
    '1. Multi super-admin: can_disable=true, motivi e chiavi di disable/demote NULL'
);

-- =========================================================
-- 2) Single super-admin: disattivo tutti gli altri binding SA.
--    Ora _t_c1 e' l'unico SA -> can_disable=false + reason valorizzata.
-- =========================================================
SELECT pg_temp.disable_other_sa((SELECT bind_id FROM _t_c1));

SELECT is(
    (SELECT can_disable || '|' || disable_reason || '|' || disable_reason_key
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c1))),
    'false|ULTIMO_SUPER_ADMIN|amministrazione.operatori.disabilita_reason.ultimo_super_admin',
    '2. Single super-admin: can_disable=false, ULTIMO_SUPER_ADMIN + chiave del disabilita'
);

-- =========================================================
-- 3) Demote bloccato (stesso scenario): l'unico SA non puo'
--    perdere il binding. can_demote_super_admin=false +
--    demote_reason valorizzata (e diversa da disable_reason).
-- =========================================================
SELECT is(
    (SELECT can_demote_super_admin || '|' || demote_reason || '|' || demote_reason_key
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c1))),
    'false|ULTIMO_SUPER_ADMIN|amministrazione.operatori.rimuovi_super_admin_reason.ultimo_super_admin',
    '3. Demote bloccato: can_demote_super_admin=false, ULTIMO_SUPER_ADMIN + chiave del demote'
);

-- =========================================================
-- 4) Invite su veste gia' ATTIVA: can_invite=false e invite_reason
--    cita 'attiva'.
--
--    ⭐ Rev 2026-09-25 (brief-db-blocco-login-per-credenziale §12,
--    20260925-43): fino a quel giorno il caso era «last_login NOT NULL
--    -> non invitabile». Con la regola unica dell'invito (D-8) si invita
--    chi ha la veste SPENTA, e last_login non decide piu': il rifiuto
--    viene dalla veste gia' attiva, che il builder accende. L'UPDATE di
--    last_login resta, a dire che anche con un accesso registrato il
--    motivo e' la veste, non il login.
--
--    Strategia: costruisco un altro SA (cosi' non e' "ultimo"
--    ed evito interazioni con lo scenario 2/3).
-- =========================================================
CREATE TEMP TABLE _t_c4 AS
SELECT auth_user_id AS au_id, identita_id AS id_id
  FROM dbops.fn_pgtap_crea_operatore_umano('detail SA invito', p_super_admin := true);

-- Email valorizzata + last_login != NULL: il rifiuto deve arrivare dalla
-- veste attiva, non dal login.
UPDATE django.auth_user
   SET email      = COALESCE(NULLIF(email, ''), 'pgtap+invite@example.com'),
       last_login = now()
 WHERE id = (SELECT au_id FROM _t_c4);

SELECT is(
    (SELECT can_invite || '|' || invite_reason || '|' || invite_reason_key
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c4))),
    'false|VESTE_GIA_ATTIVA|amministrazione.operatori.invito_reason.veste_gia_attiva',
    '4. Invite su veste gia'' attiva: can_invite=false, VESTE_GIA_ATTIVA + chiave'
);

-- =========================================================
-- 5-7) La veste mostrata e il suo stato (rev 20260925-54, R-9).
--   Il modello ammette piu' vesti OPERATORE spente sulla stessa
--   credenziale (l'unique vale solo WHERE attivo): prima il JOIN
--   nudo dava una riga per veste. Le copie spente si fabbricano qui.
-- =========================================================
SELECT is(
    (SELECT veste_attiva
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c4))),
    true,
    '5. veste_attiva = true per la veste OPERATORE accesa'
);

INSERT INTO anagrafiche.identita_digitali
       (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo, valido_dal)
SELECT idg.soggetto_ruolo_id, idg.auth_user_id, idg.ruolo_applicativo, false, idg.valido_dal
  FROM anagrafiche.identita_digitali idg
 WHERE idg.id = (SELECT id_id FROM _t_c4);

SELECT is(
    (SELECT count(*) || '|' || bool_and(veste_attiva)
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c4))),
    '1|true',
    '6. veste attiva + una spenta: UNA riga, e mostra quella attiva'
);

-- Un operatore non SA con la veste spenta, e una seconda veste spenta.
CREATE TEMP TABLE _t_c7 AS
SELECT auth_user_id AS au_id, identita_id AS id_id
  FROM dbops.fn_pgtap_crea_operatore_umano('detail due spente', p_super_admin := false);

UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE id = (SELECT id_id FROM _t_c7);

INSERT INTO anagrafiche.identita_digitali
       (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo, valido_dal)
SELECT idg.soggetto_ruolo_id, idg.auth_user_id, idg.ruolo_applicativo, false, idg.valido_dal
  FROM anagrafiche.identita_digitali idg
 WHERE idg.id = (SELECT id_id FROM _t_c7);

SELECT is(
    (SELECT count(*) || '|' || bool_and(NOT veste_attiva)
                     || '|' || bool_and(NOT can_invite)
                     || '|' || string_agg(invite_reason || '|' || invite_reason_key, ',')
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c7))),
    '1|true|true|PIU_VESTI_SPENTE|amministrazione.operatori.invito_reason.piu_vesti_spente',
    '7. due vesti spente: UNA riga, veste_attiva=false, invito non offerto (PIU_VESTI_SPENTE)'
);

-- =========================================================
-- 8-10) La data di fine del rapporto (rev 20261007-27).
--   Qui i SA attivi sono c1 (il binding che il caso 2 ha tenuto) e c4
--   (costruito dopo), tutti e due senza date di fine.
-- =========================================================
SELECT is(
    (SELECT string_agg(can_set_valido_al || '|' || (valido_al_reason IS NULL
                                                     AND valido_al_reason_key IS NULL),
                       ',')
       FROM (SELECT * FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c1))
             UNION ALL
             SELECT * FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c7))) d),
    'true|true,true|true',
    '8. due SA senza scadenza, e un operatore non SA: can_set_valido_al=true, motivo e chiave NULL'
);

-- Il rapporto di c4 riceve una data di fine: permesso, c1 non scade.
UPDATE anagrafiche.risorse_umane ru
   SET valido_al = script.fn_data_operativa() + 30
  FROM anagrafiche.identita_digitali idg
 WHERE idg.id = (SELECT id_id FROM _t_c4)
   AND ru.soggetto_ruolo_id = idg.soggetto_ruolo_id;

SELECT is(
    (SELECT can_set_valido_al || '|' || valido_al_reason || '|' || valido_al_reason_key
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c1))),
    'false|ULTIMO_SUPER_ADMIN|amministrazione.operatori.valido_al_reason.ultimo_super_admin',
    '9. ultimo SA senza scadenza: can_set_valido_al=false, ULTIMO_SUPER_ADMIN + chiave della data di fine'
);

SELECT is(
    (SELECT can_set_valido_al || '|' || (valido_al_reason IS NULL AND valido_al_reason_key IS NULL)
       FROM script.fn_get_operatore_detail((SELECT au_id FROM _t_c4))),
    'true|true',
    '10. SA che ha gia'' una data di fine: can_set_valido_al=true, motivo e chiave NULL'
);

SELECT * FROM finish();
ROLLBACK;
