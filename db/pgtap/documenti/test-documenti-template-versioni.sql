-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.template_documenti_versioni
--   - anti-overlap PUBBLICATA (EXCLUDE gist)
--   - guard A1 (immutabilita' PUBBLICATA)
--   - guard A2 (delete block PUBBLICATA/OBSOLETA/usata)
--   - daterange validita auto-calcolata da trigger
-- ------------------------------------------------------------
-- Indice test (1..11):
--  1) Setup: emittente fiscale disponibile, template di base creato
--  2) Validita' calcolata automaticamente (colonna generata)
--  3) Anti-overlap: due PUBBLICATA attive con range sovrapposti bloccate
--  4) Anti-overlap: range disgiunto ammesso
--  5) Guard A1: UPDATE html_template su PUBBLICATA bloccato
--  6) Guard A1: UPDATE valido_dal su PUBBLICATA bloccato
--  7) Guard A1: UPDATE meta (campo non protetto) ammesso anche su PUBBLICATA
--  8) Guard A2: DELETE su PUBBLICATA bloccato
--  9) Guard A2: DELETE su BOZZA non usata ammesso
-- 10) Guard A1: UPDATE versione_contesto su PUBBLICATA bloccato (20260930-17)
-- 11) versione_contesto si cambia su una BOZZA (D-C4)
--     (10-11 girano prima di 8-9: il 9 cancella la BOZZA che serve all'11)
-- Brief versione_contesto: brief-db-documenti-versione-contesto-template.md
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

SELECT plan(11);

-- ============================================================
-- Setup contesto + template di base
-- ============================================================
CREATE TEMP TABLE tmp_tdv_ctx AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo = true ORDER BY ef.id LIMIT 1)                      AS emittente_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO')                              AS sorgente_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'PREVENTIVO')                              AS tipo_output_id,
  (SELECT r.id FROM documenti.render_engine_documento r
    WHERE r.codice_interno = 'WEASYPRINT')                              AS render_id;

WITH ins AS (
  INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
    is_default, attivo
  )
  SELECT tipo_output_id, 'PGTAP-TDV', 'PGTAP_TDV', 'Template per test versioni',
         sorgente_id, 'pgtap.builder', emittente_id, false, true
    FROM tmp_tdv_ctx
   WHERE emittente_id IS NOT NULL
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_tdv_template FROM ins;

-- 1) Pre-condizione: template creato (e quindi emittente disponibile)
SELECT ok(
  (SELECT COUNT(*) > 0 FROM tmp_tdv_template),
  'Setup: emittente fiscale disponibile, template di base creato'
);

-- ============================================================
-- 2) validita' auto-calcolata
-- ============================================================
INSERT INTO documenti.template_documenti_versioni (
  template_documento_id, versione, stato, titolo, html_template,
  render_engine_id, valido_dal, valido_al, versione_contesto
)
SELECT (SELECT id FROM tmp_tdv_template),
       1, 'BOZZA', 'v1', '<html>v1</html>',
       (SELECT render_id FROM tmp_tdv_ctx),
       DATE '2026-01-01', DATE '2026-06-30', 1;

SELECT is(
  (SELECT validita FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
      AND versione = 1),
  daterange(DATE '2026-01-01', DATE '2026-06-30', '[]'),
  'Validita auto-calcolata correttamente (colonna generata)'
);

-- ============================================================
-- Pubblico la v1 e verifico anti-overlap
-- ============================================================
UPDATE documenti.template_documenti_versioni
   SET stato = 'PUBBLICATA'
 WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
   AND versione = 1;

-- 3) Anti-overlap: una seconda v2 PUBBLICATA con range sovrapposto deve fallire
INSERT INTO documenti.template_documenti_versioni (
  template_documento_id, versione, stato, titolo, html_template,
  render_engine_id, valido_dal, valido_al, versione_contesto
)
SELECT (SELECT id FROM tmp_tdv_template),
       2, 'BOZZA', 'v2', '<html>v2</html>',
       (SELECT render_id FROM tmp_tdv_ctx),
       DATE '2026-04-01', DATE '2026-09-30', 1;

SELECT throws_ok(
  $$UPDATE documenti.template_documenti_versioni
       SET stato = 'PUBBLICATA'
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 2$$,
  '23P01',
  NULL,
  'Anti-overlap: PUBBLICATA con range sovrapposto bloccata'
);

-- 4) Anti-overlap: range disgiunto ammesso
INSERT INTO documenti.template_documenti_versioni (
  template_documento_id, versione, stato, titolo, html_template,
  render_engine_id, valido_dal, valido_al, versione_contesto
)
SELECT (SELECT id FROM tmp_tdv_template),
       3, 'BOZZA', 'v3', '<html>v3</html>',
       (SELECT render_id FROM tmp_tdv_ctx),
       DATE '2026-07-01', DATE '2026-12-31', 1;

UPDATE documenti.template_documenti_versioni
   SET stato = 'PUBBLICATA'
 WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
   AND versione = 3;

SELECT is(
  (SELECT stato FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
      AND versione = 3),
  'PUBBLICATA',
  'Anti-overlap: PUBBLICATA con range disgiunto ammessa'
);

-- ============================================================
-- 5) Guard A1: immutabilita' PUBBLICATA su html_template
-- ============================================================
SELECT throws_ok(
  $$UPDATE documenti.template_documenti_versioni
       SET html_template = '<html>HACK</html>'
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 1$$,
  NULL,
  NULL,
  'A1: UPDATE html_template su PUBBLICATA bloccato'
);

-- 6) Guard A1: UPDATE valido_dal su PUBBLICATA bloccato
SELECT throws_ok(
  $$UPDATE documenti.template_documenti_versioni
       SET valido_dal = DATE '2025-01-01'
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 1$$,
  NULL,
  NULL,
  'A1: UPDATE valido_dal su PUBBLICATA bloccato'
);

-- 7) UPDATE meta (campo non in elenco protetto) ammesso anche su PUBBLICATA
UPDATE documenti.template_documenti_versioni
   SET meta = '{"updated_by_test": true}'::jsonb
 WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
   AND versione = 1;

SELECT is(
  (SELECT meta->>'updated_by_test'
     FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
      AND versione = 1),
  'true',
  'A1: UPDATE meta (non protetto) ammesso anche su PUBBLICATA'
);

-- ============================================================
-- 10-11) La forma dei dati dichiarata (versione_contesto, 20260930-17)
-- ============================================================
-- ⚠️ Prima del test 8/9: il 9 cancella la v2, che qui serve come BOZZA.
-- 10) Su una PUBBLICATA la forma non si cambia: aggirerebbe il controllo fatto
--     alla pubblicazione. throws_like sulla frase del Guard A1, non un NULL
--     generico: il rifiuto deve venire da lui, non da un CHECK.
SELECT throws_like(
  $$UPDATE documenti.template_documenti_versioni
       SET versione_contesto = 2
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 1$$,
  '%versione pubblicata%non puo''%modificata%',
  'A1: UPDATE versione_contesto su PUBBLICATA bloccato (20260930-17)'
);

-- 11) Su una BOZZA si': e' cosi' che si prepara la versione per la forma
--     successiva (D-C4), anche una forma che il builder non produce ancora.
UPDATE documenti.template_documenti_versioni
   SET versione_contesto = 7
 WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
   AND versione = 2;

SELECT is(
  (SELECT versione_contesto FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
      AND versione = 2),
  7,
  'D-C4: su una BOZZA versione_contesto si cambia, anche verso una forma non ancora prodotta'
);

-- ============================================================
-- 8) Guard A2: DELETE su PUBBLICATA bloccato
-- ============================================================
SELECT throws_ok(
  $$DELETE FROM documenti.template_documenti_versioni
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 1$$,
  NULL,
  NULL,
  'A2: DELETE su versione PUBBLICATA bloccato'
);

-- 9) Guard A2: DELETE su BOZZA non usata ammesso
DELETE FROM documenti.template_documenti_versioni
 WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
   AND versione = 2;

SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM documenti.template_documenti_versioni
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 2
  ),
  'A2: DELETE su BOZZA non usata ammesso'
);

SELECT * FROM finish();
ROLLBACK;
