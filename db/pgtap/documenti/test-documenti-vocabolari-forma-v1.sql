-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i vocabolari di documenti hanno una forma sola, si leggono soltanto,
--   e ogni tipo dichiara i formati di file che ammette.
-- Oggetti:
--   documenti.tipi_documento_output, .tipi_file_documento, .tipi_asset_documento,
--   .render_engine_documento, .formati_template, .formati_pagina,
--   .orientamenti_pagina; config.formati_file;
--   documenti.tipi_asset_documento_formati, .tipi_file_documento_formati;
--   documenti.trgfn_guard_formato_ammesso.
--
-- Elenco test (plan 20):
--   La forma
--   1) gli otto vocabolari hanno le colonne della forma unica, ne' una di piu'
--      ne' una di meno (i formati di file in piu' MIME ed estensione)
--   2) descrizione ed etichetta_key sono obbligatorie in tutti
--   3) ogni etichetta_key e' <schema>.<tabella>.<codice_interno minuscolo>
--   4) i quattro vocabolari storici non hanno storico
--   5) nessun trigger ATTIVO li nomina
--   6) il tipo di risorsa ALTRO non c'e' piu'
--   7) le eccezioni ATTIVO verso i tipi di documento e di file sono uscite
--   I formati che ogni tipo ammette
--   8) LOGO e IMMAGINE: PNG, JPEG, SVG, WEBP, GIF
--   9) FIRMA: PNG, JPEG, SVG, WEBP
--  10) PDF_FINALE: PDF; ALLEGATO: PDF, JPEG, PNG
--  11) ogni tipo di risorsa e di file ammette almeno un formato
--   La sola lettura
--  12) all'applicazione solo SELECT, sulle dieci tabelle
--  13) come applicazione, una scrittura sui formati risponde 42501
--   Il controllo del formato
--  14) una firma in GIF non nasce: E_DOCUMENTI_FORMATO_NON_AMMESSO
--  15) ... e la frase dice file, formato e tipo
--  16) un logo in GIF nasce, anche col tipo MIME scritto in maiuscolo
--  17) cambiare il tipo del logo in FIRMA, che il GIF non lo ammette, e' rifiutato
--  18) cambiare il formato di una risorsa: parla prima l'immutabilita' del file
--  19) un allegato GIF di una stampa non nasce
--  20) un allegato PNG nasce
--
-- Scopo:
--  - ⭐ i casi sono COSTRUITI: un'azienda nuova, un suo preventivo, un modello
--    con la versione pubblicata, una stampa col suo PDF, le risorse. Dal DB si
--    legge solo il catalogo di seed, che e' il contratto (80_data).
--  - 8-10 sono le liste che il backend teneva in codice il 2026-11-16: il giro
--    sposta la sede, non le regole.
--  - 12 e' la terza sede della postura (linee-guida-sql §11.8): il forward
--    90_end/20261115-98, il loop 90_end/ci_apply/20260205-41 e il provisioning
--    devono dire la stessa cosa, e su un database ricostruito da zero lo dice
--    solo questo test.
--  - ⚠️ 5 chiede che i trigger ATTIVO dei quattro siano tolti: li toglie
--    00_schema/documenti/20261115-91, e da zero il motore non li genera.
-- ------------------------------------------------------------

BEGIN;

-- Un'azienda nuova, senza modelli e senza risorse sue.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;

CREATE TEMP TABLE _src ON COMMIT DROP AS
SELECT p.preventivo_uid FROM dbops.fn_pgtap_crea_preventivo('vocabolari forma', 'DRAFT') p;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);

-- ============================================================
-- La forma
-- ============================================================
CREATE TEMP TABLE _voc (rel regclass, extra text[]) ON COMMIT DROP;
INSERT INTO _voc VALUES
  ('documenti.tipi_documento_output',   ARRAY[]::text[]),
  ('documenti.tipi_file_documento',     ARRAY[]::text[]),
  ('documenti.tipi_asset_documento',    ARRAY[]::text[]),
  ('documenti.render_engine_documento', ARRAY[]::text[]),
  ('documenti.formati_template',        ARRAY[]::text[]),
  ('documenti.formati_pagina',          ARRAY[]::text[]),
  ('documenti.orientamenti_pagina',     ARRAY[]::text[]),
  ('config.formati_file',               ARRAY['mime_type', 'estensione']);

-- 1
SELECT is(
  (SELECT string_agg(v.rel::text, ', ' ORDER BY v.rel::text)
     FROM _voc v
    WHERE (SELECT array_agg(a.attname::text ORDER BY a.attname)
             FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = v.rel AND a.attnum > 0 AND NOT a.attisdropped)
          IS DISTINCT FROM
          (SELECT array_agg(c ORDER BY c)
             FROM unnest(ARRAY['id', 'codice_interno', 'codice', 'descrizione',
                               'etichetta_key', 'ordine', 'data_insert', 'user_insert',
                               'data_update', 'user_update', 'tx_id'] || v.extra) c)),
  NULL,
  '1) gli otto vocabolari hanno le colonne della forma unica');

-- 2
SELECT is(
  (SELECT string_agg(v.rel::text || '.' || a.attname, ', ' ORDER BY 1)
     FROM _voc v
     JOIN pg_catalog.pg_attribute a ON a.attrelid = v.rel
    WHERE a.attname IN ('descrizione', 'etichetta_key') AND NOT a.attnotnull),
  NULL,
  '2) descrizione ed etichetta_key sono obbligatorie in tutti');

-- 3
CREATE FUNCTION pg_temp.etichette_fuori_forma(p_rel regclass)
RETURNS bigint LANGUAGE plpgsql AS $f$
DECLARE v_n bigint;
BEGIN
  EXECUTE format(
    'SELECT count(*) FROM %s t WHERE t.etichetta_key IS DISTINCT FROM %L || lower(t.codice_interno)',
    p_rel,
    -- schema e nome da pg_class: il testo di un regclass dipende dal search_path
    (SELECT n.nspname || '.' || c.relname || '.'
       FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
      WHERE c.oid = p_rel))
  INTO v_n;
  RETURN v_n;
END $f$;

SELECT is(
  (SELECT sum(pg_temp.etichette_fuori_forma(v.rel))::int FROM _voc v),
  0,
  '3) ogni etichetta_key e'' <schema>.<tabella>.<codice_interno minuscolo>');

-- 4
SELECT is(
  (SELECT count(*)::int
     FROM unnest(ARRAY['storico.tipi_documento_output', 'storico.tipi_file_documento',
                       'storico.tipi_asset_documento', 'storico.render_engine_documento']) s
    WHERE to_regclass(s) IS NOT NULL),
  0,
  '4) i quattro vocabolari storici non hanno storico');

-- 5
SELECT is(
  (SELECT count(*)::int
     FROM pg_catalog.pg_trigger t
    WHERE NOT t.tgisinternal
      AND t.tgfoid IN ('dbops.trgfn_prevent_deactivate_if_children'::regproc,
                       'dbops.trgfn_child_requires_active_parent'::regproc)
      AND (t.tgrelid IN (SELECT rel FROM _voc)
           -- il require del figlio: secondo argomento, la tabella del padre
           OR (dbops.fn_trigger_argomenti(t.tgargs))[2]
                IN ('tipi_documento_output', 'tipi_file_documento',
                    'tipi_asset_documento', 'render_engine_documento'))),
  0,
  '5) nessun trigger ATTIVO nomina i vocabolari');

-- 6
SELECT is(
  (SELECT count(*)::int FROM documenti.tipi_asset_documento WHERE codice_interno = 'ALTRO'),
  0,
  '6) il tipo di risorsa ALTRO non c''e'' piu''');

-- 7
SELECT is(
  (SELECT count(*)::int
     FROM dbops.automazione_attivo_eccezioni e
    WHERE (e.schema_figlia, e.tabella_figlia, e.colonna_fk) IN (
              ('vendite',   'fatture_stampa_coda',     'tipo_documento_output_id'),
              ('documenti', 'documenti_generati',      'tipo_documento_output_id'),
              ('documenti', 'documenti_generati_file', 'file_tipo_id'))),
  0,
  '7) le eccezioni ATTIVO verso tipi di documento e di file sono uscite');

-- ============================================================
-- I formati che ogni tipo ammette
-- ============================================================
CREATE FUNCTION pg_temp.formati_asset(p_tipo text)
RETURNS text LANGUAGE sql AS $f$
  SELECT string_agg(ff.codice_interno, ',' ORDER BY ff.codice_interno)
    FROM documenti.tipi_asset_documento_formati af
    JOIN documenti.tipi_asset_documento t ON t.id = af.asset_tipo_id
    JOIN config.formati_file ff ON ff.id = af.formato_file_id
   WHERE t.codice_interno = p_tipo
$f$;
CREATE FUNCTION pg_temp.formati_file(p_tipo text)
RETURNS text LANGUAGE sql AS $f$
  SELECT string_agg(ff.codice_interno, ',' ORDER BY ff.codice_interno)
    FROM documenti.tipi_file_documento_formati tf
    JOIN documenti.tipi_file_documento t ON t.id = tf.file_tipo_id
    JOIN config.formati_file ff ON ff.id = tf.formato_file_id
   WHERE t.codice_interno = p_tipo
$f$;

-- 8
SELECT is(
  pg_temp.formati_asset('LOGO') || ' | ' || pg_temp.formati_asset('IMMAGINE'),
  'GIF,JPEG,PNG,SVG,WEBP | GIF,JPEG,PNG,SVG,WEBP',
  '8) LOGO e IMMAGINE: PNG, JPEG, SVG, WEBP, GIF');

-- 9
SELECT is(
  pg_temp.formati_asset('FIRMA'),
  'JPEG,PNG,SVG,WEBP',
  '9) FIRMA: PNG, JPEG, SVG, WEBP');

-- 10
SELECT is(
  pg_temp.formati_file('PDF_FINALE') || ' | ' || pg_temp.formati_file('ALLEGATO'),
  'PDF | JPEG,PDF,PNG',
  '10) PDF_FINALE: PDF; ALLEGATO: PDF, JPEG, PNG');

-- 11
SELECT is(
  (SELECT count(*)::int FROM documenti.tipi_asset_documento t
    WHERE NOT EXISTS (SELECT 1 FROM documenti.tipi_asset_documento_formati af
                       WHERE af.asset_tipo_id = t.id))
  + (SELECT count(*)::int FROM documenti.tipi_file_documento t
      WHERE NOT EXISTS (SELECT 1 FROM documenti.tipi_file_documento_formati tf
                         WHERE tf.file_tipo_id = t.id)),
  0,
  '11) ogni tipo di risorsa e di file ammette almeno un formato');

-- ============================================================
-- La sola lettura
-- ============================================================
-- 12
SELECT is(
  (SELECT string_agg(t || ':' || p, ', ' ORDER BY t, p)
     FROM unnest(ARRAY[
            'documenti.tipi_documento_output', 'documenti.tipi_file_documento',
            'documenti.tipi_asset_documento', 'documenti.render_engine_documento',
            'documenti.formati_template', 'documenti.formati_pagina',
            'documenti.orientamenti_pagina', 'config.formati_file',
            'documenti.tipi_asset_documento_formati',
            'documenti.tipi_file_documento_formati']) t,
          unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']) p
    WHERE has_table_privilege('zeroerp_app', t, p) IS DISTINCT FROM (p = 'SELECT')),
  NULL,
  '12) all''applicazione solo SELECT, sulle dieci tabelle');

-- 13
SELECT throws_ok(
  $$UPDATE config.formati_file SET id = id WHERE false$$,
  '42501',
  NULL,
  '13) come applicazione, una scrittura sui formati risponde 42501');

-- ============================================================
-- Il controllo del formato
-- ============================================================
CREATE FUNCTION pg_temp.insert_asset(p_codice text, p_tipo text, p_mime text, p_file text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format($i$
    INSERT INTO documenti.template_asset (
        codice, codice_interno, descrizione, asset_tipo_id,
        mime_type, file_name, file_size_bytes, storage_key, sha256,
        emittente_fiscale_id, attivo)
    SELECT %L, %L, 'Risorsa del test dei formati',
           (SELECT t.id FROM documenti.tipi_asset_documento t WHERE t.codice_interno = %L),
           %L, %L, 1024, 'pgtap/formati/' || %L, md5(%L) || md5(%L),
           (SELECT emittente_fiscale_id FROM _e), true$i$,
    p_codice, p_codice, p_tipo, p_mime, p_file, p_file, p_codice, p_file)
$f$;

-- 14
SELECT is(
  dbops.fn_pgtap_codice_errore(pg_temp.insert_asset('PGTAP-FIRMA-GIF', 'FIRMA', 'image/gif', 'firma.gif')),
  'E_DOCUMENTI_FORMATO_NON_AMMESSO',
  '14) una firma in GIF non nasce');

-- 15
SELECT throws_like(
  pg_temp.insert_asset('PGTAP-FIRMA-GIF', 'FIRMA', 'image/gif', 'firma.gif'),
  '%Il file firma.gif non si carica: il formato image/gif non e'' ammesso per il tipo FIRMA%',
  '15) ... e la frase dice file, formato e tipo');

-- 16
SELECT lives_ok(
  pg_temp.insert_asset('PGTAP-LOGO-GIF', 'LOGO', 'IMAGE/GIF', 'logo.gif'),
  '16) un logo in GIF nasce, anche col tipo MIME scritto in maiuscolo');

-- 17
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE documenti.template_asset SET asset_tipo_id = %s WHERE codice = %L',
    (SELECT t.id FROM documenti.tipi_asset_documento t WHERE t.codice_interno = 'FIRMA'),
    'PGTAP-LOGO-GIF')),
  'E_DOCUMENTI_FORMATO_NON_AMMESSO',
  '17) cambiare il tipo del logo in FIRMA, che il GIF non lo ammette, e'' rifiutato');

-- 18
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE documenti.template_asset SET mime_type = %L WHERE codice = %L',
    'text/css', 'PGTAP-LOGO-GIF')),
  'E_DOCUMENTI_ASSET_FILE_IMMUTABILE',
  '18) cambiare il formato di una risorsa: parla prima l''immutabilita'' del file');

-- La stampa a cui si allegano i file: modello, versione, stampa col suo PDF.
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                   AS sorg,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO')    AS tipo,
  (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT') AS render,
  (SELECT f.id FROM documenti.tipi_file_documento f WHERE f.codice_interno = 'ALLEGATO')       AS allegato,
  (SELECT emittente_fiscale_id FROM _e)                                                        AS em;

CREATE TEMP TABLE _m ON COMMIT DROP AS
WITH t AS (
  INSERT INTO documenti.template_documenti (
      tipo_documento_output_id, codice, codice_interno, descrizione,
      sorgente_tipo_id, context_builder_code, emittente_fiscale_id, is_default, attivo)
  SELECT tipo, 'PGTAP-FORMATI', 'pgtap-formati', 'Modello del test dei formati', sorg,
         'PREVENTIVO', em, true, true
    FROM _k
  RETURNING id
)
SELECT id FROM t;

CREATE TEMP TABLE _v ON COMMIT DROP AS
WITH v AS (
  INSERT INTO documenti.template_documenti_versioni (
      template_documento_id, versione, stato, titolo, html_template,
      render_engine_id, valido_dal, valido_al, versione_contesto)
  SELECT (SELECT id FROM _m), 1, 'BOZZA', 'formati v1', '<html>formati</html>',
         render, DATE '2026-01-01', NULL, 1
    FROM _k
  RETURNING id
)
SELECT id FROM v;

-- ⚠️ Una versione nasce in bozza ed esce dalla bozza solo dal verbo della
--   pubblicazione (guard dello stato, 20261116-02): la fixture lo percorre.
SELECT documenti.fn_pubblica_template_documento_versione((SELECT id FROM _v), DATE '2026-01-01', 1, NULL);

CREATE TEMP TABLE _s ON COMMIT DROP AS
SELECT dbops.fn_pgtap_stampa_con_pdf(format($i$
    INSERT INTO documenti.documenti_generati (
        tipo_documento_output_id, template_documento_id, template_versione_id,
        sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
        titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
        emittente_fiscale_id)
    SELECT k.tipo, (SELECT id FROM _m), (SELECT id FROM _v), k.sorg,
           (SELECT preventivo_uid FROM _src), NULL, 1,
           'Stampa dei formati', 'pgtap-formati.pdf', '{"_meta": {"context_version": 1}}'::jsonb,
           repeat('1', 64), repeat('2', 64), repeat('3', 64), k.em
      FROM _k k$i$)) AS id;

CREATE FUNCTION pg_temp.insert_allegato(p_mime text, p_file text, p_ordinamento integer)
RETURNS text LANGUAGE sql AS $f$
  SELECT format($i$
    INSERT INTO documenti.documenti_generati_file (
        documento_generato_id, file_tipo_id, mime_type, file_name,
        file_size_bytes, storage_key, sha256, ordinamento, is_principale)
    SELECT (SELECT id FROM _s), (SELECT allegato FROM _k), %L, %L,
           2048, 'pgtap/formati/' || %L, md5(%L) || md5(%L), %s, false$i$,
    p_mime, p_file, p_file, p_file, p_file, p_ordinamento)
$f$;

-- 19
SELECT is(
  dbops.fn_pgtap_codice_errore(pg_temp.insert_allegato('image/gif', 'allegato.gif', 2)),
  'E_DOCUMENTI_FORMATO_NON_AMMESSO',
  '19) un allegato GIF di una stampa non nasce');

-- 20
SELECT lives_ok(
  pg_temp.insert_allegato('image/png', 'allegato.png', 2),
  '20) un allegato PNG nasce');

SELECT * FROM finish();
ROLLBACK;
