-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata
-- Constraint trigger DEFERRABLE INITIALLY DEFERRED su istanze_utilities.
-- Dal 2026-10-08 (brief-db-istanza-nasce-col-ba, R-1): ogni nuova istanza
-- deve avere il suo billing account entro la transazione. Fino a quel giorno
-- (Strategia C, sessione 2026-05-01) bastava un satellite qualunque fra BA,
-- dati precontrattuali e clienti.
--
-- Indice test (1..4):
--    1. Preflight: il constraint trigger esiste (tgconstraint <> 0)
--    2. INSERT istanza + BA (DEFERRED), poi SET CONSTRAINTS ALL IMMEDIATE
--       -> lives_ok (l'istanza ha il suo BA, il constraint si soddisfa)
--    3. Con mode IMMEDIATE attivo: INSERT istanza orfana -> E_ISTANZA_SENZA_BA
--       (il constraint trigger fa raise immediatamente)
--    4. Verifica indiretta della fonte "clienti": fn_check su cliente esistente
--    I casi della regola nuova (cancellazione dell'ultimo BA, dati
--    precontrattuali senza BA, un emittente per istanza) stanno in
--    test-istanza-nasce-col-ba-v1.sql.
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

-- ⚠️ VINCOLI DIFFERITI — ⭐ LA FINESTRA SI RIAPRE, NON SI PRESUME.
--   Il test 2 inserisce l'istanza e POI il suo BA, e chiede al constraint
--   trigger DIFFERITO di giudicare la coppia: la finestra e' l'oggetto del test.
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   ERRORE_FIXTURE: «Istanza utility senza utility dichiarata … »
--   all'INSERT dell'istanza, prima dell'IDP.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(4);

-- ============================================================
-- Setup
-- ============================================================
-- ⚠️ rev 2026-10-08: il soggetto si COSTRUISCE (prima: «il primo attivo»).
--   Ora riceve il ruolo CLIENTE per il BA del test 2, e un soggetto pescato
--   puo' avere una natura che quel ruolo non ammette.
CREATE TEMP TABLE _t_soggetto AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Istanza nasce col BA') AS soggetto_id;

CREATE TEMP TABLE _t_utility AS
SELECT u.id AS utility_id
  FROM config.utilities u
 ORDER BY u.id
 LIMIT 1;

-- Il ruolo CLIENTE del soggetto: il BA lo pretende (D-3 del brief: il ruolo
-- nasce con la prima istanza). ⛔ Il builder scrive; si legge separato.
CREATE TEMP TABLE _t_sr AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
         (SELECT soggetto_id FROM _t_soggetto), 'CL'::character varying) AS soggetto_ruolo_id;

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
-- 2) INSERT istanza + BA (DEFERRED), poi SET CONSTRAINTS ALL IMMEDIATE
-- ============================================================
DO $$
DECLARE
  v_iu_id bigint;
BEGIN
  -- La finestra si riapre QUI: gli helper del setup (_t_soggetto, _t_sr)
  -- escono con i vincoli IMMEDIATE e l'hanno richiusa (rev 2026-10-08).
  SET CONSTRAINTS ALL DEFERRED;

  INSERT INTO anagrafiche.istanze_utilities (
      fittizia, proprietario_inquilino, soggetto_id
  )
  VALUES (
      true, 'I', (SELECT soggetto_id FROM _t_soggetto)
  )
  RETURNING id INTO v_iu_id;

  INSERT INTO anagrafiche.billing_account (
      istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id
  )
  VALUES (
      v_iu_id,
      (SELECT soggetto_ruolo_id FROM _t_sr),
      (SELECT utility_id FROM _t_utility),
      (SELECT cc.id FROM anagrafiche.categorie_clienti cc
        WHERE cc.codice_interno = 'STANDARD')
  );
END $$;

-- Forza la valutazione del constraint trigger DEFERRED.
-- L'istanza ha gia' il suo BA -> deve passare.
-- Effetto collaterale: mode IMMEDIATE attivo per il resto della tx.
SELECT lives_ok(
  $$ SET CONSTRAINTS ALL IMMEDIATE $$,
  '2. Istanza + BA nella stessa tx -> SET CONSTRAINTS ALL IMMEDIATE ok'
);

-- ============================================================
-- 3) Con mode IMMEDIATE attivo: INSERT orfana -> raise P0001
--    Il constraint trigger fa raise direttamente sull'INSERT.
-- ============================================================
-- ⚠️ `%L` e non `%s`: il soggetto e' un UUID, e interpolato con `%s` finisce
--   nell'SQL SENZA apici — PostgreSQL prova a leggerlo come numero e alza
--   42601 («spazzatura finale dopo il letterale numerico»). Il test era rosso
--   per questo, non per il guard. ⭐ Se `throws_ok` non avesse avuto lo SQLSTATE
--   (`P0001`) sarebbe stato VERDE: qualunque errore avrebbe soddisfatto
--   l'asserzione, compreso l'errore di sintassi del test stesso.
SELECT throws_ok(
  format($SQL$
    INSERT INTO anagrafiche.istanze_utilities (
      fittizia, proprietario_inquilino, soggetto_id
    )
    VALUES (true, 'I', %L)
  $SQL$, (SELECT soggetto_id FROM _t_soggetto)),
  'P0001',
  NULL,
  '3. Istanza orfana con mode IMMEDIATE -> P0001 (E_ISTANZA_SENZA_BA)'
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
