-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.template_documenti_versioni
--   - la non sovrapposizione delle versioni fuori bozza, col codice del verbo
--   - fuori bozza la versione non cambia (protect_pubblicata)
--   - quali versioni si cancellano (block_delete)
--   - la validita' generata dalle date
-- ------------------------------------------------------------
-- Indice test (1..12):
--  1) Setup: il modello dell'azienda della sessione
--  2) Validita' calcolata dalle date (colonna generata)
--  3) Una pubblicazione che si sovrappone a una versione fuori bozza:
--     E_DOCUMENTI_VERSIONE_OVERLAP, dal verbo
--  4) Una pubblicazione su un periodo disgiunto: ammessa
--  5) html_template di una PUBBLICATA non cambia: E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE
--  6) valido_dal di una PUBBLICATA non cambia: E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE
--  7) meta e' libero anche su una PUBBLICATA
--  8) DELETE di una PUBBLICATA: E_DOCUMENTI_VERSIONE_DELETE_BLOCKED
--  9) DELETE di una BOZZA che nessuna stampa ha usato: ammesso
-- 10) versione_contesto di una PUBBLICATA non cambia: E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE
-- 11) versione_contesto si cambia su una BOZZA, anche verso una forma non ancora prodotta
-- 12) DELETE di una OBSOLETA: E_DOCUMENTI_VERSIONE_DELETE_BLOCKED
--     (10-11 girano prima di 8-9: il 9 cancella la BOZZA che serve all'11)
-- ⚠️ Il ramo «bozza usata da una stampa» di block_delete non si costruisce: una
--    stampa nasce solo dalla versione in uso (documenti.fn_template_motivo_non_stampabile),
--    e il ramo resta per le stampe nate prima di quella regola.
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
-- La pubblicazione del template chiede documenti_template_manage (il verbo e'
--   SECURITY DEFINER col suo guard, giro 16 della porta 16): l'operatore del
--   contesto la riceve, perche' qui si prova altro.
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(script.fn_utente_di_sessione(), 'documenti_template_manage');
END $az$;

SELECT plan(12);

-- ============================================================
-- Setup contesto + template di base
-- ============================================================
CREATE TEMP TABLE tmp_tdv_ctx AS
SELECT
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO')                              AS sorgente_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'PREVENTIVO')                              AS tipo_output_id,
  (SELECT r.id FROM documenti.render_engine_documento r
    WHERE r.codice_interno = 'WEASYPRINT')                              AS render_id;

WITH ins AS (
  INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, is_default, attivo
  )
  SELECT tipo_output_id, 'PGTAP-TDV', 'PGTAP_TDV', 'Template per test versioni',
         sorgente_id, 'pgtap.builder', false, true
    FROM tmp_tdv_ctx
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_tdv_template FROM ins;

-- 1) Pre-condizione: il modello nasce con l'azienda della sessione
--    (script.trgfn_default_emittente_fiscale)
SELECT ok(
  (SELECT t.emittente_fiscale_id IS NOT NULL
     FROM documenti.template_documenti t
    WHERE t.id = (SELECT id FROM tmp_tdv_template)),
  '1) il modello nasce con l''azienda della sessione'
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
-- ⚠️ Una versione esce dalla bozza solo dal verbo della pubblicazione (guard
--   dello stato, 20261116-02): le pubblicazioni del test lo percorrono.
SELECT documenti.fn_pubblica_template_documento_versione(
  (SELECT id FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template) AND versione = 1),
  DATE '2026-01-01', 1, DATE '2026-06-30');

-- 3) Anti-overlap: una v2 che parte lo stesso giorno della v1 pubblicata. La
--    pubblicazione chiude solo le versioni che iniziano PRIMA: qui la
--    sovrapposizione resta, e la ferma il vincolo.
INSERT INTO documenti.template_documenti_versioni (
  template_documento_id, versione, stato, titolo, html_template,
  render_engine_id, valido_dal, valido_al, versione_contesto
)
SELECT (SELECT id FROM tmp_tdv_template),
       2, 'BOZZA', 'v2', '<html>v2</html>',
       (SELECT render_id FROM tmp_tdv_ctx),
       DATE '2026-04-01', DATE '2026-09-30', 1;

SELECT is(
  dbops.fn_pgtap_codice_errore($$SELECT documenti.fn_pubblica_template_documento_versione(
      (SELECT id FROM documenti.template_documenti_versioni
        WHERE template_documento_id = (SELECT id FROM tmp_tdv_template) AND versione = 2),
      DATE '2026-01-01', 1, DATE '2026-09-30')$$),
  'E_DOCUMENTI_VERSIONE_OVERLAP',
  '3) la sovrapposizione con una versione fuori bozza: E_DOCUMENTI_VERSIONE_OVERLAP, dal verbo'
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

SELECT documenti.fn_pubblica_template_documento_versione(
  (SELECT id FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template) AND versione = 3),
  DATE '2026-07-01', 1, DATE '2026-12-31');

SELECT is(
  (SELECT stato FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
      AND versione = 3),
  'PUBBLICATA',
  'Anti-overlap: PUBBLICATA con range disgiunto ammessa'
);

-- ============================================================
-- 5) Fuori bozza html_template non cambia
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.template_documenti_versioni
       SET html_template = '<html>HACK</html>'
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 1$$),
  'E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE',
  '5) html_template di una PUBBLICATA non cambia'
);

-- 6) valido_dal di una PUBBLICATA non cambia
SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.template_documenti_versioni
       SET valido_dal = DATE '2025-01-01'
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 1$$),
  'E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE',
  '6) valido_dal di una PUBBLICATA non cambia'
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
  '7) meta e'' libero anche su una PUBBLICATA'
);

-- ============================================================
-- 10-11) La forma dei dati dichiarata (versione_contesto, 20260930-17)
-- ============================================================
-- ⚠️ Prima del test 8/9: il 9 cancella la v2, che qui serve come BOZZA.
-- 10) Su una PUBBLICATA la forma non si cambia: aggirerebbe il controllo fatto
--     alla pubblicazione. Il codice dice che il rifiuto viene dal guard dello
--     stato, non da un CHECK.
SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.template_documenti_versioni
       SET versione_contesto = 2
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 1$$),
  'E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE',
  '10) versione_contesto di una PUBBLICATA non cambia'
);

-- 11) Su una BOZZA si': e' cosi' che si prepara la versione per la forma
--     successiva, anche una forma che il builder non produce ancora.
UPDATE documenti.template_documenti_versioni
   SET versione_contesto = 7
 WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
   AND versione = 2;

SELECT is(
  (SELECT versione_contesto FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
      AND versione = 2),
  7,
  '11) su una BOZZA versione_contesto si cambia, anche verso una forma non ancora prodotta'
);

-- ============================================================
-- 8) DELETE di una PUBBLICATA
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$DELETE FROM documenti.template_documenti_versioni
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 1$$),
  'E_DOCUMENTI_VERSIONE_DELETE_BLOCKED',
  '8) una PUBBLICATA non si cancella: E_DOCUMENTI_VERSIONE_DELETE_BLOCKED'
);

-- 9) DELETE di una BOZZA che nessuna stampa ha usato
DELETE FROM documenti.template_documenti_versioni
 WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
   AND versione = 2;

SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM documenti.template_documenti_versioni
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 2
  ),
  '9) una BOZZA che nessuna stampa ha usato si cancella'
);

-- ============================================================
-- 12) DELETE di una OBSOLETA
--     La v4 parte dentro la v3: pubblicandola, la v3 diventa OBSOLETA, chiusa
--     al giorno prima.
-- ============================================================
INSERT INTO documenti.template_documenti_versioni (
  template_documento_id, versione, stato, titolo, html_template,
  render_engine_id, versione_contesto
)
SELECT (SELECT id FROM tmp_tdv_template),
       4, 'BOZZA', 'v4', '<html>v4</html>',
       (SELECT render_id FROM tmp_tdv_ctx), 1;

SELECT documenti.fn_pubblica_template_documento_versione(
  (SELECT id FROM documenti.template_documenti_versioni
    WHERE template_documento_id = (SELECT id FROM tmp_tdv_template) AND versione = 4),
  DATE '2026-10-01', 1, NULL);

SELECT is(
  dbops.fn_pgtap_codice_errore($$DELETE FROM documenti.template_documenti_versioni
     WHERE template_documento_id = (SELECT id FROM tmp_tdv_template)
       AND versione = 3 AND stato = 'OBSOLETA'$$),
  'E_DOCUMENTI_VERSIONE_DELETE_BLOCKED',
  '12) una OBSOLETA non si cancella: E_DOCUMENTI_VERSIONE_DELETE_BLOCKED'
);

SELECT * FROM finish();
ROLLBACK;
