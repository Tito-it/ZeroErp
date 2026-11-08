-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il DOCUMENTO GENERATO (documenti.documenti_generati) e la CODA DI
--   STAMPA (vendite.fatture_stampa_coda) nella grammatica del modello. La chiave
--   del documento stampato sta in sorgente_id (tipi a chiave id) o in
--   sorgente_uid uuid (tipi a chiave uid), una serie sola di versioni per
--   documento, il guard unico la valida e blocca la cancellazione del documento
--   stampato. La coda tiene la fattura nella sola sorgente_id, FK vera.
-- ChangeSet: 20261108-14 … -21
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto D, giro D.1 (S-4, S-6, S-9, D-3, V-6)
-- ------------------------------------------------------------
-- Indice test (plan 18):
--   LA FORMA
--    1) sorgente_id bigint, sorgente_uid uuid, entrambe NULL ammesse
--    2) CHECK di forma e unicita' delle versioni sulla chiave nuova (NULLS NOT DISTINCT)
--    3) guard unico (DOCUMENTO, BLOCCA); perimetro UNICO; il guard testuale non c'e'
--   LE STAMPE
--    4) la stampa di un preventivo (chiave uid): passa
--    5) la stampa di un ordine (chiave id): passa
--    6) la seconda stampa dello stesso documento con lo stesso numero: 23505 (V-6)
--    7) ... e con il numero dopo: passa
--   IL GUARD UNICO
--    8) l'id in sorgente_id per il preventivo (chiave uid): E_SORG_CHIAVE_NON_CONFORME
--    9) un preventivo che non c'e': E_SORG_NOT_FOUND
--   10) tutte e due le chiavi: E_SORG_CHIAVE_NON_CONFORME (il guard parla prima del CHECK)
--   LO SNAPSHOT
--   11) la stampa spostata su un altro preventivo: E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE
--   12) lo stato si cambia ancora
--   LA CANCELLAZIONE (BLOCCA)
--   13) il preventivo stampato non si cancella: E_SORG_ORIGINE_REFERENZIATA
--   14) ... e l'ordine stampato nemmeno
--   GLI ORFANI
--   15) il presidio degli orfani non vede le stampe del test
--   LA CODA DI STAMPA
--   16) sorgente_uid non c'e' piu', ne' nella tabella ne' nel presidio
--   17) esente dal solo guard unico, col motivo (la FK vera)
--   18) fn_accoda_stampe_lotto non nomina la colonna ritirata
--
-- ⚠️ Il mondo si COSTRUISCE: due preventivi e un ordine dai builder
--   dbops.fn_pgtap_*, con il contesto aperto (un'azienda, un emittente). I modelli
--   di stampa sono del test, dell'emittente del mondo. Gira come l'applicazione
--   (operatore in sessione, RLS attiva).
-- rev 2026-11-08 (brief-db-sorgente-documento-e-riga lotto P, giro P.1): le sorelle vecchie si cercano per nome da pg_proc (la _testuale e' ritirata).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

-- L'esito di un'istruzione: PASSA, il codice d'errore applicativo (dal
-- CONSTRAINT dell'errore di fn_log_and_raise_error), o SQLSTATE + vincolo.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT is(
  (SELECT string_agg(a.attname || ':' || format_type(a.atttypid, a.atttypmod) || ':' || a.attnotnull, '|' ORDER BY a.attname)
     FROM pg_attribute a
    WHERE a.attrelid = 'documenti.documenti_generati'::regclass
      AND a.attname IN ('sorgente_id', 'sorgente_uid')),
  'sorgente_id:bigint:false|sorgente_uid:uuid:false',
  '1) la chiave del documento stampato sta in due colonne tipizzate, una delle due NULL');

SELECT is(
  (SELECT string_agg(k.conname || '=' || pg_get_constraintdef(k.oid), ' | ' ORDER BY k.conname)
     FROM pg_constraint k
    WHERE k.conrelid = 'documenti.documenti_generati'::regclass
      AND k.conname IN ('chk_documenti_generati_sorgente_forma', 'uq_documenti_generati_sorgente_progressivo',
                        'chk_documenti_generati_sorgente_uid_non_vuoto')),
  'chk_documenti_generati_sorgente_forma=CHECK ((num_nonnulls(sorgente_id, sorgente_uid) = 1)) | '
  'uq_documenti_generati_sorgente_progressivo=UNIQUE NULLS NOT DISTINCT (sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, progressivo_sorgente)',
  '2) CHECK di forma e unicita'' delle versioni sulla chiave nuova, NULLS NOT DISTINCT; il CHECK del testo non c''e''');

-- ⚠️ Schema e nome da pg_class + pg_namespace, non da regclass::text: il testo
--   di un regclass dipende dal search_path di chi guarda.
SELECT is(
  (SELECT concat_ws('|',
      (SELECT m.livello_minimo || '/' || m.azione_cancellazione
         FROM script.fn_sorgente_guard_montaggi() m
        WHERE m.schema_tabella = 'documenti' AND m.nome_tabella = 'documenti_generati'),
      (SELECT count(*) FROM pg_trigger t
        WHERE t.tgrelid = 'documenti.documenti_generati'::regclass
          -- Per nome da pg_proc, non ::regproc: un cast sul nome di una funzione
          -- ritirata (la _testuale, giro P.1) e' un errore, non uno zero.
          AND t.tgfoid IN (SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                            WHERE n.nspname = 'script'
                              AND p.proname IN ('trgfn_guard_sorgente_polimorfa_testuale',
                                                'trgfn_guard_sorgente_polimorfa_tipizzata'))),
      (SELECT p.grammatica || '/' || coalesce(p.orfani_esclusi_perche, 'nessuna esenzione')
         FROM dbops.fn_sorgenti_orfane_perimetro() p
        WHERE p.schema_tabella = 'documenti' AND p.nome_tabella = 'documenti_generati'))),
  'DOCUMENTO/BLOCCA|0|UNICO/nessuna esenzione',
  '3) guard unico (DOCUMENTO, BLOCCA), nessuna delle sorelle vecchie; la tabella sta nel perimetro degli orfani');

-- ============================================================
-- Fixture: due preventivi e un ordine del mondo, un modello di stampa per
--   tipo, dell'emittente del mondo
-- ============================================================
CREATE TEMP TABLE _pv AS
SELECT v.k, p.*
  FROM (VALUES ('A'), ('B')) v(k),
       LATERAL dbops.fn_pgtap_crea_preventivo('dg sorgente ' || v.k, 'DRAFT') p;

CREATE TEMP TABLE _or AS
SELECT o.* FROM dbops.fn_pgtap_crea_ordine('dg sorgente ordine', 'DRAFT',
                                           (SELECT billing_account_id FROM _pv WHERE k = 'A')) o;

CREATE TEMP TABLE _tpl AS
WITH t AS (
  INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id, is_default, attivo)
  SELECT o.id, 'PGTAP-DGS-' || s.codice_interno, 'pgtap_dgs_' || lower(s.codice_interno),
         'Modello del test della provenienza', s.id, 'pgtap.builder',
         (SELECT emittente_fiscale_id FROM _pv WHERE k = 'A'), false, true
    FROM (VALUES ('PREVENTIVO', 'PREVENTIVO'), ('ORDINE_VENDITA', 'ORDINE_VENDITA')) v(sorgente, output)
    JOIN config.sorgenti s ON s.codice_interno = v.sorgente
    JOIN documenti.tipi_documento_output o ON o.codice_interno = v.output
  RETURNING id, tipo_documento_output_id, sorgente_tipo_id
), tv AS (
  INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
  SELECT t.id, 1, 'PUBBLICATA', 'v1', '<html>v1</html>',
         (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT'),
         DATE '2026-01-01', DATE '2099-12-31', 1
    FROM t
  RETURNING id, template_documento_id
)
SELECT s.codice_interno AS sorgente, t.id AS template_id, tv.id AS versione_id,
       t.tipo_documento_output_id AS tipo_output_id, t.sorgente_tipo_id
  FROM t JOIN tv ON tv.template_documento_id = t.id
  JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id;

-- La stampa di un documento: le colonne dello snapshot dal modello del tipo,
-- la chiave e il numero dal test. Ritorna l'istruzione, per pg_temp.esito.
CREATE FUNCTION pg_temp.stampa(p_sorgente text, p_id bigint, p_uid uuid, p_progressivo integer)
RETURNS text LANGUAGE sql AS $f$
  SELECT format(
    'INSERT INTO documenti.documenti_generati (
        tipo_documento_output_id, template_documento_id, template_versione_id,
        sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
        titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
        emittente_fiscale_id)
     SELECT t.tipo_output_id, t.template_id, t.versione_id,
            t.sorgente_tipo_id, %s, %s, NULL, %s,
            ''Stampa pgTAP'', ''pgtap-dgs.pdf'', ''{"_meta": {"context_version": 1}}''::jsonb,
            repeat(''1'', 64), repeat(''2'', 64), repeat(''3'', 64),
            (SELECT emittente_fiscale_id FROM _pv WHERE k = ''A'')
       FROM _tpl t WHERE t.sorgente = %L',
    coalesce(p_id::text, 'NULL'), coalesce(quote_literal(p_uid::text) || '::uuid', 'NULL'),
    p_progressivo, p_sorgente)
$f$;

-- ============================================================
-- LE STAMPE
-- ============================================================
SELECT is(pg_temp.esito(pg_temp.stampa('PREVENTIVO', NULL, (SELECT preventivo_uid FROM _pv WHERE k = 'A'), 1)),
  'PASSA',
  '4) la stampa di un preventivo, chiave uid in sorgente_uid: passa');

SELECT is(pg_temp.esito(pg_temp.stampa('ORDINE_VENDITA', (SELECT ordine_id FROM _or), NULL, 1)),
  'PASSA',
  '5) la stampa di un ordine, chiave id in sorgente_id: passa');

SELECT is(pg_temp.esito(pg_temp.stampa('PREVENTIVO', NULL, (SELECT preventivo_uid FROM _pv WHERE k = 'A'), 1)),
  '23505 uq_documenti_generati_sorgente_progressivo',
  '6) una seconda versione del preventivo col numero gia'' usato: una serie sola per documento (V-6)');

SELECT is(pg_temp.esito(pg_temp.stampa('PREVENTIVO', NULL, (SELECT preventivo_uid FROM _pv WHERE k = 'A'), 2)),
  'PASSA',
  '7) ... e col numero dopo: passa');

-- ============================================================
-- IL GUARD UNICO
-- ============================================================
SELECT is(pg_temp.esito(pg_temp.stampa('PREVENTIVO', (SELECT preventivo_id FROM _pv WHERE k = 'A'), NULL, 3)),
  'E_SORG_CHIAVE_NON_CONFORME',
  '8) l''id in sorgente_id per il preventivo, che ha chiave uid: E_SORG_CHIAVE_NON_CONFORME');

SELECT is(pg_temp.esito(pg_temp.stampa('PREVENTIVO', NULL, gen_random_uuid(), 1)),
  'E_SORG_NOT_FOUND',
  '9) un preventivo che non c''e'': E_SORG_NOT_FOUND');

SELECT is(pg_temp.esito(pg_temp.stampa('PREVENTIVO', (SELECT preventivo_id FROM _pv WHERE k = 'A'),
                                       (SELECT preventivo_uid FROM _pv WHERE k = 'A'), 3)),
  'E_SORG_CHIAVE_NON_CONFORME',
  '10) tutte e due le chiavi: E_SORG_CHIAVE_NON_CONFORME, il guard parla prima del CHECK');

-- ============================================================
-- LO SNAPSHOT
-- ============================================================
-- ⭐ Il preventivo B esiste: il guard unico passa, e a parlare e' lo snapshot.
SELECT is(pg_temp.esito(format(
    'UPDATE documenti.documenti_generati SET sorgente_uid = %L::uuid
      WHERE sorgente_uid = %L::uuid AND progressivo_sorgente = 1',
    (SELECT preventivo_uid FROM _pv WHERE k = 'B'), (SELECT preventivo_uid FROM _pv WHERE k = 'A'))),
  'E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE',
  '11) la stampa spostata su un altro preventivo: lo snapshot non cambia');

SELECT is(pg_temp.esito(format(
    'UPDATE documenti.documenti_generati SET stato = ''ARCHIVIATO''
      WHERE sorgente_uid = %L::uuid AND progressivo_sorgente = 2',
    (SELECT preventivo_uid FROM _pv WHERE k = 'A'))),
  'PASSA',
  '12) lo stato fuori dallo snapshot si cambia ancora');

-- ============================================================
-- LA CANCELLAZIONE (BLOCCA)
-- ============================================================
SELECT is(pg_temp.esito(format('DELETE FROM vendite.preventivi WHERE id = %s',
                               (SELECT preventivo_id FROM _pv WHERE k = 'A'))),
  'E_SORG_ORIGINE_REFERENZIATA',
  '13) il preventivo stampato non si cancella: la stampa e'' append-only, quindi BLOCCA');

SELECT is(pg_temp.esito(format('DELETE FROM vendite.ordini WHERE id = %s', (SELECT ordine_id FROM _or))),
  'E_SORG_ORIGINE_REFERENZIATA',
  '14) ... e l''ordine stampato nemmeno');

-- ============================================================
-- GLI ORFANI
-- ============================================================
SELECT is_empty(
  $$SELECT 1 FROM dbops.vw_sorgenti_orfane o
     WHERE o.tabella = 'documenti.documenti_generati'::regclass$$,
  '15) il presidio degli orfani non vede le stampe del test');

-- ============================================================
-- LA CODA DI STAMPA
-- ============================================================
SELECT is(
  (SELECT concat_ws('|',
      (SELECT count(*) FROM pg_attribute a
        WHERE a.attrelid = 'vendite.fatture_stampa_coda'::regclass
          AND a.attname = 'sorgente_uid' AND NOT a.attisdropped),
      (SELECT count(*) FROM pg_attribute a
        WHERE a.attrelid = 'dbops.vw_fatture_stampa_coda_da_guardare'::regclass
          AND a.attname = 'sorgente_uid'),
      (SELECT array_to_string(c.reloptions, ',') FROM pg_class c
        WHERE c.oid = 'dbops.vw_fatture_stampa_coda_da_guardare'::regclass))),
  '0|0|security_invoker=true',
  '16) sorgente_uid non c''e'' piu'', ne'' nella coda ne'' nel suo presidio, che resta security_invoker');

SELECT is(
  (SELECT p.grammatica || '/' || coalesce(p.orfani_esclusi_perche, 'orfani guardati') || '/'
          || (p.guard_esente_perche ~ 'FK vera')::text
     FROM dbops.fn_sorgenti_orfane_perimetro() p
    WHERE p.schema_tabella = 'vendite' AND p.nome_tabella = 'fatture_stampa_coda'),
  'TESTUALE/orfani guardati/true',
  '17) la coda e'' esente dal solo guard unico, col motivo: la sua chiave e'' una FK vera');

SELECT ok(
  (SELECT p.prosrc !~ 'sorgente_uid' FROM pg_proc p
    WHERE p.oid = 'vendite.fn_accoda_stampe_lotto(bigint, bigint)'::regprocedure),
  '18) fn_accoda_stampe_lotto non nomina la colonna ritirata');

SELECT * FROM finish();
ROLLBACK;
