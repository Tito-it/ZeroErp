-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: origine della distinta, quadratura col dichiarato, distinta per operatore
--
-- Presidia i passi S1-18, S1-19 e S1-22 del lotto 2 del cantiere incassi.
--
-- Elenco test (plan 8):
-- 1) Il vocabolario di origine è a TRE valori
-- 2) Una AUTOMATICA senza totale dichiarato è rifiutata
-- 3) Una GENERATA con un totale dichiarato è rifiutata
-- 4) 🔴 S1-22: validare con un dichiarato che non quadra è rifiutato
-- 5) ⚠️ La quadratura conta anche le righe SCARTATE
-- 6) Senza dichiarato non si controlla niente
-- 7) 🔴 S1-19: due operatori aprono DUE distinte manuali, non una
-- 8) 🔴 Riaprire in BOZZA una distinta non manuale è rifiutato
--
-- Scopo:
--  - il test 5 è il più importante e il meno ovvio: se una riga scartata uscisse
--    dalla somma, il PRIMO SCARTO romperebbe la quadratura di una distinta sana.
--    La quadratura dice «abbiamo letto tutto ciò che c'era», non «tutto è nostro»;
--  - il test 7 è la prova che il lock chiesto non serve: due operatori non
--    condividono una distinta manuale, quindi non c'è niente da contendere;
--  - il test 8 presidia una regola che la MATRICE non porta: VALIDATA -> BOZZA è
--    seminata come ammessa, e la restrizione a MANUALE vive nel guard. Chi legge
--    la sola matrice non la vede.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

CREATE TEMP TABLE tmp_coq AS
SELECT
  (SELECT c.id FROM pagamenti.centri_riscossione c WHERE c.codice_interno = 'BANCA') AS centro_id,
  -- ⭐ Rev 2026-09-18 (D20-a): le righe della fixture sono SOSPESE, non piu'
  --   DA_ABBINARE — una riga non lavorata non entra in VALIDATA, e qui la
  --   posta e' la QUADRATURA, non il lavoro non finito. Quel motivo ha il suo
  --   presidio in test-contabile-validabile-v1.
  (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
    WHERE s.codice_interno = 'SOSPESA')                                              AS st_sospesa,
  (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
    WHERE s.codice_interno = 'SCARTATA')                                             AS st_scartata,
  (SELECT s.id FROM pagamenti.vendite_contabili_stati s
    WHERE s.codice_interno = 'VALIDATA')                                             AS st_validata,
  (SELECT s.id FROM pagamenti.vendite_contabili_stati s
    WHERE s.codice_interno = 'BOZZA')                                                AS st_bozza;

-- ============================================================
-- 1) Il vocabolario è a tre
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_constraint
    WHERE conrelid = 'pagamenti.vendite_contabili'::regclass
      AND conname = 'chk_vendite_contabili_origine'
      AND pg_get_constraintdef(oid) LIKE '%GENERATA%'),
  1,
  'origine ammette anche GENERATA: il sync dei fondi non e'' ne'' manuale ne'' automatica'
);

-- ============================================================
-- 2) AUTOMATICA senza dichiarato
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, origine, meta)
  SELECT 'COQ_AUTO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         c.centro_id, script.fn_data_operativa(), script.fn_data_operativa(), 'AUTOMATICA',
         '{"test_scope":"pgtap_contabili_origine"}'::jsonb
    FROM tmp_coq c;
  $$,
  '23514',
  NULL,
  'Una distinta AUTOMATICA deve dichiarare il totale: e'' l''autocontrollo dell''import'
);

-- ============================================================
-- 3) GENERATA con dichiarato
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, origine, importo_dichiarato, meta)
  SELECT 'COQ_GEN_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         c.centro_id, script.fn_data_operativa(), script.fn_data_operativa(), 'GENERATA', 100.00,
         '{"test_scope":"pgtap_contabili_origine"}'::jsonb
    FROM tmp_coq c;
  $$,
  '23514',
  NULL,
  'Una distinta GENERATA non puo'' dichiarare un totale: nessuna sorgente l''ha fatto'
);

-- ============================================================
-- Fixture: una manuale che dichiara 100 e contiene 60 + 30 scartati
-- ============================================================
CREATE TEMP TABLE tmp_coq_dist AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione,
     origine, importo_dichiarato, meta)
  SELECT 'COQ_MAN_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         c.centro_id, script.fn_data_operativa(), script.fn_data_operativa(), 'MANUALE', 100.00,
         '{"test_scope":"pgtap_contabili_origine"}'::jsonb
    FROM tmp_coq c
  RETURNING id
)
SELECT id AS contabile_id FROM ins;

INSERT INTO pagamenti.vendite_contabili_righe (contabile_id, importo, stato_id, motivo_sospeso, meta)
SELECT d.contabile_id, 60.00, c.st_sospesa, 'in attesa', '{"test_scope":"pgtap_contabili_origine"}'::jsonb
  FROM tmp_coq_dist d, tmp_coq c;

-- ============================================================
-- 4) 🔴 60 dichiarati 100: non quadra
-- ============================================================
SELECT throws_ok(
  $$ UPDATE pagamenti.vendite_contabili
        SET stato_id = (SELECT st_validata FROM tmp_coq)
      WHERE id = (SELECT contabile_id FROM tmp_coq_dist) $$,
  'P0001',
  NULL,
  'Validare con un totale dichiarato che non quadra e'' rifiutato'
);

-- ============================================================
-- 5) ⚠️ E la riga SCARTATA fa quadrare: quel denaro E' arrivato
--   Se le scartate uscissero dalla somma, il primo scarto romperebbe una
--   distinta sana.
-- ============================================================
INSERT INTO pagamenti.vendite_contabili_righe (contabile_id, importo, stato_id, meta)
SELECT d.contabile_id, 40.00, c.st_scartata, '{"test_scope":"pgtap_contabili_origine"}'::jsonb
  FROM tmp_coq_dist d, tmp_coq c;

SELECT lives_ok(
  $$ UPDATE pagamenti.vendite_contabili
        SET stato_id = (SELECT st_validata FROM tmp_coq)
      WHERE id = (SELECT contabile_id FROM tmp_coq_dist) $$,
  'La quadratura conta anche le righe SCARTATE: quel denaro e'' arrivato comunque'
);

-- ============================================================
-- 6) Senza dichiarato non si controlla niente
-- ============================================================
CREATE TEMP TABLE tmp_coq_libera AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, origine, meta)
  SELECT 'COQ_LIB_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         c.centro_id, script.fn_data_operativa() + 2, script.fn_data_operativa(), 'MANUALE',
         '{"test_scope":"pgtap_contabili_origine"}'::jsonb
    FROM tmp_coq c
  RETURNING id
)
SELECT id AS contabile_id FROM ins;

INSERT INTO pagamenti.vendite_contabili_righe (contabile_id, importo, stato_id, motivo_sospeso, meta)
SELECT d.contabile_id, 7.00, c.st_sospesa, 'in attesa', '{"test_scope":"pgtap_contabili_origine"}'::jsonb
  FROM tmp_coq_libera d, tmp_coq c;

SELECT lives_ok(
  $$ UPDATE pagamenti.vendite_contabili
        SET stato_id = (SELECT st_validata FROM tmp_coq)
      WHERE id = (SELECT contabile_id FROM tmp_coq_libera) $$,
  'Senza totale dichiarato non si controlla niente: sul manuale e'' facoltativo'
);

-- ============================================================
-- 7) 🔴 S1-19 — due operatori, due distinte
--   ⚠️ Si cambia SOLO la GUC dell'utente applicativo: e' quella che
--   fn_get_or_create_vendite_contabile confronta con user_insert.
-- ============================================================
CREATE TEMP TABLE tmp_coq_op AS
SELECT set_config('app.jwt_user', 'pgtap_operatore_anna', true) AS ignora;

CREATE TEMP TABLE tmp_coq_anna AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_id FROM tmp_coq),
           p_data_contabile        => script.fn_data_operativa() + 3,
           p_origine               => 'MANUALE') AS id;

SELECT set_config('app.jwt_user', 'pgtap_operatore_marco', true);

CREATE TEMP TABLE tmp_coq_marco AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_id FROM tmp_coq),
           p_data_contabile        => script.fn_data_operativa() + 3,
           p_origine               => 'MANUALE') AS id;

SELECT isnt(
  (SELECT id FROM tmp_coq_anna),
  (SELECT id FROM tmp_coq_marco),
  'Due operatori nello stesso giorno e canale ottengono DUE distinte manuali: la contesa non esiste'
);

-- ============================================================
-- 8) 🔴 Riaprire una distinta non manuale
--   VALIDATA -> BOZZA e' in matrice; la restrizione vive nel guard.
-- ============================================================
CREATE TEMP TABLE tmp_coq_gen AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine, meta)
  SELECT 'COQ_GEN2_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         c.centro_id, script.fn_data_operativa() + 4, script.fn_data_operativa(), c.st_validata, 'GENERATA',
         '{"test_scope":"pgtap_contabili_origine"}'::jsonb
    FROM tmp_coq c
  RETURNING id
)
SELECT id AS contabile_id FROM ins;

SELECT throws_ok(
  $$ UPDATE pagamenti.vendite_contabili
        SET stato_id = (SELECT st_bozza FROM tmp_coq)
      WHERE id = (SELECT contabile_id FROM tmp_coq_gen) $$,
  'P0001',
  NULL,
  'Una distinta non manuale non si riapre: la matrice lo ammette, il guard no'
);

SELECT * FROM finish();
ROLLBACK;
