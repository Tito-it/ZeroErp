-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: perche' un modello oggi non stampa, e chi lo chiede; la stampa nasce
--   dalla versione in uso; lo scarto di una copia il cui standard non stampa;
--   la risoluzione senza tipo nomina il documento; le risorse utilizzabili oggi.
-- Oggetti:
--   documenti.fn_template_motivo_non_stampabile
--   documenti.trgfn_documenti_generati_check_coerenza
--   documenti.fn_risolvi_template_applicabile
--   documenti.vw_template_personalizzati_scarto
--   documenti.vw_template_risoluzione_emittente
--   documenti.fn_template_motivo_non_coerente
--   documenti.vw_template_asset_utilizzabili
--
-- Elenco test (plan 26):
--   La forma
--   1) il building block del motivo esiste, con la versione facoltativa
--   2) la vista delle risorse utilizzabili esiste
--   3) ... e si legge coi privilegi di chi interroga (security_invoker)
--   Perche' un modello oggi non stampa
--   4) un modello che non esiste: MODELLO_INESISTENTE
--   5) un modello con la sola bozza: NESSUNA_VERSIONE_VALIDA
--   6) il modello che stampa: NULL
--   7) ... con la versione in uso: NULL
--   8) ... con la versione superata ieri: VERSIONE_NON_IN_USO
--   La nascita della stampa
--   9) dalla versione superata: rifiutata
--  10) da una bozza: rifiutata
--  11) con la versione di un altro modello: rifiutata
--  12) dalla versione in uso: si registra
--   Lo scarto
--  13) una copia senza standard che stampa resta nello scarto: STANDARD_NON_STAMPA
--  14) ... senza standard di riferimento ne' sua versione
--   La risoluzione
--  15) senza tipo, su una sorgente senza modelli che stampano: la frase nomina
--      la sorgente, non «?»
--  16) ... ed e' E_DOCUMENTI_TEMPLATE_NON_RISOLTO
--  17) il modello per un'altra sorgente: motivo SORGENTE
--  18) il modello per un altro tipo: motivo TIPO
--  19) una coppia col solo modello proprio, senza versione accesa, e nessuno
--      standard: la vista della risoluzione dice NON_RISOLTO
--  20) ... e la stampa lo stesso, col suo codice
--   Le risorse
--  21) accesa e valida oggi: utilizzabile
--  22) spenta: non utilizzabile
--  23) valida da domani: non utilizzabile
--   Il modello spento
--  24) il building block dice MODELLO_SPENTO
--  25) la risoluzione col modello indicato lo rifiuta: E_DOCUMENTI_TEMPLATE_NON_STAMPABILE
--  26) una stampa non nasce da un modello spento
--
-- Scopo:
--  - provare sui casi COSTRUITI le regole del giro 4 della revisione di
--    documenti: un'azienda nuova, i suoi modelli e le sue risorse, un suo
--    preventivo. Nessuna riga di dbdev entra come soggetto.
--  - Le coppie senza standard sono contratto del seed: gli standard sono dei
--    sei documenti di vendita, ciascuno col tipo della sua sorgente. Non ce
--    n'e' per (CONTRATTO, PREVENTIVO) ne' per la sorgente ORDINE_ACQUISTO.
--  - Il motivo della coerenza sta nel contesto del log, non nell'eccezione:
--    9-11 e 26 asseriscono il codice; quale regola parla lo dicono 4-8 e 24,
--    sul building block che la coerenza legge.
-- ⭐ Senza i changeSet 20261116-05 … -09 (prova sullo scratch, 2026-11-16) la
--   corsa si interrompe al 4: il building block del motivo non esiste. Con
--   l'estratto 26 su 26. I casi che il giro corregge: 9, 10 e 26 (la stampa
--   nasceva da una versione superata, da una bozza, da un modello spento; l'11
--   era gia' rifiutato e resta a presidio dell'ordine delle domande), 13-14
--   (la copia spariva dallo scarto), 15 (la frase diceva «?»), 21-23 (la regola
--   delle risorse non aveva sede).
-- ⚠️ Gira come applicazione: le versioni escono di bozza dal verbo.
-- ------------------------------------------------------------

BEGIN;

-- Un'azienda nuova, senza modelli suoi.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;
-- La pubblicazione del template chiede documenti_template_manage (il verbo e'
--   SECURITY DEFINER col suo guard, giro 16 della porta 16): l'operatore del
--   contesto la riceve, perche' qui si prova altro.
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(script.fn_utente_di_sessione(), 'documenti_template_manage');
END $az$;

-- La stampa e' di un preventivo vero del mondo dell'operatore: il guard della
-- sorgente verifica che il documento stampato esista.
CREATE TEMP TABLE _src ON COMMIT DROP AS
SELECT p.preventivo_uid FROM dbops.fn_pgtap_crea_preventivo('dg risoluzione', 'DRAFT') p;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- ============================================================
-- Fixture
--   M: il modello predefinito dell'azienda per il preventivo. V1 in vigore da
--      dieci giorni, V2 da ieri: la V1 e' superata.
--   B: un modello del preventivo con la sola bozza.
--   K: un modello dell'azienda per (CONTRATTO, PREVENTIVO), coppia senza
--      standard, con una versione in vigore.
-- ============================================================
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                   AS sorg,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_ACQUISTO')              AS sorg_vuota,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO')    AS tipo,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'CONTRATTO')     AS tipo2,
  (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT') AS render,
  (SELECT a.id FROM documenti.tipi_asset_documento a WHERE a.codice_interno = 'LOGO')          AS logo,
  (SELECT emittente_fiscale_id FROM _e)                                                        AS em,
  script.fn_data_operativa()                                                                   AS oggi;

CREATE TEMP TABLE _m ON COMMIT DROP AS
WITH ins AS (
  INSERT INTO documenti.template_documenti (
      tipo_documento_output_id, codice, codice_interno, descrizione,
      sorgente_tipo_id, context_builder_code, emittente_fiscale_id, is_default, attivo)
  SELECT x.tipo, 'PGTAP-RIS-' || x.k, 'pgtap-ris-' || x.k, 'Modello della risoluzione ' || x.k,
         k.sorg, 'PREVENTIVO', k.em, x.k = 'M', true
    FROM _k k,
         LATERAL (VALUES ('M', k.tipo), ('B', k.tipo), ('K', k.tipo2)) x(k, tipo)
  RETURNING id, codice_interno
)
SELECT id, upper(right(codice_interno, 1)) AS k FROM ins;

-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
CREATE TEMP TABLE _v ON COMMIT DROP AS
WITH ins AS (
  INSERT INTO documenti.template_documenti_versioni (
      template_documento_id, versione, stato, titolo, html_template,
      render_engine_id, versione_contesto)
  SELECT m.id, x.n, 'BOZZA', 'risoluzione ' || x.k || x.n, '<html>' || x.k || x.n || '</html>',
         (SELECT render FROM _k), 1
    FROM (VALUES ('M', 1), ('M', 2), ('B', 1), ('K', 1)) x(k, n)
    JOIN _m m ON m.k = x.k
  RETURNING id, template_documento_id, versione
)
SELECT i.id, m.k || i.versione AS kv FROM ins i JOIN _m m ON m.id = i.template_documento_id;

-- Dal verbo: M1 da dieci giorni fa, poi M2 da ieri (chiude M1), K1 da dieci giorni fa.
SELECT documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM _v WHERE kv = 'M1'), (SELECT oggi - 10 FROM _k), 1, NULL);
SELECT documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM _v WHERE kv = 'M2'), (SELECT oggi - 1 FROM _k), 1, NULL);
SELECT documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM _v WHERE kv = 'K1'), (SELECT oggi - 10 FROM _k), 1, NULL);

-- L'INSERT di una stampa del preventivo, dal modello e dalla versione indicati.
CREATE FUNCTION pg_temp.insert_stampa(p_modello text, p_versione text, p_progressivo integer)
RETURNS text LANGUAGE sql AS $f$
  SELECT format($i$
    INSERT INTO documenti.documenti_generati (
        tipo_documento_output_id, template_documento_id, template_versione_id,
        sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
        titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
        emittente_fiscale_id)
    SELECT k.tipo, (SELECT id FROM _m WHERE k = %L), (SELECT id FROM _v WHERE kv = %L), k.sorg,
           (SELECT preventivo_uid FROM _src), NULL, %s,
           'Stampa risoluzione', %L, '{"_meta": {"context_version": 1}}'::jsonb,
           repeat('1', 64), repeat('2', 64), repeat('3', 64), k.em
      FROM _k k$i$, p_modello, p_versione, p_progressivo, 'pgtap-ris-' || p_progressivo || '.pdf')
$f$;

-- ============================================================
-- La forma
-- ============================================================
-- 1
SELECT has_function('documenti', 'fn_template_motivo_non_stampabile', ARRAY['bigint', 'bigint'],
  '1) il building block del motivo esiste, con la versione facoltativa');

-- 2
SELECT has_view('documenti', 'vw_template_asset_utilizzabili',
  '2) la vista delle risorse utilizzabili esiste');

-- 3
SELECT ok(
  (SELECT 'security_invoker=true' = ANY (c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'documenti' AND c.relname = 'vw_template_asset_utilizzabili'),
  '3) ... e si legge coi privilegi di chi interroga');

-- ============================================================
-- Perche' un modello oggi non stampa
-- ============================================================
-- 4
SELECT is(documenti.fn_template_motivo_non_stampabile(-1),
  'MODELLO_INESISTENTE',
  '4) un modello che non esiste: MODELLO_INESISTENTE');

-- 5
SELECT is(documenti.fn_template_motivo_non_stampabile((SELECT id FROM _m WHERE k = 'B')),
  'NESSUNA_VERSIONE_VALIDA',
  '5) un modello con la sola bozza: NESSUNA_VERSIONE_VALIDA');

-- 6
SELECT is(documenti.fn_template_motivo_non_stampabile((SELECT id FROM _m WHERE k = 'M')),
  NULL,
  '6) il modello che stampa: NULL');

-- 7
SELECT is(documenti.fn_template_motivo_non_stampabile(
            (SELECT id FROM _m WHERE k = 'M'), (SELECT id FROM _v WHERE kv = 'M2')),
  NULL,
  '7) ... con la versione in uso: NULL');

-- 8
SELECT is(documenti.fn_template_motivo_non_stampabile(
            (SELECT id FROM _m WHERE k = 'M'), (SELECT id FROM _v WHERE kv = 'M1')),
  'VERSIONE_NON_IN_USO',
  '8) ... con la versione superata ieri: VERSIONE_NON_IN_USO');

-- ============================================================
-- La nascita della stampa
-- ============================================================
-- 9
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.insert_stampa('M', 'M1', 1)),
  'E_DOCUMENTI_GENERATO_COERENZA',
  '9) una stampa non nasce dalla versione superata');

-- 10
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.insert_stampa('B', 'B1', 1)),
  'E_DOCUMENTI_GENERATO_COERENZA',
  '10) ... ne'' da una bozza');

-- 11
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.insert_stampa('M', 'K1', 1)),
  'E_DOCUMENTI_GENERATO_COERENZA',
  '11) ... ne'' con la versione di un altro modello');

-- 12
CREATE TEMP TABLE _s ON COMMIT DROP AS
SELECT dbops.fn_pgtap_stampa_con_pdf(pg_temp.insert_stampa('M', 'M2', 1)) AS id;

SELECT is(
  (SELECT g.template_versione_id FROM documenti.documenti_generati g WHERE g.id = (SELECT id FROM _s)),
  (SELECT id FROM _v WHERE kv = 'M2'),
  '12) dalla versione in uso la stampa si registra');

-- ============================================================
-- Lo scarto
-- ============================================================
-- 13
SELECT is(
  (SELECT sc.stato FROM documenti.vw_template_personalizzati_scarto sc
    WHERE sc.template_documento_id = (SELECT id FROM _m WHERE k = 'K')),
  'STANDARD_NON_STAMPA',
  '13) una copia senza standard che stampa resta nello scarto: STANDARD_NON_STAMPA');

-- 14
SELECT is(
  (SELECT ROW(sc.standard_template_documento_id, sc.standard_versione_id, sc.standard_versione)::text
     FROM documenti.vw_template_personalizzati_scarto sc
    WHERE sc.template_documento_id = (SELECT id FROM _m WHERE k = 'K')),
  ROW(NULL::bigint, NULL::bigint, NULL::integer)::text,
  '14) ... senza standard di riferimento ne'' sua versione');

-- ============================================================
-- La risoluzione
-- ============================================================
-- 15: la frase si compone dalla sorgente (descrizione, o codice se manca).
SELECT throws_like(
  format('SELECT * FROM documenti.fn_risolvi_template_applicabile(%s, %s)',
         (SELECT sorg_vuota FROM _k), (SELECT em FROM _k)),
  (SELECT '%«' || coalesce(s.descrizione::text, s.codice_interno::text) || '»%'
     FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_ACQUISTO'),
  '15) senza tipo, su una sorgente senza modelli che stampano: la frase nomina la sorgente');

-- 16
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'SELECT * FROM documenti.fn_risolvi_template_applicabile(%s, %s)',
    (SELECT sorg_vuota FROM _k), (SELECT em FROM _k))),
  'E_DOCUMENTI_TEMPLATE_NON_RISOLTO',
  '16) ... ed e'' E_DOCUMENTI_TEMPLATE_NON_RISOLTO');

-- 17
SELECT is(
  documenti.fn_template_motivo_non_coerente(
    (SELECT id FROM _m WHERE k = 'M'), (SELECT sorg_vuota FROM _k), (SELECT em FROM _k), NULL),
  'SORGENTE',
  '17) il modello per un''altra sorgente: motivo SORGENTE');

-- 18
SELECT is(
  documenti.fn_template_motivo_non_coerente(
    (SELECT id FROM _m WHERE k = 'M'), (SELECT sorg FROM _k), (SELECT em FROM _k), (SELECT tipo2 FROM _k)),
  'TIPO',
  '18) il modello per un altro tipo: motivo TIPO');

-- 19: K senza versione accesa; la coppia (CONTRATTO, PREVENTIVO) resta nella
--     vista perche' ha un modello dell'azienda, in qualunque stato.
UPDATE documenti.template_documenti_versioni SET attivo = false WHERE id = (SELECT id FROM _v WHERE kv = 'K1');

SELECT is(
  (SELECT r.esito FROM documenti.vw_template_risoluzione_emittente r, _k k
    WHERE r.emittente_fiscale_id = k.em
      AND r.tipo_documento_output_id = k.tipo2
      AND r.sorgente_tipo_id = k.sorg),
  'NON_RISOLTO',
  '19) il solo modello proprio senza versione accesa, nessuno standard: la vista dice NON_RISOLTO');

-- 20
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'SELECT * FROM documenti.fn_risolvi_template_applicabile(%s, %s, %s)',
    (SELECT sorg FROM _k), (SELECT em FROM _k), (SELECT tipo2 FROM _k))),
  'E_DOCUMENTI_TEMPLATE_NON_RISOLTO',
  '20) ... e la stampa lo stesso, col suo codice');

-- ============================================================
-- Le risorse
-- ============================================================
CREATE TEMP TABLE _a ON COMMIT DROP AS
WITH ins AS (
  INSERT INTO documenti.template_asset (
      codice, codice_interno, descrizione, asset_tipo_id,
      mime_type, file_name, file_size_bytes, storage_key, sha256,
      emittente_fiscale_id, valido_dal, attivo)
  SELECT 'PGTAP-RIS-' || x.k, 'pgtap-ris-' || x.k, 'Risorsa della risoluzione ' || x.k, k.logo,
         'image/png', 'pgtap-ris-' || x.k || '.png', 1024, 'pgtap/ris/' || x.k,
         md5(x.k) || md5(x.k || 'x'), k.em, x.dal, x.attivo
    FROM _k k,
         LATERAL (VALUES ('ACCESA', k.oggi - 1, true),
                         ('SPENTA', k.oggi - 1, false),
                         ('FUTURA', k.oggi + 1, true)) x(k, dal, attivo)
  RETURNING id, codice
)
SELECT id, substr(codice, 11) AS k FROM ins;

-- 21
SELECT ok(
  EXISTS (SELECT 1 FROM documenti.vw_template_asset_utilizzabili u
           WHERE u.template_asset_id = (SELECT id FROM _a WHERE k = 'ACCESA')),
  '21) accesa e valida oggi: utilizzabile');

-- 22
SELECT ok(
  NOT EXISTS (SELECT 1 FROM documenti.vw_template_asset_utilizzabili u
               WHERE u.template_asset_id = (SELECT id FROM _a WHERE k = 'SPENTA')),
  '22) spenta: non utilizzabile');

-- 23
SELECT ok(
  NOT EXISTS (SELECT 1 FROM documenti.vw_template_asset_utilizzabili u
               WHERE u.template_asset_id = (SELECT id FROM _a WHERE k = 'FUTURA')),
  '23) valida da domani: non utilizzabile');

-- ============================================================
-- Il modello spento
-- ============================================================
-- Le versioni accese sono figlie vive: si spengono prima del modello.
UPDATE documenti.template_documenti_versioni SET attivo = false
 WHERE template_documento_id = (SELECT id FROM _m WHERE k = 'M');
UPDATE documenti.template_documenti SET attivo = false WHERE id = (SELECT id FROM _m WHERE k = 'M');

-- 24
SELECT is(documenti.fn_template_motivo_non_stampabile(
            (SELECT id FROM _m WHERE k = 'M'), (SELECT id FROM _v WHERE kv = 'M2')),
  'MODELLO_SPENTO',
  '24) il building block dice MODELLO_SPENTO');

-- 25
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'SELECT * FROM documenti.fn_risolvi_template_applicabile(%s, %s, %s, %s)',
    (SELECT sorg FROM _k), (SELECT em FROM _k), (SELECT tipo FROM _k), (SELECT id FROM _m WHERE k = 'M'))),
  'E_DOCUMENTI_TEMPLATE_NON_STAMPABILE',
  '25) la risoluzione col modello indicato lo rifiuta');

-- 26
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.insert_stampa('M', 'M2', 2)),
  'E_DOCUMENTI_GENERATO_COERENZA',
  '26) una stampa non nasce da un modello spento');

SELECT * FROM finish();
ROLLBACK;
