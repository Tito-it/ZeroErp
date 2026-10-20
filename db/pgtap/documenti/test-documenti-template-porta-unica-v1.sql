-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un modello STANDARD, che solo il proprietario della tabella scrive (D-2): l'applicazione non puo' allestirlo. Il rifiuto all'app e' in test-documenti-template-standard-app-v1.sql
-- pgTAP test per Zero ERP
-- Test: la porta unica della stampa (brief-db-modelli-documento-standard §10.3
--   K-1 … K-5; changeSet 20261021-04 … -09)
-- ------------------------------------------------------------
-- Elenco test (plan 17):
--  Struttura
--   1) le due viste nuove sono security_invoker
--  K-1, «puo' stampare» (vw_template_versioni_stampabili)
--   2) un modello attivo con una versione pubblicata valida: una riga, con quella versione
--   3) un modello spento non c'e'
--   4) un modello con la sola bozza non c'e'
--  K-2, K-3, il modello indicato (fn_risolvi_template_applicabile, p_template_documento_id)
--   5) il suo modello stampabile: INDICATO, con la versione
--   6) lo standard, indicato da un emittente qualunque: INDICATO, con la versione dello standard
--   7) un modello spento: NON_STAMPABILE, «è disattivato»
--   8) un modello con la sola bozza: NON_STAMPABILE, «non ha una versione pubblicata valida oggi»
--   9) il modello di un'altra azienda: NON_COERENTE, «è di un'altra azienda»
--  10) un modello di un altro tipo: NON_COERENTE, «produce un altro tipo di documento»
--  11) un modello di un'altra sorgente: NON_COERENTE, «è per un'altra sorgente»
--  12) un id che non e' un modello: INPUT_INVALIDO
--  K-4, la coerenza del documento generato legge lo stesso BB
--  13) un documento di E1 reso col modello di E2: E_DOCUMENTI_GENERATO_COERENZA
--  14) il motivo del BB per lo stesso caso e' EMITTENTE
--  K-5, l'esito per emittente (vw_template_risoluzione_emittente)
--  15) E1 EMITTENTE col suo predefinito, E3 STANDARD, E4 SENZA_PREDEFINITO
--  16) ⭐ parita': per E1, E2, E3 la vista dice lo stesso modello e la stessa versione della stampa
--  17) ⭐ parita': per E4 la stampa solleva proprio SENZA_PREDEFINITO
--
-- Scopo:
--  - provare sui casi COSTRUITI che «puo' stampare» ha una sede sola e che il
--    modello indicato passa dalla stessa porta del modello risolto;
--  - ⚠️ gli standard del seed perdono il flag predefinito dentro la
--    transazione, perche' la coppia del test non collida col seed (come in
--    test-documenti-template-standard-v1). Gli emittenti sono NUOVI (helper).
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT 'E1'::text AS lato, m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _e SELECT 'E2', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _e SELECT 'E3', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _e SELECT 'E4', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e WHERE lato = 'E1'));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                  AS sorg,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'CONTRATTO')                   AS sorg2,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO')   AS tipo,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'CONTRATTO')    AS tipo2,
  (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT') AS render,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E1') AS e1,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E2') AS e2,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E3') AS e3,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E4') AS e4;

UPDATE documenti.template_documenti SET is_default = false WHERE standard AND is_default;

-- I modelli: (codice_interno, emittente, standard, tipo, sorgente, predefinito).
CREATE TEMP TABLE _m ON COMMIT DROP AS
SELECT * FROM (VALUES
  ('pgtap-pu-std', NULL,  true,  'tipo',  'sorg',  true),   -- lo standard
  ('pgtap-pu-m1',  'e1',  false, 'tipo',  'sorg',  true),   -- E1, stampa
  ('pgtap-pu-m2',  'e1',  false, 'tipo',  'sorg',  false),  -- E1, poi spento
  ('pgtap-pu-m3',  'e1',  false, 'tipo',  'sorg',  false),  -- E1, solo bozza
  ('pgtap-pu-m4',  'e1',  false, 'tipo2', 'sorg',  false),  -- E1, altro tipo
  ('pgtap-pu-m5',  'e1',  false, 'tipo2', 'sorg2', true),   -- E1, altra sorgente
  ('pgtap-pu-n1',  'e2',  false, 'tipo',  'sorg',  true),   -- E2, stampa
  ('pgtap-pu-p1',  'e4',  false, 'tipo',  'sorg',  false)   -- E4, stampa ma non predefinito
) AS m(codice_interno, chi, standard, quale_tipo, quale_sorg, is_default);

INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id, standard, is_default, attivo)
SELECT CASE m.quale_tipo WHEN 'tipo' THEN k.tipo ELSE k.tipo2 END,
       upper(m.codice_interno), m.codice_interno, 'Porta unica ' || m.codice_interno,
       CASE m.quale_sorg WHEN 'sorg' THEN k.sorg ELSE k.sorg2 END,
       'PREVENTIVO',
       CASE m.chi WHEN 'e1' THEN k.e1 WHEN 'e2' THEN k.e2 WHEN 'e4' THEN k.e4 END,
       m.standard, m.is_default, true
  FROM _m m, _k k;

-- Le versioni: pubblicate e valide per tutti, tranne m3 (solo bozza).
INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
SELECT t.id, 1,
       CASE WHEN t.codice_interno = 'pgtap-pu-m3' THEN 'BOZZA' ELSE 'PUBBLICATA' END,
       t.codice_interno || ' v1', '<html>' || t.codice_interno || '</html>', k.render,
       CASE WHEN t.codice_interno = 'pgtap-pu-m3' THEN NULL ELSE DATE '2026-01-01' END,
       NULL, 2
  FROM documenti.template_documenti t, _k k
 WHERE t.codice_interno LIKE 'pgtap-pu-%';

-- m2 si spegne: prima la versione, poi il modello.
UPDATE documenti.template_documenti_versioni v SET attivo = false
  FROM documenti.template_documenti t
 WHERE t.id = v.template_documento_id AND t.codice_interno = 'pgtap-pu-m2';
UPDATE documenti.template_documenti SET attivo = false WHERE codice_interno = 'pgtap-pu-m2';

CREATE TEMP TABLE _id ON COMMIT DROP AS
SELECT t.codice_interno, t.id, v.id AS versione_id
  FROM documenti.template_documenti t
  LEFT JOIN documenti.template_documenti_versioni v ON v.template_documento_id = t.id
 WHERE t.codice_interno LIKE 'pgtap-pu-%';

-- ============================================================
-- Struttura
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'documenti'
      AND c.relname IN ('vw_template_versioni_stampabili', 'vw_template_risoluzione_emittente')
      AND c.reloptions @> ARRAY['security_invoker=true']),
  2,
  '1) le due viste nuove sono security_invoker');

-- ============================================================
-- K-1
-- ============================================================
SELECT is(
  (SELECT row(count(*), max(s.template_versione_id))::text
     FROM documenti.vw_template_versioni_stampabili s
    WHERE s.template_documento_id = (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-m1')),
  (SELECT row(1::bigint, versione_id)::text FROM _id WHERE codice_interno = 'pgtap-pu-m1'),
  '2) un modello che stampa: una riga, con la sua versione');

SELECT is(
  (SELECT count(*)::int FROM documenti.vw_template_versioni_stampabili s
    WHERE s.template_documento_id = (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-m2')),
  0,
  '3) un modello spento non puo'' stampare');

SELECT is(
  (SELECT count(*)::int FROM documenti.vw_template_versioni_stampabili s
    WHERE s.template_documento_id = (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-m3')),
  0,
  '4) un modello con la sola bozza non puo'' stampare');

-- ============================================================
-- K-2, K-3: il modello indicato
-- ============================================================
SELECT is(
  (SELECT row(r.template_documento_id, r.livello, r.template_versione_id)::text
     FROM _k, documenti.fn_risolvi_template_applicabile(
            _k.sorg, _k.e1, _k.tipo, (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-m1')) r),
  (SELECT row(id, 'INDICATO', versione_id)::text FROM _id WHERE codice_interno = 'pgtap-pu-m1'),
  '5) il suo modello che stampa: INDICATO, con la versione');

SELECT is(
  (SELECT row(r.template_documento_id, r.livello, r.template_versione_id)::text
     FROM _k, documenti.fn_risolvi_template_applicabile(
            _k.sorg, _k.e3, NULL, (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-std')) r),
  (SELECT row(id, 'INDICATO', versione_id)::text FROM _id WHERE codice_interno = 'pgtap-pu-std'),
  '6) lo standard, indicato da un emittente qualunque: INDICATO');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(
      _k.sorg, _k.e1, _k.tipo, (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-m2'))$$,
  '%oggi non può stampare: è disattivato%',
  '7) un modello spento: NON_STAMPABILE');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(
      _k.sorg, _k.e1, _k.tipo, (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-m3'))$$,
  '%oggi non può stampare: non ha una versione pubblicata valida oggi%',
  '8) un modello con la sola bozza: NON_STAMPABILE');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(
      _k.sorg, _k.e1, _k.tipo, (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-n1'))$$,
  '%non è adatto a questo documento: è di un''altra azienda%',
  '9) il modello di un''altra azienda: NON_COERENTE');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(
      _k.sorg, _k.e1, _k.tipo, (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-m4'))$$,
  '%non è adatto a questo documento: produce un altro tipo di documento%',
  '10) un modello di un altro tipo: NON_COERENTE');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(
      _k.sorg, _k.e1, NULL, (SELECT id FROM _id WHERE codice_interno = 'pgtap-pu-m5'))$$,
  '%non è adatto a questo documento: è per un''altra sorgente%',
  '11) un modello di un''altra sorgente: NON_COERENTE');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e1, _k.tipo, 999999999999)$$,
  '%Parametro non valido per la scelta del modello di stampa%',
  '12) un id che non e'' un modello: INPUT_INVALIDO');

-- ============================================================
-- K-4: la coerenza del documento generato legge lo stesso BB
-- ============================================================
SELECT throws_like(
  $$INSERT INTO documenti.documenti_generati (
        tipo_documento_output_id, template_documento_id, template_versione_id,
        sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
        titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
        emittente_fiscale_id)
    SELECT k.tipo, i.id, i.versione_id, k.sorg, 'PGTAP-PU-DOC-1', NULL, 1,
           'Doc', 'doc.pdf', '{"_meta": {"context_version": 2}}'::jsonb,
           repeat('1', 64), repeat('2', 64), repeat('3', 64), k.e1
      FROM _k k, _id i WHERE i.codice_interno = 'pgtap-pu-n1'$$,
  '%Incoerenza referenziale%',
  '13) un documento di E1 reso col modello di E2: E_DOCUMENTI_GENERATO_COERENZA');

SELECT is(
  (SELECT documenti.fn_template_motivo_non_coerente(i.id, k.sorg, k.e1, k.tipo)
     FROM _k k, _id i WHERE i.codice_interno = 'pgtap-pu-n1'),
  'EMITTENTE',
  '14) il motivo del BB per lo stesso caso e'' EMITTENTE');

-- ============================================================
-- K-5: l'esito per emittente, e la parita' con la stampa
-- ============================================================
CREATE TEMP TABLE _v ON COMMIT DROP AS
SELECT x.lato, r.*
  FROM _e x, _k k, documenti.vw_template_risoluzione_emittente r
 WHERE r.emittente_fiscale_id = x.emittente_fiscale_id
   AND r.tipo_documento_output_id = k.tipo
   AND r.sorgente_tipo_id = k.sorg;

SELECT is(
  (SELECT string_agg(lato || ':' || esito, ' ' ORDER BY lato) FROM _v WHERE lato IN ('E1', 'E3', 'E4')),
  'E1:EMITTENTE E3:STANDARD E4:SENZA_PREDEFINITO',
  '15) la vista: E1 col suo predefinito, E3 con lo standard, E4 senza predefinito');

SELECT is(
  (SELECT string_agg(row(v.lato, v.template_documento_id, v.template_versione_id)::text, ' ' ORDER BY v.lato)
     FROM _v v WHERE v.lato IN ('E1', 'E2', 'E3')),
  (SELECT string_agg(row(x.lato, r.template_documento_id, r.template_versione_id)::text, ' ' ORDER BY x.lato)
     FROM _e x, _k k,
          documenti.fn_risolvi_template_applicabile(k.sorg, x.emittente_fiscale_id, k.tipo) r
    WHERE x.lato IN ('E1', 'E2', 'E3')),
  '16) parita'': la vista dice lo stesso modello e la stessa versione della stampa');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e4, _k.tipo)$$,
  '%ha modelli di stampa suoi, ma nessuno è segnato come predefinito%',
  '17) parita'': dove la vista dice SENZA_PREDEFINITO la stampa solleva quello');

SELECT * FROM finish();
ROLLBACK;
