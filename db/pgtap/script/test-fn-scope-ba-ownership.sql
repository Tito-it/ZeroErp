-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce DUE clienti fatturabili con il
--   loro billing account. Come `zeroerp_app` l'INSERT del BA muore al
--   RETURNING quando l'emittente di chi agisce non e' quello di default (la
--   policy di lettura risolve il BA non ancora mappato sul default; il legame
--   lo scrive un trigger AFTER). Il soggetto del test e'
--   script.fn_scope_ba_ownership, che prende identita' e BA come parametri:
--   il ruolo di connessione non cambia cio' che misura.
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_ba_ownership
-- Riferimento: §4.4 WIP multi-face-auth, policy BA_OWNERSHIP.
--
-- Semantica attesa:
--   - identita inesistente/inattiva -> false (fail-closed)
--   - BA appartiene al soggetto_ruolo dell'identita -> true
--   - BA appartiene a un altro soggetto_ruolo -> false (leak test)
--
-- Indice test (1..6):
--    1. Precondizione: due billing_account di clienti distinti (costruiti)
--    2. Setup: identita CLIENTE_PORTALE attiva per cliente 1
--              + identita CLIENTE_PORTALE inattiva per cliente 2
--    3. Identita inesistente -> false
--    4. Identita inattiva -> false
--    5. Identita cliente 1 su BA cliente 1 -> true
--    6. Identita cliente 1 su BA cliente 2 -> false (leak test)
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
-- ⛔ I DUE CLIENTI SI COSTRUISCONO, non si cercano (2026-09-12): fino a quel
--   giorno il file pescava due BA fra quelli ESISTENTI, e su un database
--   ricostruito dai changelog non ce n'e' nessuno — il leak test (caso 6)
--   restava collaudato solo su dbdev. Un'azienda con
--   `dbops.fn_pgtap_crea_emittente_operatore()` per il contesto, due clienti
--   con `dbops.fn_pgtap_crea_cliente_ba()` legati a lei — PRIMA del contesto,
--   altrimenti il trigger z90 del BA scriverebbe un secondo legame.
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _t_bas AS
SELECT c.billing_account_id AS ba_id,
       c.soggetto_ruolo_id  AS sr_id,
       ROW_NUMBER() OVER (ORDER BY c.billing_account_id) AS rn
  FROM (SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
                     'scope BA 1', NULL, (SELECT soggetto_ruolo_id FROM _t_mondo))
        UNION ALL
        SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
                     'scope BA 2', NULL, (SELECT soggetto_ruolo_id FROM _t_mondo))) c;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _t_mondo));
END $ctx$;

SELECT plan(6);

-- =========================================================
-- 1) Precondizione: 2 BA di clienti distinti
-- =========================================================
-- Un cliente puo' avere piu' BA; serve UN BA per cliente distinto,
-- altrimenti il leak test (caso 6) diventa banale.
SELECT ok(
    (SELECT count(*) FROM _t_bas) = 2
    AND (SELECT count(DISTINCT sr_id) FROM _t_bas) = 2,
    '1. Precondizione: 2 BA di clienti con soggetti_ruoli distinti, costruiti'
);

-- =========================================================
-- 2) Setup: 2 auth_user + 2 identita CLIENTE_PORTALE
-- =========================================================
CREATE TEMP TABLE _t_au (idx int, auth_user_id int);
DO $$
DECLARE v_i int; v_id int;
BEGIN
    FOR v_i IN 1..2 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined
        )
        VALUES (
            '_pgtap_scope_ba_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', true, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

-- Identita attiva per cliente 1 (rn=1)
CREATE TEMP TABLE _t_id (idx int, identita_id bigint);
WITH ins_a AS (
    SELECT anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au WHERE idx = 1), b.sr_id, 'CLIENTE_PORTALE', true) AS id FROM _t_bas b WHERE b.rn = 1)
INSERT INTO _t_id (idx, identita_id)
SELECT 1, id FROM ins_a;

-- Identita inattiva per cliente 2 (rn=2)
WITH ins_i AS (
    SELECT anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au WHERE idx = 2), b.sr_id, 'CLIENTE_PORTALE', false) AS id FROM _t_bas b WHERE b.rn = 2)
INSERT INTO _t_id (idx, identita_id)
SELECT 2, id FROM ins_i;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 2,
    '2. Setup: 2 identita CLIENTE_PORTALE create (1 attiva, 1 inattiva)'
);

-- =========================================================
-- 3) Identita inesistente -> false
-- =========================================================
SELECT ok(
    script.fn_scope_ba_ownership(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.identita_digitali),
        (SELECT ba_id FROM _t_bas WHERE rn = 1)
    ) = false,
    '3. Identita inesistente -> false (fail-closed)'
);

-- =========================================================
-- 4) Identita inattiva -> false
-- =========================================================
SELECT ok(
    script.fn_scope_ba_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 2),
        (SELECT ba_id FROM _t_bas WHERE rn = 2)
    ) = false,
    '4. Identita inattiva -> false (fail-closed)'
);

-- =========================================================
-- 5) Identita cliente 1 su BA cliente 1 -> true
-- =========================================================
SELECT ok(
    script.fn_scope_ba_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT ba_id FROM _t_bas WHERE rn = 1)
    ) = true,
    '5. Identita attiva cliente 1 su BA cliente 1 -> true'
);

-- =========================================================
-- 6) Identita cliente 1 su BA cliente 2 -> false (leak test)
-- =========================================================
-- Il BA del cliente 2 deve essere invisibile all'identita del cliente 1.
SELECT ok(
    script.fn_scope_ba_ownership(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT ba_id FROM _t_bas WHERE rn = 2)
    ) = false,
    '6. Identita cliente 1 su BA cliente 2 -> false (leak test: cliente A non vede BA di cliente B)'
);

SELECT * FROM finish();
ROLLBACK;
