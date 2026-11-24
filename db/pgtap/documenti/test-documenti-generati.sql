-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.documenti_generati
--   - la coerenza alla nascita (tipo, azienda)
--   - la numerazione con sorgente_riga NULL (NULLS NOT DISTINCT)
--   - il rifiuto della cancellazione
--   - lo snapshot, anche nei passaggi da e verso NULL
--   - lo stato con un valore solo
-- ------------------------------------------------------------
-- Indice test (1..13):
--  1) Setup: il modello dell'azienda del preventivo, con una versione in vigore
--  2) Una stampa coerente si registra
--  3) Un tipo di documento diverso da quello del modello: E_DOCUMENTI_GENERATO_COERENZA
--  4) Un'azienda diversa da quella del modello: E_DOCUMENTI_GENERATO_COERENZA
--  5) Stesso (tipo, chiave del documento, sorgente_riga NULL, progressivo): rifiutato
--     da uq_documenti_generati_sorgente_progressivo
--  6) DELETE di una stampa: E_DOCUMENTI_GENERATO_DELETE_BLOCKED
--  7) UPDATE di context_json: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE
--  8) UPDATE di template_versione_id: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE
--  9) Lo stato ha il solo valore GENERATO: ARCHIVIATO rifiutato da chk_documenti_generati_stato
-- 10) UPDATE di meta (libero): ammesso
-- 11) generato_da_user_id da NULL a un utente: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE
-- 12) generato_da_user_id da un utente a NULL: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE
-- 13) ... e la stampa con l'utente si era registrata
-- ⚠️ Ogni contesto porta _meta.context_version e la versione versione_contesto:
--    senza, il guard della forma (BEFORE INSERT) parlerebbe al posto dei rifiuti
--    che questi test attendono. Il guard ha il suo file:
--    test-documenti-versione-contesto-v1.sql.
-- ⚠️ La coerenza e' un trigger BEFORE: parla prima delle FK. Il 4 indica come
--    azienda un id fuori scala, e il codice atteso e' quello della coerenza, non
--    quello della FK: la regola confronta l'azienda della stampa con quella del
--    modello, e un'azienda diversa non va pescata fra quelle che ci sono.
-- ⚠️ sorgente_riga da NULL a un valore non si costruisce qui: guard_sorgente
--    (a10_guard_sorgente) parla prima dello snapshot (a10_protect_snapshot), e
--    rifiuta una riga che non e' del documento. Lo snapshot confronta
--    sorgente_riga con lo stesso IS DISTINCT FROM di generato_da_user_id (11, 12).
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

-- ⭐ La stampa e' di un preventivo VERO, del mondo dell'operatore in sessione: il
--   guard unico della sorgente verifica che il documento stampato esista, e la
--   chiave di un preventivo e' il suo uid. L'azienda e l'utente sono i suoi.
CREATE TEMP TABLE _dg_src AS
SELECT p.preventivo_uid, p.emittente_fiscale_id, p.auth_user_id
  FROM dbops.fn_pgtap_crea_preventivo('dg generati', 'DRAFT') p;


SELECT plan(13);

-- ============================================================
-- Setup: il modello dell'azienda del preventivo, con una versione in vigore
--   La versione vale da una data passata e non scade: la stampa nasce solo
--   dalla versione in uso alla data operativa.
-- ============================================================
CREATE TEMP TABLE tmp_dg_ctx AS
SELECT
  (SELECT emittente_fiscale_id FROM _dg_src)                     AS emittente_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO')                       AS sorgente_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'PREVENTIVO')                       AS tipo_output_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'CONTRATTO')                        AS tipo_altro_id,
  (SELECT r.id FROM documenti.render_engine_documento r
    WHERE r.codice_interno = 'WEASYPRINT')                       AS render_id;

WITH ins_t AS (
  INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
    is_default, attivo
  )
  SELECT tipo_output_id, 'PGTAP-DG', 'PGTAP_DG', 'Template per generati',
         sorgente_id, 'pgtap.builder', emittente_id, false, true
    FROM tmp_dg_ctx
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dg_template FROM ins_t;

WITH ins_v AS (
  INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, versione_contesto
  )
  SELECT (SELECT id FROM tmp_dg_template),
         1, 'BOZZA', 'v1', '<html>v1</html>',
         (SELECT render_id FROM tmp_dg_ctx), 1
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dg_versione FROM ins_v;

-- ⚠️ Una versione nasce in bozza ed esce dalla bozza solo dal verbo della
--   pubblicazione: la fixture lo percorre.
SELECT documenti.fn_pubblica_template_documento_versione(
  (SELECT id FROM tmp_dg_versione), script.fn_data_operativa() - 30, 1, NULL);

-- 1) Pre-condizione: setup completo
SELECT ok(
  (SELECT COUNT(*) FROM tmp_dg_versione) = 1
  AND (SELECT emittente_id IS NOT NULL AND tipo_altro_id IS NOT NULL FROM tmp_dg_ctx),
  'Setup: il modello dell''azienda del preventivo, con una versione in vigore'
);

-- ============================================================
-- 2) Una stampa coerente si registra
--    ⚠️ Col suo PDF principale (dbops.fn_pgtap_stampa_con_pdf): una stampa
--    senza principale non si registra (guard differito, che IMMEDIATE fa
--    scattare a fine istruzione).
-- ============================================================
SELECT dbops.fn_pgtap_stampa_con_pdf($i$
  INSERT INTO documenti.documenti_generati (
    tipo_documento_output_id, template_documento_id, template_versione_id,
    sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
    titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
    emittente_fiscale_id
  )
  SELECT
    (SELECT tipo_output_id FROM tmp_dg_ctx),
    (SELECT id FROM tmp_dg_template),
    (SELECT id FROM tmp_dg_versione),
    (SELECT sorgente_id FROM tmp_dg_ctx),
    (SELECT preventivo_uid FROM _dg_src), NULL, 1,
    'Doc 1', 'doc1.pdf',
    '{"tot": 100, "_meta": {"context_version": 1}}'::jsonb,
    repeat('1', 64), repeat('2', 64), repeat('3', 64),
    (SELECT emittente_id FROM tmp_dg_ctx)$i$);

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati
    WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)),
  1,
  '2) una stampa coerente si registra'
);

-- ============================================================
-- 3) Un tipo di documento diverso da quello del modello
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$INSERT INTO documenti.documenti_generati (
      tipo_documento_output_id, template_documento_id, template_versione_id,
      sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
      titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
      emittente_fiscale_id
    )
    SELECT
      (SELECT tipo_altro_id FROM tmp_dg_ctx),
      (SELECT id FROM tmp_dg_template),
      (SELECT id FROM tmp_dg_versione),
      (SELECT sorgente_id FROM tmp_dg_ctx),
      (SELECT preventivo_uid FROM _dg_src), NULL, 2,
      'Doc bad tipo', 'doc-bad.pdf',
      '{"x": 1, "_meta": {"context_version": 1}}'::jsonb,
      repeat('a', 64), repeat('b', 64), repeat('c', 64),
      (SELECT emittente_id FROM tmp_dg_ctx)$$),
  'E_DOCUMENTI_GENERATO_COERENZA',
  '3) un tipo di documento diverso da quello del modello: E_DOCUMENTI_GENERATO_COERENZA'
);

-- ============================================================
-- 4) Un'azienda diversa da quella del modello (id fuori scala: vedi testata)
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$INSERT INTO documenti.documenti_generati (
      tipo_documento_output_id, template_documento_id, template_versione_id,
      sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
      titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
      emittente_fiscale_id
    )
    SELECT
      (SELECT tipo_output_id FROM tmp_dg_ctx),
      (SELECT id FROM tmp_dg_template),
      (SELECT id FROM tmp_dg_versione),
      (SELECT sorgente_id FROM tmp_dg_ctx),
      (SELECT preventivo_uid FROM _dg_src), NULL, 3,
      'Doc bad em', 'doc-bad-em.pdf',
      '{"x": 2, "_meta": {"context_version": 1}}'::jsonb,
      repeat('a', 64), repeat('b', 64), repeat('c', 64),
      2147483647$$),
  'E_DOCUMENTI_GENERATO_COERENZA',
  '4) un''azienda diversa da quella del modello: E_DOCUMENTI_GENERATO_COERENZA'
);

-- ============================================================
-- 5) NULLS NOT DISTINCT: stesso (sorgente_tipo, uid, riga=NULL, progressivo)
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$INSERT INTO documenti.documenti_generati (
      tipo_documento_output_id, template_documento_id, template_versione_id,
      sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
      titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
      emittente_fiscale_id
    )
    SELECT
      (SELECT tipo_output_id FROM tmp_dg_ctx),
      (SELECT id FROM tmp_dg_template),
      (SELECT id FROM tmp_dg_versione),
      (SELECT sorgente_id FROM tmp_dg_ctx),
      (SELECT preventivo_uid FROM _dg_src), NULL, 1,
      'Doc dup', 'doc-dup.pdf',
      '{"x": 9, "_meta": {"context_version": 1}}'::jsonb,
      repeat('a', 64), repeat('b', 64), repeat('c', 64),
      (SELECT emittente_id FROM tmp_dg_ctx)$$),
  'uq_documenti_generati_sorgente_progressivo',
  '5) stesso documento, riga NULL e progressivo: rifiutato dalla numerazione'
);

-- ============================================================
-- 6) DELETE di una stampa
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$DELETE FROM documenti.documenti_generati
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)$$),
  'E_DOCUMENTI_GENERATO_DELETE_BLOCKED',
  '6) una stampa non si cancella: E_DOCUMENTI_GENERATO_DELETE_BLOCKED'
);

-- ============================================================
-- 7-8) Lo snapshot
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.documenti_generati
       SET context_json = '{"hack": true}'::jsonb
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)$$),
  'E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE',
  '7) context_json non cambia: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE'
);

SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.documenti_generati
       SET template_versione_id = 2147483647
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)$$),
  'E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE',
  '8) template_versione_id non cambia: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE'
);

-- 9) Lo stato ha il solo valore GENERATO: ARCHIVIATO e ANNULLATO non esistono,
--    e il CHECK li rifiuta.
SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.documenti_generati
       SET stato = 'ARCHIVIATO'
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)$$),
  'chk_documenti_generati_stato',
  '9) lo stato ARCHIVIATO non esiste: lo rifiuta chk_documenti_generati_stato'
);

-- 10) meta e' libero
UPDATE documenti.documenti_generati
   SET meta = '{"audit": "test"}'::jsonb
 WHERE template_versione_id = (SELECT id FROM tmp_dg_versione);

SELECT is(
  (SELECT meta->>'audit' FROM documenti.documenti_generati
    WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)),
  'test',
  '10) meta e'' libero: l''UPDATE passa'
);

-- ============================================================
-- 11-13) Lo snapshot nei passaggi da e verso NULL (IS DISTINCT FROM)
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.documenti_generati
       SET generato_da_user_id = (SELECT auth_user_id FROM _dg_src)
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)
       AND progressivo_sorgente = 1$$),
  'E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE',
  '11) generato_da_user_id da NULL a un utente: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE'
);

SELECT dbops.fn_pgtap_stampa_con_pdf($i$
  INSERT INTO documenti.documenti_generati (
    tipo_documento_output_id, template_documento_id, template_versione_id,
    sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
    titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
    emittente_fiscale_id, generato_da_user_id
  )
  SELECT
    (SELECT tipo_output_id FROM tmp_dg_ctx),
    (SELECT id FROM tmp_dg_template),
    (SELECT id FROM tmp_dg_versione),
    (SELECT sorgente_id FROM tmp_dg_ctx),
    (SELECT preventivo_uid FROM _dg_src), NULL, 2,
    'Doc 2', 'doc2.pdf',
    '{"tot": 200, "_meta": {"context_version": 1}}'::jsonb,
    repeat('4', 64), repeat('5', 64), repeat('6', 64),
    (SELECT emittente_id FROM tmp_dg_ctx),
    (SELECT auth_user_id FROM _dg_src)$i$);

SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.documenti_generati
       SET generato_da_user_id = NULL
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)
       AND progressivo_sorgente = 2$$),
  'E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE',
  '12) generato_da_user_id da un utente a NULL: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE'
);

SELECT is(
  (SELECT generato_da_user_id FROM documenti.documenti_generati
    WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)
      AND progressivo_sorgente = 2),
  (SELECT auth_user_id FROM _dg_src),
  '13) ... e la stampa con l''utente si era registrata, col suo utente'
);

SELECT * FROM finish();
ROLLBACK;
