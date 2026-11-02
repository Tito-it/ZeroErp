-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_check_utility_istanza_coerenza(istanza_utility_id, utility_id)
-- Pure check (no raise): la coppia ha il suo billing account.
-- Riferimento brief preventivi rev2 (sessione 2026-05-01).
-- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-1): fino a quel giorno le
--   fonti erano tre (BA, dati precontrattuali, clienti); ora e' il solo BA, e
--   le altre due lo implicano per FK. Il test 4 (via clienti) resta: un cliente
--   ha il BA della sua coppia, quindi la risposta e' ancora true.
--
-- Indice test (1..6):
--    1. Param NULL su istanza  -> false
--    2. Param NULL su utility  -> false
--    3. Coppia matching via BA -> true (uso BA esistente in fixture)
--    4. Coppia matching via clienti -> true (cliente esistente)
--    5. Coppia con istanza esistente ma utility diversa da quella satellite -> false
--    6. Coppia con istanza inesistente -> false
--
-- BEGIN; + ROLLBACK finale: nessuna manipolazione persiste.
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

-- ============================================================
-- Setup: pesco una coppia (istanza, utility) esistente da BA
-- ============================================================
CREATE TEMP TABLE _t_ba_pair AS
SELECT ba.istanza_utility_id, ba.utility_id
  FROM anagrafiche.billing_account ba
 WHERE ba.istanza_utility_id IS NOT NULL
   AND ba.utility_id IS NOT NULL
 ORDER BY ba.id
 LIMIT 1;

-- Coppia (istanza, utility) esistente da clienti (puo' essere stessa di BA)
CREATE TEMP TABLE _t_cli_pair AS
SELECT c.istanza_utility_id, c.utility_id
  FROM anagrafiche.clienti c
 WHERE c.istanza_utility_id IS NOT NULL
   AND c.utility_id IS NOT NULL
 ORDER BY c.id
 LIMIT 1;

-- ============================================================
-- 1) param NULL su istanza_utility_id
-- ============================================================
SELECT is(
    script.fn_check_utility_istanza_coerenza(NULL, 1),
    false,
    '1. param NULL su istanza_utility_id -> false'
);

-- ============================================================
-- 2) param NULL su utility_id
-- ============================================================
SELECT is(
    script.fn_check_utility_istanza_coerenza(1, NULL),
    false,
    '2. param NULL su utility_id -> false'
);

-- ============================================================
-- 3) Coppia matching via BA -> true
-- ============================================================
SELECT ok(
    script.fn_check_utility_istanza_coerenza(
        (SELECT istanza_utility_id FROM _t_ba_pair),
        (SELECT utility_id FROM _t_ba_pair)
    ) = true OR (SELECT count(*) FROM _t_ba_pair) = 0,
    '3. Coppia matching via BA -> true (skip se nessun BA fixture)'
);

-- ============================================================
-- 4) Coppia matching via clienti -> true
-- ============================================================
SELECT ok(
    script.fn_check_utility_istanza_coerenza(
        (SELECT istanza_utility_id FROM _t_cli_pair),
        (SELECT utility_id FROM _t_cli_pair)
    ) = true OR (SELECT count(*) FROM _t_cli_pair) = 0,
    '4. Coppia matching via clienti -> true (skip se nessun cliente fixture)'
);

-- ============================================================
-- 5) Coppia con istanza esistente ma utility diversa -> false
--    (utility_id = 9999 dev essere fuori range delle utility esistenti
--     associate alla stessa istanza)
-- ============================================================
SELECT is(
    script.fn_check_utility_istanza_coerenza(
        (SELECT istanza_utility_id FROM _t_ba_pair),
        9999
    ),
    false,
    '5. Coppia istanza valida + utility 9999 inesistente per quella istanza -> false'
);

-- ============================================================
-- 6) Coppia con istanza inesistente -> false
-- ============================================================
SELECT is(
    script.fn_check_utility_istanza_coerenza(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.istanze_utilities),
        1
    ),
    false,
    '6. Istanza inesistente -> false'
);

SELECT * FROM finish();
ROLLBACK;
