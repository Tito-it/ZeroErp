-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard anti-lockout ultimo SUPER_ADMIN (13.3.6 WIP multi-face-auth)
--   Copre 2 trigger che delegano a script.fn_check_almeno_un_super_admin_attivo:
--     - config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin
--     - anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin
--
-- Strategia:
--   - Ambiente con SUPER_ADMIN preesistenti (seed 80_data).
--   - mk_admin() crea un binding SA su un'identita OPERATORE "vergine"
--     (mai avuta un binding, per rispettare uq_...bindings_identita
--     partial unique).
--   - Stato progressivamente "sporco" tra i casi: lo stato finale viene
--     rolled-back dal BEGIN/ROLLBACK implicito alla fine del file.
--   - Niente SAVEPOINT esterni: ROLLBACK TO SAVEPOINT azzera anche il
--     counter interno di pgTAP e causa "No tests run!".
--
-- Indice test (1..3):
--    1. Scenario SANO: disattivo 1 binding SA con altri attivi -> no raise
--    2. Scenario LOCKOUT binding: disattivo l'ultimo binding SA -> raise
--    3. Scenario LOCKOUT identita: disattivo l'identita portante -> raise
--
-- BEGIN; + rollback implicito a fine file.
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

SELECT plan(3);

-- =========================================================
-- Helper: crea un binding SUPER_ADMIN ad-hoc su un'identita OPERATORE
-- "vergine" (mai avuta un binding). Ritorna (identita_id, binding_id).
-- Filtro su NOT EXISTS qualsiasi binding (attivo o meno) per rispettare
-- il vincolo uq_profili_accesso_bindings_identita (partial unique
-- WHERE identita_digitale_id IS NOT NULL).
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.mk_admin(OUT id_id bigint, OUT bind_id bigint)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT id.id INTO id_id
      FROM anagrafiche.identita_digitali id
     WHERE id.ruolo_applicativo = 'OPERATORE'
       AND id.attivo = true
       AND NOT EXISTS (
           SELECT 1
             FROM config.profili_accesso_bindings pab
            WHERE pab.identita_digitale_id = id.id
       )
     ORDER BY id.id
     LIMIT 1;

    IF id_id IS NULL THEN
        RAISE EXCEPTION 'Setup impossibile: nessuna identita OPERATORE vergine (tutte hanno gia un binding)';
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
-- Helper: disattiva TUTTI i binding SUPER_ADMIN attivi tranne quello
-- passato come parametro. Ritorna il numero disattivati.
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.disable_others(p_keep_bind_id bigint)
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
-- 1) Scenario SANO: disattivo 1 binding SA ad-hoc lasciando preesistenti
--    attivi -> il guard non scatta, fn_check resta true.
-- =========================================================
CREATE TEMP TABLE _t_c1 AS SELECT * FROM pg_temp.mk_admin();

UPDATE config.profili_accesso_bindings
   SET attivo = false
 WHERE id = (SELECT bind_id FROM _t_c1);

SELECT ok(
    script.fn_check_almeno_un_super_admin_attivo(),
    '1. Scenario sano: disattivo 1 binding SUPER_ADMIN con preesistenti attivi -> guard non scatta, sistema resta con admin'
);

-- =========================================================
-- 2) Scenario LOCKOUT binding: lascio solo il mio SA attivo, poi
--    tento di disattivarlo -> raise.
-- =========================================================
CREATE TEMP TABLE _t_c2 AS SELECT * FROM pg_temp.mk_admin();

SELECT pg_temp.disable_others((SELECT bind_id FROM _t_c2));

SELECT throws_ok(
    format(
        $sql$ UPDATE config.profili_accesso_bindings SET attivo = false WHERE id = %s $sql$,
        (SELECT bind_id FROM _t_c2)
    ),
    NULL,
    NULL,
    '2. Scenario lockout binding: UPDATE attivo=false dell''ultimo SUPER_ADMIN -> raise E_PROFILO_ULTIMO_SUPER_ADMIN'
);

-- =========================================================
-- 3) Scenario LOCKOUT identita: lascio solo il nuovo SA attivo, poi
--    disattivo l'identita portante -> raise.
--    Dopo caso 2, il binding mio caso 2 e' rimasto attivo (throws_ok
--    rolled-back l'UPDATE fallito), ma disable_others del caso 3 lo
--    disattivera'.
-- =========================================================
CREATE TEMP TABLE _t_c3 AS SELECT * FROM pg_temp.mk_admin();

SELECT pg_temp.disable_others((SELECT bind_id FROM _t_c3));

SELECT throws_ok(
    format(
        $sql$ UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = %s $sql$,
        (SELECT id_id FROM _t_c3)
    ),
    NULL,
    NULL,
    '3. Scenario lockout identita: UPDATE attivo=false sull''ultima identita con SUPER_ADMIN -> raise E_PROFILO_ULTIMO_SUPER_ADMIN'
);

SELECT * FROM finish();
