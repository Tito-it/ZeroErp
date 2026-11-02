-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: i due guard sulla riga contabile — bagaglio dello stato e distinta finale
--
-- Presidia i passi S1-6 e S1-7 del lotto 2 del cantiere incassi.
--
-- Elenco test (plan 7):
-- 1) Una riga DA_ABBINARE senza fattura entra: quello stato non pretende niente
-- 2) 🔴 S1-6: una riga ABBINATA senza fattura è rifiutata
-- 3) 🔴 S1-6: una riga ABBINATA senza cliente è rifiutata
-- 4) Una riga ABBINATA completa entra — e la RATA non serve
-- 5) 🔴 S1-7: una riga non si aggiunge sotto una distinta CHIUSA
-- 6) 🔴 S1-7: e nemmeno si SPOSTA sotto una distinta CHIUSA
-- 7) 🔴 S1-20: una distinta con righe pronte non si chiude
--
-- Scopo:
--  - il test 4 presidia una DECISIONE, non un vuoto: la rata resta facoltativa
--    anche su ABBINATA, perché la riga del fondo fattura ha fattura sì e rata no
--    — è un saldo per trasferimento. Se un giorno qualcuno «completasse» il
--    guard aggiungendo la rata, questo test lo fermerebbe;
--  - i test 5 e 6 sono le DUE mosse della porta d'ingresso di C-5: aggiungere e
--    spostare. Chiudere solo la prima lascerebbe l'altra aperta;
--  - il test 7 è la porta d'uscita, quella che capita davvero.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture
--   ⚠️ Niente LIMIT 1 senza ORDER BY, e la condizione che rende il caso
--   significativo — la fattura dev'essere VISIBILE (la RLS filtra da sé) e
--   avere il billing account — è scelta UNA volta.
-- ============================================================
-- ⛔ LA FATTURA SI COSTRUISCE (2026-09-23). Su un database ricostruito
--   `vendite.fatture` e' a zero: `fattura_id` e `ba_id` uscivano NULL e il
--   caso 4 — «una riga ABBINATA CON fattura e cliente entra» — sbatteva contro
--   il guard che pretende proprio quei due dati. Cioe' il test rosso diceva il
--   vero sul prodotto e il falso su se stesso: non stava misurando il ramo
--   permissivo, stava misurando l'assenza di una fattura.
-- ⚠️ Centro e stati restano pescati: sono seed di `80_data`.
CREATE TEMP TABLE tmp_rcgd_fatt AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('righe contabili guard dati');

CREATE TEMP TABLE tmp_rcgd AS
SELECT
  (SELECT fattura_id         FROM tmp_rcgd_fatt)                               AS fattura_id,
  (SELECT billing_account_id FROM tmp_rcgd_fatt)                               AS ba_id,
  (SELECT c.id FROM pagamenti.centri_riscossione c
    WHERE c.codice_interno = 'BANCA')                                          AS centro_id,
  (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
    WHERE s.codice_interno = 'DA_ABBINARE')                                    AS st_da_abbinare,
  (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
    WHERE s.codice_interno = 'ABBINATA')                                       AS st_abbinata,
  (SELECT s.id FROM pagamenti.vendite_contabili_stati s
    WHERE s.codice_interno = 'VALIDATA')                                       AS st_validata,
  (SELECT s.id FROM pagamenti.vendite_contabili_stati s
    WHERE s.codice_interno = 'CHIUSA')                                         AS st_chiusa;

CREATE TEMP TABLE tmp_rcgd_dist AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, meta)
  SELECT 'RCGD_A_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         r.centro_id, script.fn_data_operativa(), script.fn_data_operativa(),
         '{"test_scope":"pgtap_righe_contabili_guard_dati"}'::jsonb
    FROM tmp_rcgd r
  RETURNING id
)
SELECT id AS aperta FROM ins;

-- ============================================================
-- 1) DA_ABBINARE senza fattura: quello stato non pretende niente
-- ============================================================
SELECT lives_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, importo, stato_id, meta)
  SELECT d.aperta, 10.00, r.st_da_abbinare,
         '{"test_scope":"pgtap_righe_contabili_guard_dati"}'::jsonb
    FROM tmp_rcgd_dist d, tmp_rcgd r;
  $$,
  'Una riga DA_ABBINARE entra senza fattura: quello stato non pretende l''abbinamento'
);

-- ============================================================
-- 2) 🔴 ABBINATA senza fattura
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, importo, billing_account_id, stato_id, meta)
  SELECT d.aperta, 20.00, r.ba_id, r.st_abbinata,
         '{"test_scope":"pgtap_righe_contabili_guard_dati"}'::jsonb
    FROM tmp_rcgd_dist d, tmp_rcgd r;
  $$,
  'P0001',
  NULL,
  'Una riga ABBINATA senza fattura e'' rifiutata'
);

-- ============================================================
-- 3) 🔴 ABBINATA senza cliente
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, importo, fattura_id, stato_id, meta)
  SELECT d.aperta, 30.00, r.fattura_id, r.st_abbinata,
         '{"test_scope":"pgtap_righe_contabili_guard_dati"}'::jsonb
    FROM tmp_rcgd_dist d, tmp_rcgd r;
  $$,
  'P0001',
  NULL,
  'Una riga ABBINATA senza billing account e'' rifiutata'
);

-- ============================================================
-- 4) ABBINATA completa entra — e la RATA non serve
--   ⚠️ È una DECISIONE: la riga del fondo fattura ha fattura sì e rata no.
-- ============================================================
SELECT lives_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, importo, fattura_id, billing_account_id, stato_id, meta)
  SELECT d.aperta, 40.00, r.fattura_id, r.ba_id, r.st_abbinata,
         '{"test_scope":"pgtap_righe_contabili_guard_dati"}'::jsonb
    FROM tmp_rcgd_dist d, tmp_rcgd r;
  $$,
  'Una riga ABBINATA con fattura e cliente entra: la rata NON e'' richiesta'
);

-- ============================================================
-- 7) 🔴 S1-20 — la distinta ha righe pronte e non si chiude
--   ⚠️ Sta prima dei test 5 e 6 perché quelli hanno bisogno di una distinta
--   GIÀ chiusa, e per chiuderla vanno prima tolte le righe pronte.
-- ============================================================
-- ⭐ Rev 2026-09-18 (D20-a): la riga DA_ABBINARE del test 1 va guardata prima
--   di validare — una riga non lavorata non entra in VALIDATA. Si sospende:
--   il test 1 resta sull'INSERT, la regola nuova ha il suo presidio in
--   test-contabile-validabile-v1.
UPDATE pagamenti.vendite_contabili_righe
   SET stato_id = (SELECT id FROM pagamenti.vendite_contabili_righe_stati
                    WHERE codice_interno = 'SOSPESA'),
       motivo_sospeso = 'guardata, in attesa'
 WHERE contabile_id = (SELECT aperta FROM tmp_rcgd_dist)
   AND stato_id = (SELECT st_da_abbinare FROM tmp_rcgd);

UPDATE pagamenti.vendite_contabili
   SET stato_id = (SELECT st_validata FROM tmp_rcgd)
 WHERE id = (SELECT aperta FROM tmp_rcgd_dist);

SELECT throws_ok(
  $$ UPDATE pagamenti.vendite_contabili
        SET stato_id = (SELECT st_chiusa FROM tmp_rcgd)
      WHERE id = (SELECT aperta FROM tmp_rcgd_dist) $$,
  'P0001',
  NULL,
  'Una distinta con righe pronte da registrare non si chiude'
);

-- Si tolgono le righe pronte dicendo che cosa ne e' stato, e allora si chiude.
UPDATE pagamenti.vendite_contabili_righe
   SET stato_id = (SELECT id FROM pagamenti.vendite_contabili_righe_stati
                    WHERE codice_interno = 'SOSPESA')
 WHERE contabile_id = (SELECT aperta FROM tmp_rcgd_dist)
   AND stato_id = (SELECT st_abbinata FROM tmp_rcgd);

UPDATE pagamenti.vendite_contabili
   SET stato_id = (SELECT st_chiusa FROM tmp_rcgd)
 WHERE id = (SELECT aperta FROM tmp_rcgd_dist);

-- ============================================================
-- 5) 🔴 S1-7 — non si AGGIUNGE una riga sotto una distinta chiusa
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, importo, stato_id, meta)
  SELECT d.aperta, 50.00, r.st_da_abbinare,
         '{"test_scope":"pgtap_righe_contabili_guard_dati"}'::jsonb
    FROM tmp_rcgd_dist d, tmp_rcgd r;
  $$,
  'P0001',
  NULL,
  'Una riga non si aggiunge sotto una distinta chiusa'
);

-- ============================================================
-- 6) 🔴 S1-7 — e nemmeno si SPOSTA lì
--   Serve una seconda distinta, aperta, da cui spostare.
-- ============================================================
CREATE TEMP TABLE tmp_rcgd_dist2 AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, meta)
  SELECT 'RCGD_B_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         r.centro_id, script.fn_data_operativa() + 1, script.fn_data_operativa(),
         '{"test_scope":"pgtap_righe_contabili_guard_dati"}'::jsonb
    FROM tmp_rcgd r
  RETURNING id
)
SELECT id AS aperta2 FROM ins;

INSERT INTO pagamenti.vendite_contabili_righe
  (contabile_id, importo, stato_id, meta)
SELECT d.aperta2, 60.00, r.st_da_abbinare,
       '{"test_scope":"pgtap_righe_contabili_guard_dati","case":"da_spostare"}'::jsonb
  FROM tmp_rcgd_dist2 d, tmp_rcgd r;

SELECT throws_ok(
  $$ UPDATE pagamenti.vendite_contabili_righe
        SET contabile_id = (SELECT aperta FROM tmp_rcgd_dist)
      WHERE meta ->> 'case' = 'da_spostare' $$,
  'P0001',
  NULL,
  'Una riga non si sposta sotto una distinta chiusa'
);

SELECT * FROM finish();
ROLLBACK;
