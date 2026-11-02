-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le due matrici di transizione di pagamenti, e i due guard che le leggono
--
-- Presidia i passi S1-3, S1-4 e S1-5 del lotto 2 del cantiere incassi.
--
-- Elenco test (plan 10):
-- 1)  La matrice della DISTINTA ha il grafo di D14-a-bis
-- 2)  La matrice della RIGA ha il grafo di D14-a
-- 3)  ⚠️ Le uscite da IMPORTATA NON sono seminate (l'import non esiste)
-- 4)  ⛔ STORNATA non compare in nessuna transizione
-- 5)  Nessuna transizione è dichiarata «manuale» (il frontend non esiste)
-- 6)  Una transizione ammessa sulla distinta passa
-- 7)  Una transizione NON ammessa sulla distinta è rifiutata
-- 8)  Da uno stato finale non si esce
-- 9)  ⭐ POSTATA è terminale: si chiude C-2 un lotto prima del previsto
-- 10) L'INSERT NON è vincolato dalla matrice (il sync dei fondi nasce in VALIDATA)
-- 11) ⭐ D20-e: ABBINATA -> DA_ABBINARE e' SEMINATA ma SPENTA (non tolta)
--
-- Scopo:
--  - i test 1-5 verificano il SEED: un grafo monco è il difetto silenzioso di
--    questa classe, perché il guard rifiuterebbe passaggi legittimi senza che
--    nessuno capisca perché;
--  - il test 3 presidia una DECISIONE, non un'omissione: le transizioni del
--    flusso non si seminano finché l'import non esiste — un catalogo pieno di
--    righe irraggiungibili insegna cose false (la lezione pagata con STORNATA);
--  - il test 10 è quello che protegge il percorso vivo: il sync dei fondi crea
--    le sue distinte direttamente in VALIDATA e le sue righe in ABBINATA, e
--    nessuna delle due è raggiungibile per transizione.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- 1) Il grafo della DISTINTA
-- ============================================================
SELECT is(
  (SELECT array_agg(sd.codice_interno || '->' || sa.codice_interno ORDER BY sd.codice_interno, sa.codice_interno)
     FROM pagamenti.transizioni_stati_contabile t
     JOIN pagamenti.vendite_contabili_stati sd ON sd.id = t.stato_da_id
     JOIN pagamenti.vendite_contabili_stati sa ON sa.id = t.stato_a_id
    WHERE t.attivo),
  ARRAY['BOZZA->ANNULLATA','BOZZA->VALIDATA',
        'VALIDATA->ANNULLATA','VALIDATA->BOZZA','VALIDATA->CHIUSA']::text[],
  'La matrice della distinta e'' quella di D14-a-bis, giro manuale'
);

-- ============================================================
-- 2) Il grafo della RIGA
-- ============================================================
SELECT is(
  (SELECT array_agg(sd.codice_interno || '->' || sa.codice_interno ORDER BY sd.codice_interno, sa.codice_interno)
     FROM pagamenti.transizioni_stati_contabile_riga t
     JOIN pagamenti.vendite_contabili_righe_stati sd ON sd.id = t.stato_da_id
     JOIN pagamenti.vendite_contabili_righe_stati sa ON sa.id = t.stato_a_id
    WHERE t.attivo),
  -- ⭐ Rev 2026-09-18 (D20-e, strada b): ABBINATA->DA_ABBINARE non e' piu'
  --   fra le ATTIVE — su una abbinata si ri-abbina, non si «sgancia».
  --   ABBINATA->SOSPESA resta. Il comportamento e' provato in
  --   test-contabile-validabile-v1 (test 14-15); qui si pinna il seed.
  ARRAY['ABBINATA->POSTATA','ABBINATA->SOSPESA',
        'DA_ABBINARE->ABBINATA','DA_ABBINARE->SCARTATA','DA_ABBINARE->SOSPESA',
        'SCARTATA->SOSPESA',
        'SOSPESA->ABBINATA','SOSPESA->DA_ABBINARE','SOSPESA->SCARTATA']::text[],
  'La matrice della riga e'' quella di D14-a, giro manuale, meno lo «sgancia» di D20-e'
);

-- ============================================================
-- 11) ⭐ D20-e — la coppia e' seminata SPENTA, non tolta
--   L'upsert del seed non cancella: togliere la riga dal VALUES l'avrebbe
--   lasciata accesa com'era sul database. Il seed la porta a attivo = false,
--   e questo test la vuole PRESENTE e SPENTA: se sparisse, qualcuno l'ha
--   tolta dal VALUES credendo di spegnerla.
-- ============================================================
SELECT is(
  (SELECT t.attivo
     FROM pagamenti.transizioni_stati_contabile_riga t
     JOIN pagamenti.vendite_contabili_righe_stati sd ON sd.id = t.stato_da_id
     JOIN pagamenti.vendite_contabili_righe_stati sa ON sa.id = t.stato_a_id
    WHERE sd.codice_interno = 'ABBINATA' AND sa.codice_interno = 'DA_ABBINARE'),
  false,
  'D20-e: ABBINATA -> DA_ABBINARE e'' seminata e spenta (attivo = false), non cancellata'
);

-- ============================================================
-- 3) ⚠️ Le uscite da IMPORTATA non ci sono, ed è una decisione
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pagamenti.transizioni_stati_contabile_riga t
     JOIN pagamenti.vendite_contabili_righe_stati sd ON sd.id = t.stato_da_id
    WHERE sd.codice_interno = 'IMPORTATA')
  + (SELECT count(*)::int
     FROM pagamenti.transizioni_stati_contabile t
     JOIN pagamenti.vendite_contabili_stati sd ON sd.id = t.stato_da_id
    WHERE sd.codice_interno = 'IMPORTATA'),
  0,
  'Nessuna uscita da IMPORTATA: le transizioni del flusso arrivano con l''import'
);

-- ============================================================
-- 4) ⛔ STORNATA è ritirata e non compare
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pagamenti.transizioni_stati_contabile_riga t
     JOIN pagamenti.vendite_contabili_righe_stati s
       ON s.id IN (t.stato_da_id, t.stato_a_id)
    WHERE s.codice_interno = 'STORNATA'),
  0,
  'STORNATA non compare in nessuna transizione: e'' ritirata'
);

-- ============================================================
-- 5) Nessun pulsante dichiarato: il frontend di pagamenti non esiste
--   ⚠️ Una label_key qui dentro e assente dai locales fa FALLIRE
--   scripts/check_i18n_keys.py.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM (
      SELECT meta FROM pagamenti.transizioni_stati_contabile
      UNION ALL
      SELECT meta FROM pagamenti.transizioni_stati_contabile_riga
   ) x WHERE COALESCE((meta ->> 'manuale')::boolean, false)),
  0,
  'Nessuna transizione e'' esposta come pulsante: il frontend di pagamenti non esiste ancora'
);

-- ============================================================
-- Fixture: una distinta su cui provare i passaggi
-- ============================================================
CREATE TEMP TABLE tmp_tsc AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, meta)
  SELECT 'TSC_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         c.id, script.fn_data_operativa(), script.fn_data_operativa(),
         jsonb_build_object('test_scope', 'pgtap_transizioni_stati_contabili')
    FROM pagamenti.centri_riscossione c
   WHERE c.codice_interno = 'BANCA'
  RETURNING id
)
SELECT id AS contabile_id,
       (SELECT id FROM pagamenti.vendite_contabili_stati WHERE codice_interno = 'VALIDATA')  AS validata_id,
       (SELECT id FROM pagamenti.vendite_contabili_stati WHERE codice_interno = 'CHIUSA')    AS chiusa_id,
       (SELECT id FROM pagamenti.vendite_contabili_stati WHERE codice_interno = 'BOZZA')     AS bozza_id
  FROM ins;

-- ============================================================
-- 6) BOZZA -> VALIDATA passa
-- ============================================================
SELECT lives_ok(
  $$ UPDATE pagamenti.vendite_contabili
        SET stato_id = (SELECT validata_id FROM tmp_tsc)
      WHERE id = (SELECT contabile_id FROM tmp_tsc) $$,
  'Una transizione ammessa sulla distinta passa (BOZZA -> VALIDATA)'
);

-- ============================================================
-- 7) VALIDATA -> IMPORTATA non è in matrice
-- ============================================================
SELECT throws_ok(
  $$ UPDATE pagamenti.vendite_contabili
        SET stato_id = (SELECT id FROM pagamenti.vendite_contabili_stati WHERE codice_interno = 'IMPORTATA')
      WHERE id = (SELECT contabile_id FROM tmp_tsc) $$,
  'P0001',
  NULL,
  'Una transizione che non e'' in matrice viene rifiutata'
);

-- ============================================================
-- 8) Da uno stato finale non si esce
--   ⚠️ Il verbo sta in un'istruzione SEPARATA dall'asserzione.
-- ============================================================
UPDATE pagamenti.vendite_contabili
   SET stato_id = (SELECT chiusa_id FROM tmp_tsc)
 WHERE id = (SELECT contabile_id FROM tmp_tsc);

SELECT throws_ok(
  $$ UPDATE pagamenti.vendite_contabili
        SET stato_id = (SELECT bozza_id FROM tmp_tsc)
      WHERE id = (SELECT contabile_id FROM tmp_tsc) $$,
  'P0001',
  NULL,
  'Da uno stato finale non si esce: CHIUSA non ha uscite'
);

-- ============================================================
-- 9) ⭐ POSTATA è terminale — è la metà di C-2 che si chiude qui
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pagamenti.transizioni_stati_contabile_riga t
     JOIN pagamenti.vendite_contabili_righe_stati sd ON sd.id = t.stato_da_id
    WHERE sd.codice_interno = 'POSTATA' AND t.attivo),
  0,
  'POSTATA e'' terminale: una riga registrata non torna ad ABBINATA (difetto C-2)'
);

-- ============================================================
-- 10) L'INSERT non è vincolato dalla matrice
--   Il sync dei fondi crea le sue distinte direttamente in VALIDATA.
-- ============================================================
SELECT lives_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, stato_id, meta)
  SELECT 'TSC_NASCITA_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
         c.id, script.fn_data_operativa(), script.fn_data_operativa(),
         (SELECT id FROM pagamenti.vendite_contabili_stati WHERE codice_interno = 'VALIDATA'),
         '{"test_scope":"pgtap_transizioni_stati_contabili"}'::jsonb
    FROM pagamenti.centri_riscossione c
   WHERE c.codice_interno = 'BANCA';
  $$,
  'Una distinta puo'' NASCERE in VALIDATA: la matrice vincola solo il cambio di stato'
);

SELECT * FROM finish();
ROLLBACK;
