-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_check_ultimo_super_admin_attivo(p_auth_user_id)
--   Predicato per-utente per le capability can_disable /
--   can_demote_super_admin del drawer Operatore (P1 2026-04-29).
--
-- Strategia:
--   I super admin del test si COSTRUISCONO con
--   dbops.fn_pgtap_crea_operatore_umano(..., p_super_admin := true):
--   due per lo scenario multi-SA, poi si disattivano tutti gli altri
--   binding SA tranne uno per lo scenario single-SA. Lo stato finale
--   viene rolled back dal ROLLBACK a fine file.
--
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Il file PESCAVA: «SUPER_ADMIN preesistenti (seed)» e un'identita'
--   OPERATORE «vergine» a cui dare un binding a mano. Su un database
--   ricostruito (la CI) i super admin sono zero: il SA ad-hoc restava
--   l'UNICO e il caso 2 («multi-SA -> false») rispondeva true. Il seed
--   non porta super admin: sono dato di macchina. Ora ne nascono due dal
--   percorso di produzione, e il binding lo scrive la madre.
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA:
--   fn_check_ultimo_super_admin_attivo non sta mai nella stessa
--   istruzione della chiamata al builder.
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

SELECT plan(5);

-- =========================================================
-- Helper: disattiva tutti i binding SA attivi tranne quello passato.
--   Il profilo SA si riconosce dal TIPO, non dal codice: e' la chiave
--   stabile di fn_is_super_admin e dei guard anti-lockout.
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
-- 1) Guard parametro: NULL e <=0 -> false
-- =========================================================
SELECT is(
    script.fn_check_ultimo_super_admin_attivo(NULL),
    false,
    '1. NULL -> false (guard fail-closed)'
);

-- =========================================================
-- 2) Multi super-admin: se ne costruiscono DUE, quindi ce ne sono
--    >=2 comunque stia il database. Su nessuno dei due deve
--    risultare "ultimo".
-- =========================================================
CREATE TEMP TABLE _t_sa1 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('ultimo SA 1', p_super_admin := true);

CREATE TEMP TABLE _t_sa2 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('ultimo SA 2', p_super_admin := true);

-- Il binding SA del primo: e' quello che il caso 3 lascia attivo.
CREATE TEMP TABLE _t_c2 AS
SELECT t.identita_id AS id_id, t.auth_user_id AS au_id, pab.id AS bind_id
  FROM _t_sa1 t
  JOIN config.profili_accesso_bindings pab
    ON pab.identita_digitale_id = t.identita_id
   AND pab.attivo
  JOIN config.profili_accesso pa
    ON pa.id = pab.profilo_accesso_id
   AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso;

SELECT is(
    script.fn_check_ultimo_super_admin_attivo((SELECT au_id FROM _t_c2))
    OR script.fn_check_ultimo_super_admin_attivo((SELECT auth_user_id FROM _t_sa2)),
    false,
    '2. Multi super-admin (>=2 SA): nessuno dei due e'' l''ultimo -> false'
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
--    deve ricevere comunque false. L'operatore non-SA si costruisce.
-- =========================================================
CREATE TEMP TABLE _t_non_sa AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('ultimo SA non SA');

SELECT is(
    script.fn_check_ultimo_super_admin_attivo(
        (SELECT auth_user_id FROM _t_non_sa)
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
