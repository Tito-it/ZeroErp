-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata
-- Constraint trigger DEFERRABLE INITIALLY DEFERRED su istanze_utilities.
-- Strategia C (sessione 2026-05-01): ogni nuova istanza deve avere
-- almeno 1 satellite (BA, IDP, clienti) entro la transazione.
--
-- Indice test (1..4):
--    1. Preflight: il constraint trigger esiste (tgconstraint <> 0)
--    2. INSERT istanza + IDP (DEFERRED), poi SET CONSTRAINTS ALL IMMEDIATE
--       -> lives_ok (la coppia e' coerente, il constraint si soddisfa)
--    3. Con mode IMMEDIATE attivo: INSERT istanza orfana -> throws P0001
--       (il constraint trigger fa raise immediatamente)
--    4. Verifica indiretta della fonte "clienti": fn_check su cliente esistente
--
-- IMPORTANTE: nessun SAVEPOINT/ROLLBACK TO SAVEPOINT (rompe state pgTAP).
-- Ordine: success prima, force IMMEDIATE, fail dopo. ROLLBACK finale
-- (BEGIN/ROLLBACK del file) ripulisce le manipolazioni.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- ============================================================
-- Setup
-- ============================================================
CREATE TEMP TABLE _t_soggetto AS
SELECT s.id AS soggetto_id
  FROM anagrafiche.soggetti s
 WHERE s.attivo = true
 ORDER BY s.id
 LIMIT 1;

CREATE TEMP TABLE _t_utility AS
SELECT u.id AS utility_id
  FROM config.utilities u
 ORDER BY u.id
 LIMIT 1;

-- ============================================================
-- 1) Preflight: constraint trigger esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c   ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'anagrafiche'
           AND c.relname = 'istanze_utilities'
           AND t.tgname  = 'trg_istanze_utilities_z90_require_utility_dichiarata_ins'
           AND t.tgconstraint <> 0
    ),
    '1. Constraint trigger trg_istanze_utilities_z90_require_utility_dichiarata_ins esiste'
);

-- ============================================================
-- 2) INSERT istanza + IDP (DEFERRED), poi SET CONSTRAINTS ALL IMMEDIATE
-- ============================================================
DO $$
DECLARE
  v_iu_id bigint;
BEGIN
  INSERT INTO anagrafiche.istanze_utilities (
      fittizia, proprietario_inquilino, soggetto_id
  )
  VALUES (
      true, 'I', (SELECT soggetto_id FROM _t_soggetto)
  )
  RETURNING id INTO v_iu_id;

  INSERT INTO anagrafiche.istanze_dati_precontrattuali (
      istanza_utility_id, utility_id
  )
  VALUES (
      v_iu_id, (SELECT utility_id FROM _t_utility)
  );
END $$;

-- Forza la valutazione del constraint trigger DEFERRED.
-- L'istanza ha gia' un IDP -> deve passare.
-- Effetto collaterale: mode IMMEDIATE attivo per il resto della tx.
SELECT lives_ok(
  $$ SET CONSTRAINTS ALL IMMEDIATE $$,
  '2. Istanza + IDP nella stessa tx -> SET CONSTRAINTS ALL IMMEDIATE ok'
);

-- ============================================================
-- 3) Con mode IMMEDIATE attivo: INSERT orfana -> raise P0001
--    Il constraint trigger fa raise direttamente sull'INSERT.
-- ============================================================
SELECT throws_ok(
  format($SQL$
    INSERT INTO anagrafiche.istanze_utilities (
      fittizia, proprietario_inquilino, soggetto_id
    )
    VALUES (true, 'I', %s)
  $SQL$, (SELECT soggetto_id FROM _t_soggetto)),
  'P0001',
  NULL,
  '3. Istanza orfana con mode IMMEDIATE -> P0001 (E_ISTANZA_UTILITY_SENZA_UTILITY)'
);

-- ============================================================
-- 4) Verifica indiretta della fonte "clienti":
--    almeno un cliente esistente deve essere riconosciuto da fn_check.
--    Skip soft se nessun cliente in fixture.
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM anagrafiche.clienti c
     WHERE c.istanza_utility_id IS NOT NULL
       AND c.utility_id IS NOT NULL
       AND script.fn_check_utility_istanza_coerenza(c.istanza_utility_id, c.utility_id) = true
  ) OR (SELECT count(*) FROM anagrafiche.clienti
         WHERE istanza_utility_id IS NOT NULL
           AND utility_id IS NOT NULL) = 0,
  '4. Almeno un cliente esistente e'' riconosciuto come fonte coerente (skip se nessun cliente)'
);

SELECT * FROM finish();
ROLLBACK;
