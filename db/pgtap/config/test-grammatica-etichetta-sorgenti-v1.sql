-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Una grammatica sola per i tipi di documento — L2b-1: il nome leggibile
--   della sorgente (config.sorgenti.etichetta) e la provenienza dell'ordine
--   stampata con quel nome, non col codice.
--   Brief: brief-db-grammatica-unica-documenti §12.9 (L2b-1 = (a), Tid
--   2026-10-19). ChangeSet: 20261020-22 (colonna e CHECK), il CSV
--   sorgenti.csv (80_data), 20261020-23 (NOT NULL, 90_end), 20261020-25 (la
--   versione 2 dello standard «Ordine di vendita»).
--
-- Elenco test (plan 8):
--  1) etichetta e' NOT NULL: una sorgente nuova entra col suo nome
--  2) etichetta e' character varying(60)
--  3) nessuna sorgente ha un'etichetta vuota o fatta di spazi (il seed)
--  4) svuotarla: 23502 (NOT NULL)
--  5) metterci solo spazi: 23514 (chk_sorgenti_etichetta_non_vuota)
--  6) le due origini che un ordine puo' avere si stampano «Preventivo» e
--       «Offerta» (il seed: sono le parole sulla carta)
--  7) ⭐ lo standard dell'ordine, nella versione che si stampa oggi, legge
--       ordine.origine.etichetta e non piu' ordine.origine.tipo (il codice)
--  8) ...e dichiara la forma dei dati 3, quella in cui il builder porta
--       l'etichetta (il patto di documenti.fn_guard_versione_contesto)
--
-- ⭐ Legge il SEED e lo standard, non una popolazione: le righe le portano
--   il CSV di 80_data e i changeSet 20261020-16/-25, presenti anche sul
--   database ricostruito da zero.
-- ⚠️ Test 7-8 solo sullo STANDARD: le copie degli emittenti sono dati
--   dell'applicazione e i changeSet non le toccano
--   (brief-db-modelli-documento-standard §4.1 Q-5).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- 1) NOT NULL
SELECT col_not_null('config', 'sorgenti', 'etichetta',
    '1) config.sorgenti.etichetta e'' NOT NULL: una sorgente nuova entra col suo nome');

-- 2) il tipo
SELECT col_type_is('config', 'sorgenti', 'etichetta', 'character varying(60)',
    '2) config.sorgenti.etichetta e'' character varying(60)');

-- 3) nessuna etichetta vuota
SELECT is_empty(
    $$SELECT s.codice_interno FROM config.sorgenti s
       WHERE s.etichetta IS NULL OR btrim(s.etichetta) = ''
       ORDER BY 1$$,
    '3) ogni sorgente ha un''etichetta non vuota');

-- 4) svuotarla
SAVEPOINT t4;
SELECT throws_ok(
    $$UPDATE config.sorgenti SET etichetta = NULL WHERE codice_interno = 'ORDINE_VENDITA'$$,
    '23502', NULL,
    '4) etichetta a NULL: rifiutata dal NOT NULL');
ROLLBACK TO SAVEPOINT t4;

-- 5) solo spazi
SAVEPOINT t5;
SELECT throws_ok(
    $$UPDATE config.sorgenti SET etichetta = '   ' WHERE codice_interno = 'ORDINE_VENDITA'$$,
    '23514', NULL,
    '5) etichetta di soli spazi: rifiutata da chk_sorgenti_etichetta_non_vuota');
ROLLBACK TO SAVEPOINT t5;

-- 6) le parole sulla carta per le origini dell'ordine
SELECT results_eq(
    $$SELECT s.codice_interno::text, s.etichetta::text
        FROM config.sorgenti s
       WHERE s.codice_interno IN ('PREVENTIVO', 'OFFERTA_COMMERCIALE')
       ORDER BY 1$$,
    $$VALUES ('OFFERTA_COMMERCIALE', 'Offerta'), ('PREVENTIVO', 'Preventivo')$$,
    '6) le origini di un ordine si stampano «Offerta» e «Preventivo»');

-- 7-8) lo standard dell'ordine, nella versione che si stampa oggi
--   (la stessa scelta del backend: PUBBLICATA, attiva, valida alla data
--   operativa, la piu' recente)
CREATE TEMP TABLE tmp_std AS
SELECT v.html_template, v.versione_contesto
  FROM documenti.template_documenti t
  JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id
  JOIN documenti.tipi_documento_output o ON o.id = t.tipo_documento_output_id
  JOIN documenti.template_documenti_versioni v ON v.template_documento_id = t.id
 WHERE t.standard
   AND s.codice_interno = 'ORDINE_VENDITA'
   AND o.codice_interno = 'ORDINE_VENDITA'
   AND t.codice_interno = 'ordine_vendita'
   AND v.stato = 'PUBBLICATA'
   AND v.attivo
   AND v.validita @> script.fn_data_operativa()
 ORDER BY v.versione DESC, v.id DESC
 LIMIT 1;

SELECT results_eq(
    $$SELECT strpos(html_template, 'origine.tipo') = 0,
             (length(html_template) - length(replace(html_template, 'ordine.origine.etichetta', '')))
               / length('ordine.origine.etichetta')
        FROM tmp_std$$,
    $$VALUES (true, 2)$$,
    '7) lo standard dell''ordine stampa la provenienza con ordine.origine.etichetta (2 volte), non piu'' col codice');

SELECT is(
    (SELECT versione_contesto FROM tmp_std),
    3,
    '8) la versione che si stampa oggi dichiara la forma dei dati 3 (il builder porta origine.etichetta)');

SELECT * FROM finish();
ROLLBACK;
