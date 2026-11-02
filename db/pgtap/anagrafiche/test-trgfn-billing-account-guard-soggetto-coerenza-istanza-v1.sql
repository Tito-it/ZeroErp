-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza
--       Trigger: trg_billing_account_a20_guard_soggetto_coerenza_istanza_ins_upd (a10 fino al 2026-10-09)
--
-- Migrations:
--   20260502-16 (create-trgfn-billing-account-guard-soggetto-coerenza-istanza)
--
-- Indice test (1..5):
--   1) Function presente in anagrafiche.
--   2) Trigger BEFORE INSERT/UPDATE su billing_account presente.
--   3) Pre-check su DB pulito: nessun BA esistente viola il vincolo.
--   4) INSERT BA con soggetto_ruolo coerente con istanza -> ammesso.
--   5) INSERT BA con soggetto_ruolo NON coerente -> raise
--      E_BA_SOGGETTO_INCOERENTE_ISTANZA (P0001).
--
-- Pattern: usa entita' esistenti nel DB (2 soggetti distinti +
-- relativi soggetti_ruoli + istanza ancorata al soggetto1) per
-- evitare il setup complesso (soggetti hanno guard contatti+indirizzi).
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

-- ============================================================
-- 1) Function presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'anagrafiche'
      AND p.proname = 'trgfn_billing_account_guard_soggetto_coerenza_istanza'
  ),
  '1. trgfn_billing_account_guard_soggetto_coerenza_istanza presente'
);

-- ============================================================
-- 2) Trigger presente su billing_account
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'anagrafiche'
      AND c.relname = 'billing_account'
      -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-7): fascia _a20_, dopo il
      --   lock di colonna (20261009-69), perche' su UPDATE parli l'immutabilita'.
      AND t.tgname  = 'trg_billing_account_a20_guard_soggetto_coerenza_istanza_ins_upd'
      AND NOT t.tgisinternal
  ),
  '2. Trigger trg_billing_account_a20_guard_soggetto_coerenza_istanza_ins_upd presente'
);

-- ============================================================
-- 3) Pre-check coerenza dati attuali: nessun BA viola il vincolo
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM anagrafiche.billing_account ba
     JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
     JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
    WHERE sr.soggetto_id <> iu.soggetto_id),
  0,
  '3. Nessun BA esistente con soggetto incoerente vs istanza'
);

-- ============================================================
-- 4) Setup riferimenti: 2 soggetti diversi + ruoli + istanza s1
--
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   I due soggetti si PESCAVANO («i primi due con un ruolo e un'istanza»):
--   su un database ricostruito (la CI) non ce n'e' nessuno, il setup
--   restava vuoto e il test 5 prendeva un 23502 (istanza NULL) invece del
--   guard. Ora sono due clienti COSTRUITI con dbops.fn_pgtap_crea_cliente_ba
--   (soggetto -> ruolo CL -> istanza -> BA): l'istanza e' del primo, il
--   ruolo del secondo. ⛔ Cio' che il builder scrive si legge in
--   un'istruzione SEPARATA.
--   E il test 5 asserisce la FRASE del guard, non solo P0001: P0001 e' il
--   codice di tutti gli errori di dominio, e un altro guard che sollevasse
--   prima lo farebbe passare per la ragione sbagliata.
-- ============================================================
CREATE TEMP TABLE tmp_cli1 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('coerenza istanza 1');

CREATE TEMP TABLE tmp_cli2 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('coerenza istanza 2');

CREATE TEMP TABLE tmp_ba_refs AS
SELECT
  c1.soggetto_id         AS soggetto1_id,
  c2.soggetto_id         AS soggetto2_id,
  c1.soggetto_ruolo_id   AS soggetto1_ruolo_id,
  c2.soggetto_ruolo_id   AS soggetto2_ruolo_id,
  c1.istanza_utility_id  AS istanza_id,
  -- utility diversa da quella del BA gia' costruito sull'istanza 1: la
  -- UNIQUE (istanza_utility_id, utility_id) resta fuori gioco.
  (SELECT u.id FROM config.utilities u
    WHERE u.id <> c1.utility_id
    ORDER BY u.id LIMIT 1) AS utility_id,
  (SELECT cc.id FROM anagrafiche.categorie_clienti cc
    WHERE cc.codice_interno = 'STANDARD') AS categoria_cliente_id
FROM tmp_cli1 c1, tmp_cli2 c2;

-- Verifica setup: tutti i riferimenti popolati
SELECT ok(
  (SELECT soggetto1_id IS NOT NULL
      AND soggetto2_id IS NOT NULL
      AND soggetto1_id <> soggetto2_id
      AND soggetto1_ruolo_id IS NOT NULL
      AND soggetto2_ruolo_id IS NOT NULL
      AND istanza_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND categoria_cliente_id IS NOT NULL
   FROM tmp_ba_refs),
  '4. Setup: 2 soggetti distinti + ruoli + istanza s1 + utility libera disponibili'
);

-- ============================================================
-- 5) INSERT BA con soggetto_ruolo NON coerente -> raise
-- ============================================================
SELECT throws_like(
  $$INSERT INTO anagrafiche.billing_account
      (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, codice)
    SELECT istanza_id, soggetto2_ruolo_id, utility_id, categoria_cliente_id,
           'PGTAP-BA-INCOERENTE-' || substr(md5(clock_timestamp()::text), 1, 8)
      FROM tmp_ba_refs$$,
  '%diverso da soggetto dell''istanza_utility%',
  '5. INSERT BA con soggetto_ruolo di soggetto2 + istanza di soggetto1 -> E_BA_SOGGETTO_INCOERENTE_ISTANZA'
);

SELECT * FROM finish();
ROLLBACK;
