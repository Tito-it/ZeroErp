-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce modelli STANDARD, che solo il proprietario della tabella scrive (D-2): l'applicazione non puo' allestirli. La madre la chiama l'applicazione, ma lo standard da cui parte va costruito
-- pgTAP test per Zero ERP
-- Test: «personalizza» e lo scarto (brief-db-modelli-documento-standard §10.3
--   K-6, K-10; D-6, D-9; changeSet 20261021-10 … -12)
-- ------------------------------------------------------------
-- Elenco test (plan 14):
--  La madre (fn_personalizza_template_standard)
--   1) E1 senza modelli suoi: la copia e' sua, non standard, e nasce predefinita (D-6)
--   2) la bozza v1 deriva dalla versione con cui lo standard stampa OGGI, non da una pubblicata futura (D-9)
--   3) la bozza copia il corpo e la forma dei dati, senza date
--   4) con la sola bozza E1 stampa ancora con lo standard
--   5) pubblicata, E1 stampa con la copia
--   6) E2 ha gia' un suo predefinito: la copia nasce non predefinita (D-6)
--   7) da un modello che non e' standard: E_DOCUMENTI_PERSONALIZZA_NON_STANDARD
--   8) da uno standard spento: E_DOCUMENTI_TEMPLATE_NON_STAMPABILE
--   9) un codice gia' dell'emittente per la sorgente: 23505
--  10) ⭐ tutto o niente: dopo il rifiuto non resta la testata
--  Il BB della copia (fn_crea_bozza_da_versione)
--  11) copia nello stesso modello: numero successivo, titolo sostituito, nessuna origine
--  Lo scarto (vw_template_personalizzati_scarto)
--  12) la copia appena pubblicata e' ALLINEATA, sullo standard da cui deriva
--  13) ⭐ la copia di uno standard NON predefinito si confronta con lui, ed e' ALLINEATA
--  14) un modello d'emittente senza origine si confronta col predefinito della coppia: ORIGINE_NON_DICHIARATA
--
-- Scopo: provare sui casi COSTRUITI la madre e lo scarto con lo stesso
--   riferimento (la versione con cui lo standard stampa oggi).
--   ⚠️ Gli standard del seed perdono il flag predefinito dentro la transazione.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT 'E1'::text AS lato, m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _e SELECT 'E2', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _e SELECT 'E3', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e WHERE lato = 'E1'));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                  AS sorg,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO')   AS tipo,
  (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT') AS render,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E1') AS e1,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E2') AS e2,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E3') AS e3;

UPDATE documenti.template_documenti SET is_default = false WHERE standard AND is_default;

-- S1 standard predefinito, S2 standard non predefinito, S3 standard poi spento;
-- N2 il predefinito di E2.
INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id, standard, is_default, attivo)
SELECT k.tipo, upper(m.ci), m.ci, 'Personalizza ' || m.ci, k.sorg, 'PREVENTIVO',
       CASE WHEN m.ci = 'pgtap-pz-n2' THEN k.e2 END,
       m.ci <> 'pgtap-pz-n2', m.ci IN ('pgtap-pz-s1', 'pgtap-pz-n2'), true
  FROM _k k, (VALUES ('pgtap-pz-s1'), ('pgtap-pz-s2'), ('pgtap-pz-s3'), ('pgtap-pz-n2')) m(ci);

-- v1 pubblicata e valida da gennaio per tutti; S1 ha anche una v2 pubblicata che
-- vale solo fra trenta giorni (forma dei dati diversa, per riconoscerla).
INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
SELECT t.id, 1, 'PUBBLICATA', t.codice_interno || ' v1', '<html>' || t.codice_interno || ' v1</html>',
       k.render, DATE '2026-01-01', script.fn_data_operativa() + 29, 2
  FROM documenti.template_documenti t, _k k
 WHERE t.codice_interno LIKE 'pgtap-pz-%';
INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
SELECT t.id, 2, 'PUBBLICATA', 's1 v2', '<html>s1 v2</html>', k.render,
       script.fn_data_operativa() + 30, NULL, 3
  FROM documenti.template_documenti t, _k k
 WHERE t.codice_interno = 'pgtap-pz-s1';

-- S3 si spegne: prima la versione, poi il modello.
UPDATE documenti.template_documenti_versioni v SET attivo = false
  FROM documenti.template_documenti t
 WHERE t.id = v.template_documento_id AND t.codice_interno = 'pgtap-pz-s3';
UPDATE documenti.template_documenti SET attivo = false WHERE codice_interno = 'pgtap-pz-s3';

CREATE TEMP TABLE _id ON COMMIT DROP AS
SELECT t.codice_interno, t.id,
       max(v.id) FILTER (WHERE v.versione = 1) AS v1,
       max(v.id) FILTER (WHERE v.versione = 2) AS v2
  FROM documenti.template_documenti t
  JOIN documenti.template_documenti_versioni v ON v.template_documento_id = t.id
 WHERE t.codice_interno LIKE 'pgtap-pz-%'
 GROUP BY t.codice_interno, t.id;

-- ============================================================
-- La madre
-- ============================================================
CREATE TEMP TABLE _c ON COMMIT DROP AS
SELECT 'C1'::text AS copia,
       documenti.fn_personalizza_template_standard(
           (SELECT id FROM _id WHERE codice_interno = 'pgtap-pz-s1'), (SELECT e1 FROM _k)) AS id;

SELECT is(
  (SELECT row(t.emittente_fiscale_id, t.standard, t.is_default, t.codice_interno)::text
     FROM documenti.template_documenti t WHERE t.id = (SELECT id FROM _c WHERE copia = 'C1')),
  (SELECT row(e1, false, true, 'pgtap-pz-s1')::text FROM _k),
  '1) la copia e'' di E1, non standard, e nasce predefinita');

SELECT is(
  (SELECT row(v.stato, v.versione, v.derivata_da_versione_id)::text
     FROM documenti.template_documenti_versioni v
    WHERE v.template_documento_id = (SELECT id FROM _c WHERE copia = 'C1')),
  (SELECT row('BOZZA', 1, v1)::text FROM _id WHERE codice_interno = 'pgtap-pz-s1'),
  '2) la bozza v1 deriva dalla versione con cui lo standard stampa oggi, non dalla futura');

SELECT is(
  (SELECT row(v.html_template, v.versione_contesto, v.valido_dal, v.valido_al)::text
     FROM documenti.template_documenti_versioni v
    WHERE v.template_documento_id = (SELECT id FROM _c WHERE copia = 'C1')),
  row('<html>pgtap-pz-s1 v1</html>', 2, NULL::date, NULL::date)::text,
  '3) la bozza copia corpo e forma dei dati, senza date');

SELECT is(
  (SELECT row(r.template_documento_id, r.livello)::text
     FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e1, _k.tipo) r),
  (SELECT row(id, 'STANDARD')::text FROM _id WHERE codice_interno = 'pgtap-pz-s1'),
  '4) con la sola bozza E1 stampa ancora con lo standard');

SELECT documenti.fn_pubblica_template_documento_versione(v.id, script.fn_data_operativa(), 2)
  FROM documenti.template_documenti_versioni v
 WHERE v.template_documento_id = (SELECT id FROM _c WHERE copia = 'C1');

SELECT is(
  (SELECT row(r.template_documento_id, r.livello)::text
     FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e1, _k.tipo) r),
  (SELECT row(id, 'EMITTENTE')::text FROM _c WHERE copia = 'C1'),
  '5) pubblicata, E1 stampa con la copia');

INSERT INTO _c
SELECT 'C2', documenti.fn_personalizza_template_standard(
           (SELECT id FROM _id WHERE codice_interno = 'pgtap-pz-s1'), (SELECT e2 FROM _k));

SELECT is(
  (SELECT t.is_default FROM documenti.template_documenti t WHERE t.id = (SELECT id FROM _c WHERE copia = 'C2')),
  false,
  '6) E2 ha gia'' un suo predefinito: la copia nasce non predefinita');

SELECT throws_like(
  $$SELECT documenti.fn_personalizza_template_standard(
      (SELECT id FROM _id WHERE codice_interno = 'pgtap-pz-n2'), (SELECT e3 FROM _k))$$,
  '%Si personalizza solo un modello standard%',
  '7) da un modello che non e'' standard: rifiutato');

SELECT throws_like(
  $$SELECT documenti.fn_personalizza_template_standard(
      (SELECT id FROM _id WHERE codice_interno = 'pgtap-pz-s3'), (SELECT e3 FROM _k))$$,
  '%oggi non può stampare: è disattivato%',
  '8) da uno standard spento: NON_STAMPABILE');


CREATE TEMP TABLE _n ON COMMIT DROP AS
SELECT count(*) AS prima FROM documenti.template_documenti WHERE emittente_fiscale_id = (SELECT e1 FROM _k);

-- E1 ha gia' il codice dello standard (la copia C1): la seconda copia collide
-- sull'unico per emittente + sorgente + codice, dopo che la madre ha deciso
-- tutto il resto.
SELECT throws_ok(
  $$SELECT documenti.fn_personalizza_template_standard(
      (SELECT id FROM _id WHERE codice_interno = 'pgtap-pz-s1'), (SELECT e1 FROM _k))$$,
  '23505', NULL,
  '9) un codice gia'' dell''emittente per la sorgente: rifiutato');

SELECT is(
  (SELECT count(*) FROM documenti.template_documenti WHERE emittente_fiscale_id = (SELECT e1 FROM _k)),
  (SELECT prima FROM _n),
  '10) tutto o niente: dopo il rifiuto non resta nessuna testata in piu''');

-- ============================================================
-- Il BB della copia
-- ============================================================
CREATE TEMP TABLE _b ON COMMIT DROP AS
SELECT documenti.fn_crea_bozza_da_versione(
           p_versione_origine_id   => (SELECT v1 FROM _id WHERE codice_interno = 'pgtap-pz-n2'),
           p_template_documento_id => (SELECT id FROM _id WHERE codice_interno = 'pgtap-pz-n2'),
           p_titolo                => 'clone di prova') AS id;

SELECT is(
  (SELECT row(v.versione, v.stato, v.titolo, v.derivata_da_versione_id)::text
     FROM documenti.template_documenti_versioni v WHERE v.id = (SELECT id FROM _b)),
  row(2, 'BOZZA', 'clone di prova', NULL::bigint)::text,
  '11) copia nello stesso modello: numero successivo, titolo sostituito, nessuna origine');

-- ============================================================
-- Lo scarto
-- ============================================================
SELECT is(
  (SELECT row(sc.stato, sc.standard_template_documento_id, sc.standard_versione_id)::text
     FROM documenti.vw_template_personalizzati_scarto sc
    WHERE sc.template_documento_id = (SELECT id FROM _c WHERE copia = 'C1')),
  (SELECT row('ALLINEATA', id, v1)::text FROM _id WHERE codice_interno = 'pgtap-pz-s1'),
  '12) la copia appena pubblicata e'' ALLINEATA, sullo standard da cui deriva');

INSERT INTO _c
SELECT 'C3', documenti.fn_personalizza_template_standard(
           (SELECT id FROM _id WHERE codice_interno = 'pgtap-pz-s2'), (SELECT e3 FROM _k));
SELECT documenti.fn_pubblica_template_documento_versione(v.id, script.fn_data_operativa(), 2)
  FROM documenti.template_documenti_versioni v
 WHERE v.template_documento_id = (SELECT id FROM _c WHERE copia = 'C3');

SELECT is(
  (SELECT row(sc.stato, sc.standard_template_documento_id)::text
     FROM documenti.vw_template_personalizzati_scarto sc
    WHERE sc.template_documento_id = (SELECT id FROM _c WHERE copia = 'C3')),
  (SELECT row('ALLINEATA', id)::text FROM _id WHERE codice_interno = 'pgtap-pz-s2'),
  '13) la copia di uno standard NON predefinito si confronta con lui: ALLINEATA');

SELECT is(
  (SELECT row(sc.stato, sc.standard_template_documento_id)::text
     FROM documenti.vw_template_personalizzati_scarto sc
    WHERE sc.template_documento_id = (SELECT id FROM _id WHERE codice_interno = 'pgtap-pz-n2')),
  (SELECT row('ORIGINE_NON_DICHIARATA', id)::text FROM _id WHERE codice_interno = 'pgtap-pz-s1'),
  '14) un modello d''emittente senza origine si confronta col predefinito della coppia');

SELECT * FROM finish();
ROLLBACK;
