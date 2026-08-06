-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_ba_ownership ruolo-aware
-- Riferimento: migration 20260420-09 (§6.3 guida permessi).
--
-- Post 20-04-2026 la fn filtra internamente
--   id.ruolo_applicativo IN ('CLIENTE_PORTALE', 'SHOP_CUSTOMER')
-- Difesa-in-profondita: se un'identita non-cliente avesse per errore
-- un SR comune al BA, la fn deve restituire comunque false.
--
-- Scenari testabili senza conflitti col guard di coerenza su
-- identita_digitali (che impone OPERATORE su RIS_UMANA e
-- FORNITORE_PORTALE su FO):
--   - CLIENTE_PORTALE su SR_CL -> ammesso dal guard
--   - SHOP_CUSTOMER su SR_CL -> ammesso
--   - DISABILITATO su SR_CL -> ammesso (early-exit guard)
--   - identita inattiva -> indipendente dal ruolo, testa attivo=false
--
-- Indice test (1..5):
--    1. Precondizione: cliente con SR + BA
--    2. fn(identita CLIENTE_PORTALE attiva, BA) -> true
--    3. fn(identita SHOP_CUSTOMER attiva, BA) -> true
--       (test chiave: multi-canale sullo stesso SR)
--    4. fn(identita DISABILITATO attiva, BA) -> false
--       (filtro ruolo-aware esclude non-cliente)
--    5. fn(identita CLIENTE_PORTALE con attivo=false, BA) -> false
--       (fail-closed su identita inattiva)
--
-- Nota: per testare ogni caso su stesso SR servono auth_user
-- diversi (uq_sr_ruolo_attivo limita a 1 attiva per ruolo).
-- I test 2 e 3 usano lo stesso SR per esercitare multi-canale.
--
-- BEGIN; + rollback implicito.
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

SELECT plan(5);

-- =========================================================
-- 1) Precondizione: 1 SR CL libero (no identita attive, soggetto
--    attivo) con BA associato
-- =========================================================
CREATE TEMP TABLE _t_ctx AS
SELECT sr.id AS sr_cl_id,
       ba.id AS ba_id
  FROM anagrafiche.clienti         c
  JOIN anagrafiche.soggetti_ruoli  sr ON sr.id = c.soggetto_ruolo_id
  JOIN anagrafiche.soggetti        s  ON s.id  = sr.soggetto_id
  JOIN anagrafiche.billing_account ba ON ba.soggetto_ruolo_id = sr.id
 WHERE s.attivo = true
   AND NOT EXISTS (
       SELECT 1
         FROM anagrafiche.identita_digitali id
        WHERE id.soggetto_ruolo_id = sr.id
          AND id.attivo = true
   )
 ORDER BY c.soggetto_ruolo_id, ba.id
 LIMIT 1;

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
            '_pgtap_scope_ba_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', false, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au_pool (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

SELECT ok(
    (SELECT count(*) FROM _t_ctx)     = 1
    AND (SELECT count(*) FROM _t_au_pool) = 4,
    '1. Precondizioni: SR CL + BA + 4 auth_user pool'
);

-- =========================================================
-- Tutti i test 2-5 skippano uniformemente se fixture insufficiente
-- (count(_t_ctx) = 0). Gli INSERT in DO block sono gate'd con
-- IF EXISTS (_t_ctx) per evitare NULL propagato a zeroerp.test_id_*.
-- =========================================================

-- =========================================================
-- 2) CLIENTE_PORTALE attiva + BA stesso SR -> true
-- =========================================================
DO $$
DECLARE
    v_id bigint;
BEGIN
    IF EXISTS (SELECT 1 FROM _t_ctx) THEN
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (
            (SELECT sr_cl_id FROM _t_ctx),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1),
            'CLIENTE_PORTALE', true
        ) RETURNING id INTO v_id;

        PERFORM set_config('zeroerp.test_id_1', v_id::text, true);
    END IF;
END
$$;

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_ctx) THEN
        is(
            script.fn_scope_ba_ownership(
                current_setting('zeroerp.test_id_1')::bigint,
                (SELECT ba_id FROM _t_ctx)
            ),
            true,
            '2. CLIENTE_PORTALE attiva + BA stesso SR -> true'
        )
    ELSE skip('fixture insufficiente (no SR CL libero con BA): test 2 skippato', 1)
END;

-- =========================================================
-- 3) SHOP_CUSTOMER attiva su stesso SR (user diverso) + BA -> true
--    Multi-canale: la stessa policy scope ammette entrambe.
-- =========================================================
DO $$
DECLARE
    v_id bigint;
BEGIN
    IF EXISTS (SELECT 1 FROM _t_ctx) THEN
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (
            (SELECT sr_cl_id FROM _t_ctx),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 2),
            'SHOP_CUSTOMER', true
        ) RETURNING id INTO v_id;

        PERFORM set_config('zeroerp.test_id_2', v_id::text, true);
    END IF;
END
$$;

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_ctx) THEN
        is(
            script.fn_scope_ba_ownership(
                current_setting('zeroerp.test_id_2')::bigint,
                (SELECT ba_id FROM _t_ctx)
            ),
            true,
            '3. SHOP_CUSTOMER attiva + BA stesso SR -> true (multi-canale)'
        )
    ELSE skip('fixture insufficiente: test 3 skippato', 1)
END;

-- =========================================================
-- 4) DISABILITATO attiva + BA stesso SR -> false
--    La fn filtra id.ruolo_applicativo IN (CLIENTE_PORTALE, SHOP_CUSTOMER)
--    -> DISABILITATO non passa anche se l'identita e' attiva e il
--    SR coincide.
-- =========================================================
DO $$
DECLARE
    v_id bigint;
BEGIN
    IF EXISTS (SELECT 1 FROM _t_ctx) THEN
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (
            (SELECT sr_cl_id FROM _t_ctx),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 3),
            'DISABILITATO', true
        ) RETURNING id INTO v_id;

        PERFORM set_config('zeroerp.test_id_3', v_id::text, true);
    END IF;
END
$$;

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_ctx) THEN
        is(
            script.fn_scope_ba_ownership(
                current_setting('zeroerp.test_id_3')::bigint,
                (SELECT ba_id FROM _t_ctx)
            ),
            false,
            '4. DISABILITATO attiva + BA stesso SR -> false (filtro ruolo-aware)'
        )
    ELSE skip('fixture insufficiente: test 4 skippato', 1)
END;

-- =========================================================
-- 5) CLIENTE_PORTALE con attivo=false -> false (fail-closed)
-- =========================================================
DO $$
DECLARE
    v_id bigint;
BEGIN
    IF EXISTS (SELECT 1 FROM _t_ctx) THEN
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (
            (SELECT sr_cl_id FROM _t_ctx),
            (SELECT auth_user_id FROM _t_au_pool WHERE idx = 4),
            'CLIENTE_PORTALE', false
        ) RETURNING id INTO v_id;

        PERFORM set_config('zeroerp.test_id_4', v_id::text, true);
    END IF;
END
$$;

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_ctx) THEN
        is(
            script.fn_scope_ba_ownership(
                current_setting('zeroerp.test_id_4')::bigint,
                (SELECT ba_id FROM _t_ctx)
            ),
            false,
            '5. CLIENTE_PORTALE con attivo=false + BA -> false (fail-closed su attivo)'
        )
    ELSE skip('fixture insufficiente: test 5 skippato', 1)
END;

SELECT * FROM finish();
ROLLBACK;
