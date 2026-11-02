-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_sync_auth_user_is_active — scenario transizionale
-- Riferimento:
--   - migration 20260420-10 (semantica OR multi-veste)
--   - trigger trg_identita_digitali_z90_sync_auth_user_active_upd
--     (migration 20260418-75)
--   - handoff 20260421: bug osservato in smoke §8.3.9 — UPDATE
--     identita 19 SET attivo=false ha portato auth_user.is_active=false
--     pur avendo identita 24 CLIENTE_PORTALE ancora attiva.
--
-- Obiettivo diagnostico: riprodurre il caso transizionale "2 identita
-- attive → disattivo 1 → is_active deve restare true" che i 6 test
-- statici esistenti (test-fn-sync-auth-user-is-active-or.sql) NON
-- coprono. Se T3 passa, il bug osservato in smoke e' dato-dipendente
-- (p.es. soggetto parent di identita 24 disattivo o finestra temporale
-- fuori range), non un bug della funzione. Se T3 fallisce, bug reale
-- nella semantica OR o nel trigger.
--
-- Strategia: 1 auth_user fresco + 2 SR CL liberi con soggetti parent
-- attivi. Insert 2 identita attive, verifico is_active=true via OR.
-- Poi UPDATE a cascata (una alla volta) e verifico la soglia: finche'
-- almeno una identita e' utilizzabile, is_active resta true. Quando
-- tutte sono disattivate, is_active passa a false.
--
-- Il trigger AFTER UPDATE OF attivo chiama gia' la sync; la chiamata
-- esplicita dopo ogni UPDATE funge da "assert di coerenza" (idempotente).
--
-- Indice test (1..4):
--    1. Precondizione: 2 SR CL liberi + 1 auth_user
--    2. Baseline: 2 identita attive (CLIENTE_PORTALE + SHOP_CUSTOMER)
--       -> is_active=true
--    3. BUG KEY: UPDATE identita #1 SET attivo=false, identita #2 resta
--       attiva -> is_active=true (OR tiene)
--    4. Negativo: UPDATE anche identita #2 SET attivo=false
--       -> is_active=false (nessuna identita utilizzabile)
--
-- Vincoli di test: fixture 2 SR CL **liberi** (senza identita attive e
-- con soggetto attivo) per evitare collisioni con l'indice parziale
-- uq_identita_digitali_sr_ruolo_attivo. Skip-safe se ne trova <2.
--
-- BEGIN; + rollback implicito.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- =========================================================
-- 1) Precondizione: 2 SR CL liberi + 1 auth_user fresco
--    NOTA: anagrafiche.clienti NON ha UNIQUE su soggetto_ruolo_id
--    (un SR-CL puo' avere N clienti, uno per istanza utility).
--    CTE con DISTINCT garantisce SR univoci prima del row_number().
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


CREATE TEMP TABLE _t_au (auth_user_id int);
DO $$
DECLARE
    v_id int;
BEGIN
    INSERT INTO django.auth_user (
        username, password, is_active, is_staff, is_superuser,
        first_name, last_name, email, date_joined
    )
    VALUES (
        '_pgtap_sync_transizione_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', false, false, false, '', '', '', now()
    )
    RETURNING id INTO v_id;
    INSERT INTO _t_au (auth_user_id) VALUES (v_id);
END
$$;

SELECT ok(
    (SELECT count(*) FROM _t_sr_cl) = 2
    AND (SELECT count(*) FROM _t_au) = 1,
    '1. Precondizioni: 2 SR CL liberi + 1 auth_user'
);

-- =========================================================
-- Tutti gli INSERT/UPDATE sono gate'd su 'count(_t_sr_cl) = 2'
-- via WHERE clause: se la fixture non e' completa, nessuna
-- mutazione viene fatta e i test 2-4 skippano uniformemente.
-- =========================================================

-- =========================================================
-- 2) Baseline: 2 identita attive stesso auth_user
--    (CLIENTE_PORTALE + SHOP_CUSTOMER su 2 SR CL diversi)
--    -> is_active=true (OR ha 2 candidati utilizzabili)
-- =========================================================
INSERT INTO anagrafiche.identita_digitali
    (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
SELECT
    (SELECT sr_id FROM _t_sr_cl WHERE rn = 1),
    (SELECT auth_user_id FROM _t_au),
    'CLIENTE_PORTALE'::config.ruolo_applicativo, true
 WHERE (SELECT count(*) FROM _t_sr_cl) = 2
UNION ALL
SELECT
    (SELECT sr_id FROM _t_sr_cl WHERE rn = 2),
    (SELECT auth_user_id FROM _t_au),
    'SHOP_CUSTOMER'::config.ruolo_applicativo, true
 WHERE (SELECT count(*) FROM _t_sr_cl) = 2;

-- Assert di coerenza: il trigger AFTER INSERT ha gia' chiamato la sync;
-- la chiamata esplicita e' idempotente e documenta l'intento.
SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT auth_user_id FROM _t_au)
)
 WHERE (SELECT count(*) FROM _t_sr_cl) = 2;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        is(
            (SELECT is_active FROM django.auth_user
              WHERE id = (SELECT auth_user_id FROM _t_au)),
            true,
            '2. Baseline: 2 identita attive -> is_active=true'
        )
    ELSE skip('fixture insufficiente (<2 SR CL liberi): test 2 skippato', 1)
END;

-- =========================================================
-- 3) BUG KEY: disattivo identita #1 (CLIENTE_PORTALE).
--    Identita #2 (SHOP_CUSTOMER) resta attiva e utilizzabile.
--    Atteso: is_active=true (OR tiene grazie a identita #2).
--    Se questo test fallisce, confermato bug nella funzione
--    fn_sync_auth_user_is_active o nel trigger associato.
-- =========================================================
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE soggetto_ruolo_id = (SELECT sr_id FROM _t_sr_cl WHERE rn = 1)
   AND auth_user_id     = (SELECT auth_user_id FROM _t_au)
   AND (SELECT count(*) FROM _t_sr_cl) = 2;

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT auth_user_id FROM _t_au)
)
 WHERE (SELECT count(*) FROM _t_sr_cl) = 2;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        is(
            (SELECT is_active FROM django.auth_user
              WHERE id = (SELECT auth_user_id FROM _t_au)),
            true,
            '3. BUG KEY: disattivo 1 su 2 identita -> is_active=true (OR tiene)'
        )
    ELSE skip('fixture insufficiente: test 3 skippato', 1)
END;

-- =========================================================
-- 4) Negativo: disattivo anche identita #2 (SHOP_CUSTOMER).
--    Nessuna identita utilizzabile.
--    Atteso: is_active=false.
-- =========================================================
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE soggetto_ruolo_id = (SELECT sr_id FROM _t_sr_cl WHERE rn = 2)
   AND auth_user_id     = (SELECT auth_user_id FROM _t_au)
   AND (SELECT count(*) FROM _t_sr_cl) = 2;

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT auth_user_id FROM _t_au)
)
 WHERE (SELECT count(*) FROM _t_sr_cl) = 2;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 2 THEN
        is(
            (SELECT is_active FROM django.auth_user
              WHERE id = (SELECT auth_user_id FROM _t_au)),
            false,
            '4. Negativo: disattivo entrambe -> is_active=false'
        )
    ELSE skip('fixture insufficiente: test 4 skippato', 1)
END;

SELECT * FROM finish();
ROLLBACK;
