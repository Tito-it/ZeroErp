-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.template_asset
--   - lo stesso file una volta sola per azienda (uq_template_asset_emittente_sha256)
--   - una risorsa non si cancella
--   - il file non cambia (protect_file), il codice interno nemmeno (lock di colonna)
--   - i campi liberi: codice, descrizione, date, attivo, meta
-- ------------------------------------------------------------
-- Indice test (1..17):
--  1) Setup: una risorsa nasce con l'azienda della sessione
--  2) Stessa azienda, stessa impronta: uq_template_asset_emittente_sha256
--  3) Stessa impronta per un'altra azienda: ammessa
--  4) Stessa azienda, stesso codice interno: uq_template_asset_emittente_codice_interno
--  5) DELETE di una risorsa: E_DOCUMENTI_ASSET_DELETE_BLOCKED
--  6-10) storage_key, sha256, file_size_bytes, mime_type, file_name non cambiano:
--        E_DOCUMENTI_ASSET_FILE_IMMUTABILE
-- 11) codice_interno non cambia: E_CODICE_NON_MODIFICABILE
-- 12) meta e' libero
-- 13) codice e' libero, e si salva in maiuscolo
-- 14) descrizione e' libera
-- 15) le date sono libere: valido_al si chiude
-- 16) attivo e' libero: la risorsa si spegne
-- 17) ... e una risorsa spenta il file non lo cambia lo stesso
-- ⚠️ Le due aziende si costruiscono (dbops.fn_pgtap_crea_emittente_operatore):
--    il caso «un'altra azienda» non si pesca fra quelle che ci sono.
-- ⚠️ Il cambio del tipo MIME lo giudicherebbe anche il guard del formato
--    (a10_tipo_ammette_formato), che viene dopo protect_file (a10_protect_file):
--    parla protect_file, ed e' il codice atteso.
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

-- Due aziende nuove, ciascuna col suo operatore.
CREATE TEMP TABLE _e  ON COMMIT DROP AS SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
CREATE TEMP TABLE _e2 ON COMMIT DROP AS SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- Contesto applicativo: questo test gira come gira l'applicazione, con
-- l'operatore della prima azienda in sessione.
DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;

SELECT plan(17);

-- ============================================================
-- Setup: la risorsa di base, con l'azienda della sessione
--   (script.trgfn_default_emittente_fiscale riempie emittente_fiscale_id)
-- ============================================================
CREATE TEMP TABLE tmp_ta_ctx ON COMMIT DROP AS
SELECT (SELECT t.id FROM documenti.tipi_asset_documento t
         WHERE t.codice_interno = 'LOGO') AS tipo_logo_id;

WITH ins AS (
  INSERT INTO documenti.template_asset (
    codice, codice_interno, descrizione, asset_tipo_id,
    mime_type, file_name, file_size_bytes, storage_key, sha256, attivo
  )
  SELECT 'PGTAP-ASSET-1', 'PGTAP_ASSET_1', 'Logo test',
         tipo_logo_id, 'image/png', 'logo.png', 1024,
         's3://bucket/pgtap/logo.png', repeat('a', 64), true
    FROM tmp_ta_ctx
  RETURNING id, emittente_fiscale_id
)
SELECT id, emittente_fiscale_id INTO TEMP TABLE tmp_ta_asset FROM ins;

-- 1) Pre-condizione
SELECT is(
  (SELECT emittente_fiscale_id FROM tmp_ta_asset),
  (SELECT emittente_fiscale_id FROM _e),
  '1) la risorsa nasce con l''azienda della sessione'
);

-- ============================================================
-- 2-4) Le unicita' per azienda
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$INSERT INTO documenti.template_asset (
      codice, codice_interno, descrizione, asset_tipo_id,
      mime_type, file_name, file_size_bytes, storage_key, sha256, attivo
    )
    SELECT 'PGTAP-ASSET-1-BIS', 'PGTAP_ASSET_1_BIS', 'stesso file',
           tipo_logo_id, 'image/png', 'logo2.png', 2048,
           's3://bucket/pgtap/logo2.png', repeat('a', 64), true
      FROM tmp_ta_ctx$$),
  'uq_template_asset_emittente_sha256',
  '2) stessa azienda, stessa impronta: uq_template_asset_emittente_sha256'
);

SELECT is(
  dbops.fn_pgtap_codice_errore(format($q$INSERT INTO documenti.template_asset (
      codice, codice_interno, descrizione, asset_tipo_id,
      mime_type, file_name, file_size_bytes, storage_key, sha256,
      emittente_fiscale_id, attivo
    )
    SELECT 'PGTAP-ASSET-EM2', 'PGTAP_ASSET_EM2', 'Logo dell''altra azienda',
           tipo_logo_id, 'image/png', 'logo.png', 1024,
           's3://bucket/em2/logo.png', repeat('a', 64), %s, true
      FROM tmp_ta_ctx$q$, (SELECT emittente_fiscale_id FROM _e2))),
  NULL,
  '3) la stessa impronta per un''altra azienda e'' ammessa'
);

SELECT is(
  dbops.fn_pgtap_codice_errore($$INSERT INTO documenti.template_asset (
      codice, codice_interno, descrizione, asset_tipo_id,
      mime_type, file_name, file_size_bytes, storage_key, sha256, attivo
    )
    SELECT 'PGTAP-ASSET-1-TER', 'PGTAP_ASSET_1', 'stesso codice interno',
           tipo_logo_id, 'image/png', 'logo3.png', 3072,
           's3://bucket/pgtap/logo3.png', repeat('c', 64), true
      FROM tmp_ta_ctx$$),
  'uq_template_asset_emittente_codice_interno',
  '4) stessa azienda, stesso codice interno: uq_template_asset_emittente_codice_interno'
);

-- ============================================================
-- 5) Una risorsa non si cancella
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore($$DELETE FROM documenti.template_asset
     WHERE id = (SELECT id FROM tmp_ta_asset)$$),
  'E_DOCUMENTI_ASSET_DELETE_BLOCKED',
  '5) una risorsa non si cancella: E_DOCUMENTI_ASSET_DELETE_BLOCKED'
);

-- ============================================================
-- 6-10) Il file non cambia
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE documenti.template_asset SET %s WHERE id = %s',
    c.set_clause, (SELECT id FROM tmp_ta_asset))),
  'E_DOCUMENTI_ASSET_FILE_IMMUTABILE',
  c.n || ') ' || c.colonna || ' non cambia: E_DOCUMENTI_ASSET_FILE_IMMUTABILE')
  FROM (VALUES
    (6,  'storage_key',     'storage_key = ''s3://hack/logo.png'''),
    (7,  'sha256',          'sha256 = repeat(''b'', 64)'),
    (8,  'file_size_bytes', 'file_size_bytes = file_size_bytes + 1'),
    (9,  'mime_type',       'mime_type = ''image/jpeg'''),
    (10, 'file_name',       'file_name = ''logo-nuovo.png''')
  ) AS c(n, colonna, set_clause)
 ORDER BY c.n;

-- 11) Il codice interno non cambia
SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.template_asset
       SET codice_interno = 'PGTAP_ASSET_ALTRO'
     WHERE id = (SELECT id FROM tmp_ta_asset)$$),
  'E_CODICE_NON_MODIFICABILE',
  '11) codice_interno non cambia: E_CODICE_NON_MODIFICABILE'
);

-- ============================================================
-- 12-16) I campi liberi
-- ============================================================
UPDATE documenti.template_asset
   SET meta = '{"asset_test": "ok"}'::jsonb
 WHERE id = (SELECT id FROM tmp_ta_asset);

SELECT is(
  (SELECT meta->>'asset_test' FROM documenti.template_asset
    WHERE id = (SELECT id FROM tmp_ta_asset)),
  'ok',
  '12) meta e'' libero'
);

UPDATE documenti.template_asset
   SET codice = 'pgtap-asset-nuovo'
 WHERE id = (SELECT id FROM tmp_ta_asset);

SELECT is(
  (SELECT codice::text FROM documenti.template_asset
    WHERE id = (SELECT id FROM tmp_ta_asset)),
  'PGTAP-ASSET-NUOVO',
  '13) codice e'' libero, e si salva in maiuscolo'
);

UPDATE documenti.template_asset
   SET descrizione = 'Logo rinominato'
 WHERE id = (SELECT id FROM tmp_ta_asset);

SELECT is(
  (SELECT descrizione FROM documenti.template_asset
    WHERE id = (SELECT id FROM tmp_ta_asset)),
  'Logo rinominato',
  '14) descrizione e'' libera'
);

UPDATE documenti.template_asset
   SET valido_al = script.fn_data_operativa() + 30
 WHERE id = (SELECT id FROM tmp_ta_asset);

SELECT is(
  (SELECT valido_al FROM documenti.template_asset
    WHERE id = (SELECT id FROM tmp_ta_asset)),
  script.fn_data_operativa() + 30,
  '15) le date sono libere: valido_al si chiude'
);

UPDATE documenti.template_asset
   SET attivo = false
 WHERE id = (SELECT id FROM tmp_ta_asset);

SELECT is(
  (SELECT attivo FROM documenti.template_asset
    WHERE id = (SELECT id FROM tmp_ta_asset)),
  false,
  '16) attivo e'' libero: la risorsa si spegne'
);

SELECT is(
  dbops.fn_pgtap_codice_errore($$UPDATE documenti.template_asset
       SET storage_key = 's3://hack/logo-spento.png'
     WHERE id = (SELECT id FROM tmp_ta_asset)$$),
  'E_DOCUMENTI_ASSET_FILE_IMMUTABILE',
  '17) spenta, la risorsa non cambia file lo stesso'
);

SELECT * FROM finish();
ROLLBACK;
