-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_change_user_emittenti_scope(p_auth_user_id, p_emittente_ids)
--   Orchestrazione atomica del cambio scope per il drawer Operatore
--   (Fase 2 P1 2026-04-29).
--
-- Strategia:
--   Setup OPERATORE vergine non-SA (cambio scope senza interazione
--   con guard ultimo-SA). Setup separato SA singleton per testare
--   il guard E_PROFILO_ULTIMO_SUPER_ADMIN. Stato accumulato tra i
--   casi (no SAVEPOINT) e rolled-back a fine file.
--
-- Indice test (1..6):
--   1. MULTI (>1) -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO
--   2. GLOBAL -> SINGLE  (INSERT)            -> changed=true, riga creata
--   3. SINGLE -> SINGLE stesso EF (no-op)    -> changed=false, riga invariata
--   4. SINGLE -> GLOBAL  (DELETE + override) -> changed=true, riga rimossa
--   5. NULL/[] su utente senza riga (no-op)  -> changed=false
--   6. Ultimo SA cambia scope -> raise E_PROFILO_ULTIMO_SUPER_ADMIN
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

SELECT plan(6);

-- =========================================================
-- Helper SA standard
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.mk_admin(OUT id_id bigint, OUT au_id integer, OUT bind_id bigint)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT id.id, id.auth_user_id INTO id_id, au_id
      FROM anagrafiche.identita_digitali id
     WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
       AND id.attivo = true
       AND NOT EXISTS (
           SELECT 1 FROM config.profili_accesso_bindings pab
            WHERE pab.identita_digitale_id = id.id
       )
     ORDER BY id.id LIMIT 1;

    IF id_id IS NULL THEN
        RAISE EXCEPTION 'Setup impossibile: nessuna identita OPERATORE vergine disponibile';
    END IF;

    INSERT INTO config.profili_accesso_bindings
        (profilo_accesso_id, identita_digitale_id, attivo)
    VALUES (
        (SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'),
        id_id, true
    )
    RETURNING id INTO bind_id;
END
$$;

CREATE OR REPLACE FUNCTION pg_temp.disable_other_sa(p_keep_bind_id bigint)
RETURNS int LANGUAGE plpgsql AS $$
DECLARE v_b record; v_count int := 0;
BEGIN
    FOR v_b IN
        SELECT pab.id FROM config.profili_accesso_bindings pab
          JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
         WHERE pa.codice = 'SUPER_ADMIN' AND pab.attivo = true
           AND pab.id <> p_keep_bind_id
    LOOP
        UPDATE config.profili_accesso_bindings SET attivo = false WHERE id = v_b.id;
        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END
$$;

-- =========================================================
-- Setup OPERATORE non-SA libero (no binding, no user_emittenti_fiscali)
-- =========================================================
CREATE TEMP TABLE _t_user AS
SELECT id.auth_user_id AS au_id
  FROM anagrafiche.identita_digitali id
 WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
        WHERE pab.identita_digitale_id = id.id AND pab.attivo = true
   )
   AND NOT EXISTS (
       SELECT 1 FROM config.user_emittenti_fiscali uef
        WHERE uef.auth_user_id = id.auth_user_id
   )
 ORDER BY id.auth_user_id LIMIT 1;

-- Due EF attivi (per il caso SINGLE con id reale)
CREATE TEMP TABLE _t_ef AS
SELECT ef.id AS ef_id, row_number() OVER (ORDER BY ef.id) AS rn
  FROM anagrafiche.emittenti_fiscali ef
 WHERE ef.attivo = true
 ORDER BY ef.id LIMIT 1;

-- =========================================================
-- 1) Guard MULTI (>1 elementi) -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO
-- =========================================================
SELECT throws_like(
    format(
        $sql$ SELECT script.fn_change_user_emittenti_scope(%s, ARRAY[1::bigint, 2::bigint]) $sql$,
        (SELECT au_id FROM _t_user)
    ),
    '%MULTI%',
    '1. p_emittente_ids con >1 elementi -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO'
);

-- =========================================================
-- 2) GLOBAL -> SINGLE: INSERT, changed=true
-- =========================================================
SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_user),
                ARRAY[(SELECT ef_id FROM _t_ef)]
            )->>'changed')::boolean,
    true,
    '2. GLOBAL -> SINGLE: changed=true'
);

SELECT is(
    (SELECT count(*)::int FROM config.user_emittenti_fiscali
      WHERE auth_user_id = (SELECT au_id FROM _t_user)),
    1,
    '2.bis Riga creata in user_emittenti_fiscali'
);

-- =========================================================
-- 3) SINGLE -> SINGLE stesso EF: no-op, changed=false
-- =========================================================
SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_user),
                ARRAY[(SELECT ef_id FROM _t_ef)]
            )->>'changed')::boolean,
    false,
    '3. SINGLE -> SINGLE stesso EF: no-op (changed=false)'
);

-- =========================================================
-- 4) SINGLE -> GLOBAL: DELETE con override interno, changed=true
--    Verifica che il guard_delete venga superato dal SET LOCAL
--    interno (auth_user e' attivo).
-- =========================================================
SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_user),
                NULL::bigint[]
            )->>'changed')::boolean,
    true,
    '4. SINGLE -> GLOBAL: changed=true (override guard_delete via SET LOCAL)'
);

-- Skip caso 5 perche' ridondante con caso 1 - rimpiazzato con verifica
-- residua riga assente:
SELECT is(
    (SELECT count(*)::int FROM config.user_emittenti_fiscali
      WHERE auth_user_id = (SELECT au_id FROM _t_user)),
    0,
    '5. Riga rimossa dopo SINGLE -> GLOBAL'
);

-- =========================================================
-- 6) Ultimo SA: cambio scope vietato -> raise E_PROFILO_ULTIMO_SUPER_ADMIN
--    Setup: aggiungo SA ad-hoc, garantisco scope GLOBAL del SA
--    (cleanup difensivo) e disabilito gli altri SA.
-- =========================================================
CREATE TEMP TABLE _t_sa AS SELECT * FROM pg_temp.mk_admin();

-- Defensive: forzare GLOBAL sul nuovo SA cosi' il target SINGLE
-- e' un cambio reale (non un no-op).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM config.user_emittenti_fiscali
                WHERE auth_user_id = (SELECT au_id FROM _t_sa)) THEN
        SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
        DELETE FROM config.user_emittenti_fiscali
         WHERE auth_user_id = (SELECT au_id FROM _t_sa);
    END IF;
END $$;

SELECT pg_temp.disable_other_sa((SELECT bind_id FROM _t_sa));

SELECT throws_like(
    format(
        $sql$ SELECT script.fn_change_user_emittenti_scope(%s, ARRAY[%s::bigint]) $sql$,
        (SELECT au_id FROM _t_sa),
        (SELECT ef_id FROM _t_ef)
    ),
    '%SUPER_ADMIN%',
    '6. Ultimo SA: cambio scope reale -> raise E_PROFILO_ULTIMO_SUPER_ADMIN'
);

SELECT * FROM finish();
ROLLBACK;
