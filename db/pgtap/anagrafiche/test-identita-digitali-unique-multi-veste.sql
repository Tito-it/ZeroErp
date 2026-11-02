-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: invarianti UNIQUE multi-veste su anagrafiche.identita_digitali
-- Riferimento: migration 20260420-01 (§3.1 guida multi-face v2.0)
--
-- Vincoli testati:
--   uq_identita_digitali_auth_user_ruolo_attivo
--     -> UNIQUE (auth_user_id, ruolo_applicativo) WHERE attivo = true
--   uq_identita_digitali_sr_ruolo_attivo
--     -> UNIQUE (soggetto_ruolo_id, ruolo_applicativo) WHERE attivo = true
--
-- Semantica attesa post 20-04-2026:
--   - un auth_user puo' avere N identita attive (una per ruolo)
--   - un soggetto_ruolo puo' avere N identita attive (una per ruolo)
--   - un SR-CL puo' avere CLIENTE_PORTALE + SHOP_CUSTOMER attive
--     contemporaneamente (stesso user o user diversi)
--   - duplicati sullo stesso (user, ruolo) attivi -> throws
--   - duplicati sullo stesso (SR, ruolo) attivi -> throws
--   - indice e' parziale: attivo=false esenta dal vincolo
--
-- Indice test (1..8):
--    1. Precondizione: fixture 2 clienti + pool 4 auth_user
--    2. CLIENTE_PORTALE su (user1, SR_CL_1) attivo -> lives_ok
--    3. SHOP_CUSTOMER su (user1, SR_CL_1) attivo -> lives_ok
--       (stesso user + stesso SR, veste diversa)
--    4. CLIENTE_PORTALE duplicato (user1, SR_CL_1) attivo -> throws
--       (violazione uq auth_user + ruolo)
--    5. CLIENTE_PORTALE su (user2, SR_CL_1) attivo -> throws
--       (violazione uq SR + ruolo: gia' CLIENTE_PORTALE attivo su SR_CL_1)
--    6. CLIENTE_PORTALE su (user2, SR_CL_1) con attivo=false -> lives_ok
--       (indice parziale non si applica a inattive)
--    7. CLIENTE_PORTALE su (user3, SR_CL_2) attivo -> lives_ok
--       (SR diverso, nessun conflitto)
--    8. Dopo disattivazione identita punto 2, insert CLIENTE_PORTALE
--       (user4, SR_CL_1) attivo -> lives_ok (unica attiva)
--
-- BEGIN; + rollback implicito a fine file (isolamento completo).
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

SELECT plan(8);

-- =========================================================
-- 1) Precondizione: 2 SR CL liberi (no identita attive,
--    soggetto attivo) + pool 4 auth_user
--    NOTA: anagrafiche.clienti NON ha UNIQUE su soggetto_ruolo_id
--    (un SR puo' avere N clienti = N righe) -> DISTINCT necessario
--    per non creare duplicati di sr_id nel fixture.
-- =========================================================
CREATE TEMP TABLE _t_sr_cl AS
WITH sr_liberi AS (
    SELECT DISTINCT sr.id AS sr_id
      FROM anagrafiche.clienti        c
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
      JOIN anagrafiche.soggetti       s  ON s.id = sr.soggetto_id
     WHERE s.attivo = true
       AND NOT EXISTS (
           SELECT 1
             FROM anagrafiche.identita_digitali id
            WHERE id.soggetto_ruolo_id = sr.id
              AND id.attivo = true
       )
)
SELECT sr_id,
       row_number() OVER (ORDER BY sr_id) AS rn
  FROM sr_liberi
 ORDER BY sr_id
 LIMIT 2;

CREATE TEMP TABLE _t_au_pool (idx int, auth_user_id int);
DO $$
DECLARE
    v_i int;
    v_id int;
BEGIN
    FOR v_i IN 1..4 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined
        )
        VALUES (
            '_pgtap_uniq_mv_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', true, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au_pool (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

SELECT ok(
    (SELECT count(*) FROM _t_sr_cl) = 2
    AND (SELECT count(*) FROM _t_au_pool) = 4,
    '1. Precondizioni: 2 SR CL + 4 auth_user pool'
);

-- =========================================================
-- Tutti i test 2-8 skippano uniformemente se fixture insufficiente
-- (count(_t_sr_cl) < 2). Pattern CASE ... THEN test ELSE skip END.
-- =========================================================

-- =========================================================
-- 2) CLIENTE_PORTALE su (user1, SR_CL_1) attivo -> lives_ok
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        lives_ok(
            format($sql$
                INSERT INTO anagrafiche.identita_digitali
                    (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
                VALUES (%s, %s, 'CLIENTE_PORTALE', true)
            $sql$,
            (SELECT sr_id FROM _t_sr_cl WHERE rn = 1),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1)),
            '2. CLIENTE_PORTALE su (user1, SR_CL_1) attivo -> ok'
        )
    ELSE skip('fixture insufficiente (<2 SR CL liberi): test 2 skippato', 1)
END;

-- =========================================================
-- 3) SHOP_CUSTOMER su (user1, SR_CL_1) attivo -> lives_ok
--    Scenario multi-canale chiave: stesso user, stesso SR,
--    veste diversa. Era impossibile pre 20-04-2026.
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        lives_ok(
            format($sql$
                INSERT INTO anagrafiche.identita_digitali
                    (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
                VALUES (%s, %s, 'SHOP_CUSTOMER', true)
            $sql$,
            (SELECT sr_id FROM _t_sr_cl WHERE rn = 1),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1)),
            '3. SHOP_CUSTOMER su (user1, SR_CL_1) attivo -> ok (multi-canale stesso user+SR)'
        )
    ELSE skip('fixture insufficiente: test 3 skippato', 1)
END;

-- =========================================================
-- 4) CLIENTE_PORTALE duplicato (user1, SR_CL_1) attivo -> throws
--    Violazione uq_identita_digitali_auth_user_ruolo_attivo
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        throws_ok(
            format($sql$
                INSERT INTO anagrafiche.identita_digitali
                    (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
                VALUES (%s, %s, 'CLIENTE_PORTALE', true)
            $sql$,
            (SELECT sr_id FROM _t_sr_cl WHERE rn = 1),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1)),
            '23505',
            NULL,
            '4. Duplicato CLIENTE_PORTALE su stesso user+SR attivo -> throws (uq auth_user+ruolo)'
        )
    ELSE skip('fixture insufficiente: test 4 skippato', 1)
END;

-- =========================================================
-- 5) CLIENTE_PORTALE su (user2, SR_CL_1) attivo -> throws
--    Violazione uq_identita_digitali_sr_ruolo_attivo:
--    gia' esiste un CLIENTE_PORTALE attivo su SR_CL_1 (punto 2).
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        throws_ok(
            format($sql$
                INSERT INTO anagrafiche.identita_digitali
                    (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
                VALUES (%s, %s, 'CLIENTE_PORTALE', true)
            $sql$,
            (SELECT sr_id FROM _t_sr_cl WHERE rn = 1),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 2)),
            '23505',
            NULL,
            '5. CLIENTE_PORTALE su SR_CL_1 con user diverso attivo -> throws (uq SR+ruolo)'
        )
    ELSE skip('fixture insufficiente: test 5 skippato', 1)
END;

-- =========================================================
-- 6) CLIENTE_PORTALE su (user2, SR_CL_1) attivo=false -> lives_ok
--    L'indice parziale non copre inattive.
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        lives_ok(
            format($sql$
                INSERT INTO anagrafiche.identita_digitali
                    (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
                VALUES (%s, %s, 'CLIENTE_PORTALE', false)
            $sql$,
            (SELECT sr_id FROM _t_sr_cl WHERE rn = 1),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 2)),
            '6. CLIENTE_PORTALE storicizzata (attivo=false) su stesso SR -> ok (parziale non copre)'
        )
    ELSE skip('fixture insufficiente: test 6 skippato', 1)
END;

-- =========================================================
-- 7) CLIENTE_PORTALE su (user3, SR_CL_2) attivo -> lives_ok
--    SR diverso: nessun conflitto.
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        lives_ok(
            format($sql$
                INSERT INTO anagrafiche.identita_digitali
                    (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
                VALUES (%s, %s, 'CLIENTE_PORTALE', true)
            $sql$,
            (SELECT sr_id FROM _t_sr_cl WHERE rn = 2),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 3)),
            '7. CLIENTE_PORTALE su SR diverso -> ok'
        )
    ELSE skip('fixture insufficiente: test 7 skippato', 1)
END;

-- =========================================================
-- 8) Dopo disattivazione identita punto 2, nuova CLIENTE_PORTALE
--    su SR_CL_1 e' ammessa (solo una attiva alla volta).
-- =========================================================
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE auth_user_id = (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1)
   AND ruolo_applicativo = 'CLIENTE_PORTALE'::config.ruolo_applicativo
   AND (SELECT count(*) FROM _t_sr_cl) = 2;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        lives_ok(
            format($sql$
                INSERT INTO anagrafiche.identita_digitali
                    (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
                VALUES (%s, %s, 'CLIENTE_PORTALE', true)
            $sql$,
            (SELECT sr_id FROM _t_sr_cl WHERE rn = 1),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 4)),
            '8. Post-disattivazione identita 2, nuova CLIENTE_PORTALE su SR_CL_1 -> ok'
        )
    ELSE skip('fixture insufficiente: test 8 skippato', 1)
END;

SELECT * FROM finish();
ROLLBACK;
