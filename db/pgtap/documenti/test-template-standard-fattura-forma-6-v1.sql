-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La fattura stampata porta i documenti di origine: lo standard «Fattura di
--   vendita» in forma 6 (fattura.origini al posto di fattura.origine).
--   Brief: brief-modello-documento-vendita §15.16 (D-S1 = forma 6, Tid
--   2026-10-27), §15.17 (K-S1, K-S3). ChangeSet: 20261028-01.
--
-- Elenco test (plan 6):
--  1) lo standard della fattura ha UNA versione che si stampa oggi
--       (PUBBLICATA, attiva, valida alla data operativa)
--  2) ...dichiara la forma dei dati 6 (il patto di
--       documenti.fn_guard_versione_contesto: il builder porta origini)
--  3) ...non legge piu' fattura.origine (la chiave che la forma 6 toglie:
--       con StrictUndefined fermerebbe il render)
--  4) ...stampa l'elenco: un `for` su fattura.origini, con etichetta e codice
--  5) la versione 1 (forma 5) non e' piu' valida alla data operativa
--  6) nessuna BOZZA sullo standard: lo cambiano solo i changeSet
--
-- ⭐ Legge lo standard, non una popolazione: lo portano i changeSet
--   20261020-18 e 20261028-01, presenti anche sul database ricostruito da
--   zero.
-- ⚠️ Solo lo STANDARD: le copie degli emittenti sono dati dell'applicazione
--   e i changeSet non le toccano (brief-db-modelli-documento-standard §4.1
--   Q-5); le porta alla forma 6 lo script una tantum del brief (K-S2).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

CREATE TEMP TABLE tmp_tpl AS
SELECT t.id
  FROM documenti.template_documenti t
  JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id
  JOIN documenti.tipi_documento_output o ON o.id = t.tipo_documento_output_id
 WHERE t.standard
   AND s.codice_interno = 'FATTURA'
   AND o.codice_interno = 'FATTURA_VENDITA'
   AND t.codice_interno = 'fattura_vendita';

-- Le versioni che si stampano oggi (la scelta del backend: PUBBLICATA,
-- attiva, valida alla data operativa).
CREATE TEMP TABLE tmp_oggi AS
SELECT v.versione, v.html_template, v.versione_contesto
  FROM documenti.template_documenti_versioni v
 WHERE v.template_documento_id = (SELECT id FROM tmp_tpl)
   AND v.stato = 'PUBBLICATA'
   AND v.attivo
   AND v.validita @> script.fn_data_operativa();

SELECT is(
    (SELECT count(*)::int FROM tmp_oggi),
    1,
    '1) lo standard della fattura ha una sola versione che si stampa oggi');

SELECT is(
    (SELECT versione_contesto FROM tmp_oggi),
    6,
    '2) la versione che si stampa oggi dichiara la forma dei dati 6');

SELECT is(
    (SELECT strpos(html_template, 'fattura.origine.') FROM tmp_oggi),
    0,
    '3) la versione che si stampa oggi non legge fattura.origine (tolta dalla forma 6)');

SELECT results_eq(
    $$SELECT strpos(html_template, '{% for o in fattura.origini %}') > 0,
             strpos(html_template, '{{ o.etichetta }}') > 0,
             strpos(html_template, '{{ o.codice }}') > 0
        FROM tmp_oggi$$,
    $$VALUES (true, true, true)$$,
    '4) la versione che si stampa oggi elenca fattura.origini, con etichetta e codice');

SELECT is(
    (SELECT count(*)::int
       FROM documenti.template_documenti_versioni v
      WHERE v.template_documento_id = (SELECT id FROM tmp_tpl)
        AND v.versione = 1
        AND v.validita @> script.fn_data_operativa()),
    0,
    '5) la versione 1 (forma 5) non e'' piu'' valida alla data operativa');

SELECT is(
    (SELECT count(*)::int
       FROM documenti.template_documenti_versioni v
      WHERE v.template_documento_id = (SELECT id FROM tmp_tpl)
        AND v.stato = 'BOZZA'),
    0,
    '6) nessuna BOZZA sullo standard della fattura');

SELECT * FROM finish();
ROLLBACK;
