-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un cliente fatturabile con il suo
--   billing account. Come `zeroerp_app` l'INSERT del BA muore al RETURNING
--   quando l'emittente di chi agisce non e' quello di default (la policy di
--   lettura risolve il BA non ancora mappato sul default; il legame lo scrive
--   un trigger AFTER). Il soggetto del test e' script.fn_scope_ba_ownership,
--   che prende identita' e BA come parametri: il ruolo di connessione non
--   cambia cio' che misura.
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
--   - API_CLIENT su SR_CL -> ammesso (early-exit guard)
--     ⚠️ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): era
--     DISABILITATO, che la tabella viva ora rifiuta. API_CLIENT e' l'unico
--     altro tipo che il guard ammette su un ruolo cliente, ed e' proprio
--     «un'identita non-cliente su un SR comune al BA».
--   - identita inattiva -> indipendente dal ruolo, testa attivo=false
--
-- Indice test (1..5):
--    1. Precondizione: cliente con SR + BA (costruito)
--    2. fn(identita CLIENTE_PORTALE attiva, BA) -> true
--    3. fn(identita SHOP_CUSTOMER attiva, BA) -> true
--       (test chiave: multi-canale sullo stesso SR)
--    4. fn(identita API_CLIENT attiva, BA) -> false
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

-- ⛔ IL CLIENTE SI COSTRUISCE, non si cerca (2026-09-12): fino a quel giorno il
--   file pescava un cliente «libero» con BA fra quelli ESISTENTI e, se non lo
--   trovava, SALTAVA i test 2-5 — su un database ricostruito dai changelog era
--   rosso al test 1 e saltato in tutto il resto (verde per sottrazione). Ora:
--   un'azienda con `dbops.fn_pgtap_crea_emittente_operatore()` per il contesto
--   e un cliente con `dbops.fn_pgtap_crea_cliente_ba()` legato a lei, PRIMA
--   del contesto (con un operatore in sessione il trigger z90 del BA
--   scriverebbe un secondo legame). Niente piu' rami `skip`.
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _t_ctx AS
SELECT c.soggetto_ruolo_id  AS sr_cl_id,
       c.billing_account_id AS ba_id
  FROM dbops.fn_pgtap_crea_cliente_ba(
           'scope BA ruolo-aware', NULL, (SELECT soggetto_ruolo_id FROM _t_mondo)) c;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _t_mondo));
END $ctx$;

SELECT plan(5);

-- =========================================================
-- 1) Precondizione: il SR CL costruito, con BA e senza identita'
-- =========================================================
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
    (SELECT count(*) FROM _t_ctx) = 1
    AND NOT EXISTS (SELECT 1 FROM anagrafiche.identita_digitali id
                     WHERE id.soggetto_ruolo_id = (SELECT sr_cl_id FROM _t_ctx))
    AND (SELECT count(*) FROM _t_au_pool) = 4,
    '1. Precondizioni: SR CL costruito, con BA, senza identita'', + 4 auth_user pool'
);

-- =========================================================
-- 2) CLIENTE_PORTALE attiva + BA stesso SR -> true
-- =========================================================
DO $$
DECLARE
    v_id bigint;
BEGIN
    v_id := anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 1), (SELECT sr_cl_id FROM _t_ctx), 'CLIENTE_PORTALE', true);

    PERFORM set_config('zeroerp.test_id_1', v_id::text, true);
END
$$;

SELECT is(
    script.fn_scope_ba_ownership(
        current_setting('zeroerp.test_id_1')::bigint,
        (SELECT ba_id FROM _t_ctx)
    ),
    true,
    '2. CLIENTE_PORTALE attiva + BA stesso SR -> true'
);

-- =========================================================
-- 3) SHOP_CUSTOMER attiva su stesso SR (user diverso) + BA -> true
--    Multi-canale: la stessa policy scope ammette entrambe.
-- =========================================================
DO $$
DECLARE
    v_id bigint;
BEGIN
    v_id := anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 2), (SELECT sr_cl_id FROM _t_ctx), 'SHOP_CUSTOMER', true);

    PERFORM set_config('zeroerp.test_id_2', v_id::text, true);
END
$$;

SELECT is(
    script.fn_scope_ba_ownership(
        current_setting('zeroerp.test_id_2')::bigint,
        (SELECT ba_id FROM _t_ctx)
    ),
    true,
    '3. SHOP_CUSTOMER attiva + BA stesso SR -> true (multi-canale)'
);

-- =========================================================
-- 4) API_CLIENT attiva + BA stesso SR -> false
--    La fn filtra id.ruolo_applicativo IN (CLIENTE_PORTALE, SHOP_CUSTOMER)
--    -> API_CLIENT non passa anche se l'identita e' attiva e il
--    SR coincide.
-- =========================================================
DO $$
DECLARE
    v_id bigint;
BEGIN
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (
        (SELECT sr_cl_id FROM _t_ctx),
        (SELECT auth_user_id FROM _t_au_pool WHERE idx = 3),
        'API_CLIENT', true
    ) RETURNING id INTO v_id;

    PERFORM set_config('zeroerp.test_id_3', v_id::text, true);
END
$$;

SELECT is(
    script.fn_scope_ba_ownership(
        current_setting('zeroerp.test_id_3')::bigint,
        (SELECT ba_id FROM _t_ctx)
    ),
    false,
    '4. API_CLIENT attiva + BA stesso SR -> false (filtro ruolo-aware)'
);

-- =========================================================
-- 5) CLIENTE_PORTALE con attivo=false -> false (fail-closed)
-- =========================================================
DO $$
DECLARE
    v_id bigint;
BEGIN
    v_id := anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 4), (SELECT sr_cl_id FROM _t_ctx), 'CLIENTE_PORTALE', false);

    PERFORM set_config('zeroerp.test_id_4', v_id::text, true);
END
$$;

SELECT is(
    script.fn_scope_ba_ownership(
        current_setting('zeroerp.test_id_4')::bigint,
        (SELECT ba_id FROM _t_ctx)
    ),
    false,
    '5. CLIENTE_PORTALE con attivo=false + BA -> false (fail-closed su attivo)'
);

SELECT * FROM finish();
ROLLBACK;
