-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_user_emittenti_scope(p_auth_user_id)
--   Vista dichiarativa "scope emittenti" per il drawer Operatore
--   (Fase 2 P1 2026-04-29).
--
-- Strategia:
--   Riusa il pattern mk_admin/disable_other_sa per generare scenari
--   ultimo-SA controllabili. Setup di una riga
--   user_emittenti_fiscali transitoria su un'OPERATORE vergine per
--   esercitare il ramo SINGLE. Stato accumulato tra i casi
--   (no SAVEPOINT) e rolled-back a fine file.
--
-- Indice test (1..6):
--   1. Auth user senza righe -> scope_mode=GLOBAL, emittente_id=NULL
--   2. Auth user con riga    -> scope_mode=SINGLE, emittente_id valued
--   3. allowed_scope_modes   -> sempre ['GLOBAL','SINGLE']
--   4. emittente_descrizione -> valorizzata in SINGLE
--   5. Multi super-admin     -> can_change_scope=true (target non e' ultimo)
--   6. Single super-admin    -> can_change_scope=false + reason valorizzato
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
-- Helper: identita OPERATORE vergine (no binding) + binding SA
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
-- Setup: OPERATORE non-SA con riga GLOBAL (pesco un auth_user
-- OPERATORE attivo senza binding e senza riga in user_emittenti_fiscali)
-- =========================================================
-- 🔴 FIXTURE RICOSTRUITA il 2026-08-18 — gemella di quella in
--   test-fn-change-user-emittenti-scope, e rotta dalla stessa causa.
--   Cercava un operatore GIA' in stato GLOBAL (senza riga in
--   user_emittenti_fiscali) e si affidava al fatto che in sviluppo ne
--   esistesse uno. Il cantiere perimetro emittente (DL-A) li ha portati a
--   ZERO: la ricerca tornava vuota e l'INSERT del test 2 moriva su
--   `auth_user_id` NULL.
--   ⚠️ La precondizione non si CERCA, si COSTRUISCE: la fixture ha smesso di
--   funzionare il giorno in cui il progetto ha sistemato i dati, che e' il
--   momento peggiore per scoprirlo.
--   Il DELETE passa dall'override GUC (la tabella ha un guard sul delete) e il
--   file e' transazionale: lo scope vero torna al ROLLBACK.
CREATE TEMP TABLE _t_user_global AS
SELECT id.auth_user_id AS au_id
  FROM anagrafiche.identita_digitali id
 WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
        WHERE pab.identita_digitale_id = id.id AND pab.attivo = true
   )
 ORDER BY id.auth_user_id LIMIT 1;

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT au_id FROM _t_user_global);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

-- Setup: emittente fiscale attivo per il ramo SINGLE
CREATE TEMP TABLE _t_ef AS
SELECT ef.id AS ef_id
  FROM anagrafiche.emittenti_fiscali ef
 WHERE ef.attivo = true
 ORDER BY ef.id LIMIT 1;

-- =========================================================
-- 1) Auth user senza righe -> scope_mode=GLOBAL, emittente_id=NULL
-- =========================================================
SELECT is(
    (SELECT (scope_mode, emittente_id::text)
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_user_global))),
    -- 🔴 `'GLOBAL'::text` il 2026-08-18: senza il cast il letterale resta di tipo
    --   `unknown`, e il confronto fra RECORD pretende colonne dello stesso tipo
    --   («non e' possibile confrontare i tipi di colonne dissimili text e
    --   unknown»). Il secondo elemento il cast ce l'aveva gia': mancava al primo.
    --   ⚠️ Il file non falliva, MORIVA: 6 asserzioni su 6 mai eseguite.
    --   ⭐ Verificato che NON e' una conseguenza di P-2a (20260818-11/-12): il
    --   rosso e' storico e riguarda la forma del confronto, non il valore
    --   restituito dalla funzione.
    ROW('GLOBAL'::text, NULL::text)::record,
    '1. Senza riga in user_emittenti_fiscali -> scope_mode=GLOBAL, emittente_id NULL'
);

-- =========================================================
-- 2) Auth user con riga -> scope_mode=SINGLE, emittente_id valued
-- =========================================================
INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
VALUES ((SELECT au_id FROM _t_user_global), (SELECT ef_id FROM _t_ef));

SELECT is(
    (SELECT scope_mode FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_user_global))),
    'SINGLE',
    '2. Con riga in user_emittenti_fiscali -> scope_mode=SINGLE'
);

-- =========================================================
-- 3) allowed_scope_modes -> sempre ['GLOBAL','SINGLE']
-- =========================================================
SELECT is(
    (SELECT allowed_scope_modes
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_user_global))),
    ARRAY['GLOBAL','SINGLE']::text[],
    '3. allowed_scope_modes esposto sempre come [GLOBAL, SINGLE]'
);

-- =========================================================
-- 4) emittente_descrizione valorizzata in SINGLE
-- =========================================================
SELECT ok(
    (SELECT emittente_descrizione IS NOT NULL AND length(emittente_descrizione) > 0
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_user_global))),
    '4. emittente_descrizione valorizzata in scope SINGLE'
);

-- =========================================================
-- 5) Multi super-admin: aggiungo 1 SA ad-hoc -> >=2 SA totali.
--    Sul nuovo SA: can_change_scope=true.
-- =========================================================
CREATE TEMP TABLE _t_sa AS SELECT * FROM pg_temp.mk_admin();

SELECT is(
    (SELECT can_change_scope
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_sa))),
    true,
    '5. Multi super-admin: can_change_scope=true (target non e'' ultimo SA)'
);

-- =========================================================
-- 6) Single super-admin: disabilito tutti gli altri SA bindings
--    -> il SA di _t_sa diventa l'unico. can_change_scope=false +
--    change_scope_reason valorizzato.
-- =========================================================
SELECT pg_temp.disable_other_sa((SELECT bind_id FROM _t_sa));

SELECT is(
    (SELECT (NOT can_change_scope)
            AND change_scope_reason ILIKE '%lockout%'
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_sa))),
    true,
    '6. Single super-admin: can_change_scope=false + change_scope_reason cita lockout'
);

SELECT * FROM finish();
ROLLBACK;
