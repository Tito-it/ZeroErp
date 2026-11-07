-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.documenti_generati_eventi
--   - INSERT eventi ammessi (GENERATO/SCARICATO/STORAGE_ORPHAN/RISTAMPA_FEDELE)
--   - CHECK evento_tipo (set chiuso v1: ANTEPRIMA, RENDER_KO rifiutati)
--   - CHECK esito (OK/KO/WARN)
--   - CHECK messaggio non-vuoto / detail jsonb object
--   - guard append-only: block UPDATE / block DELETE
--   - FK documento_generato_id (asserita dal CATALOGO: da quando la tabella e'
--     in RLS il perimetro rifiuta prima della foreign key — vedi test 12 e 16)
--   - storico OFF (no provisioning automatico)
--   - default audit popolati su INSERT minimo
-- ------------------------------------------------------------
-- Indice test (1..16):
--  1) Setup: documento generato di riferimento creato
--  2) INSERT evento GENERATO esito=OK passa
--  3) INSERT evento SCARICATO con messaggio passa
--  4) INSERT evento STORAGE_ORPHAN user_id=NULL esito=KO passa
--  5) CHECK evento_tipo: ANTEPRIMA non ammesso in v1 (Decisione 30)
--  6) CHECK evento_tipo: RENDER_KO non ammesso (set chiuso)
--  7) CHECK esito: valore non in (OK,KO,WARN) rifiutato
--  8) CHECK messaggio: stringa solo whitespace rifiutata
--  9) CHECK detail: jsonb non-object (array) rifiutato
-- 10) Guard block UPDATE: UPDATE messaggio bloccato
-- 11) Guard block DELETE: DELETE evento bloccato
-- 12) FK: documento_generato_id dichiarata a catalogo verso documenti_generati
-- 13) Storico OFF: storico.documenti_generati_eventi NON esiste
-- 14) Default audit: data_insert e user_insert popolati su INSERT minimo
-- 15) CHECK evento_tipo: RISTAMPA_FEDELE ammesso, con esito WARN
-- 16) RLS: un documento fuori perimetro e' rifiutato PRIMA della FK -> 42501
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

-- ⭐ La stampa e' di un preventivo VERO, del mondo dell'operatore in sessione: dal
--   lotto D di brief-db-sorgente-documento-e-riga il guard unico verifica che il
--   documento stampato esista, e la chiave di un preventivo e' il suo uid.
CREATE TEMP TABLE _dg_src AS
SELECT p.preventivo_uid FROM dbops.fn_pgtap_crea_preventivo('dg eventi', 'DRAFT') p;


SELECT plan(16);

-- ============================================================
-- Setup contesto: emittente + template + versione + documento generato
-- ============================================================
CREATE TEMP TABLE tmp_dge_ctx AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo = true ORDER BY ef.id LIMIT 1)               AS emittente_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO')                       AS sorgente_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'PREVENTIVO')                       AS tipo_output_id,
  (SELECT r.id FROM documenti.render_engine_documento r
    WHERE r.codice_interno = 'WEASYPRINT')                       AS render_id;

WITH ins_t AS (
  INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
    is_default, attivo
  )
  SELECT tipo_output_id, 'PGTAP-DGE', 'PGTAP_DGE', 'Template per eventi',
         sorgente_id, 'pgtap.builder', emittente_id, false, true
    FROM tmp_dge_ctx
   WHERE emittente_id IS NOT NULL
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dge_template FROM ins_t;

WITH ins_v AS (
  INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto
  )
  SELECT (SELECT id FROM tmp_dge_template),
         1, 'PUBBLICATA', 'v1', '<html>v1</html>',
         (SELECT render_id FROM tmp_dge_ctx),
         DATE '2026-01-01', DATE '2026-12-31', 1
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dge_versione FROM ins_v;

WITH ins_dg AS (
  INSERT INTO documenti.documenti_generati (
    tipo_documento_output_id, template_documento_id, template_versione_id,
    sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
    titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
    emittente_fiscale_id
  )
  SELECT
    (SELECT tipo_output_id FROM tmp_dge_ctx),
    (SELECT id FROM tmp_dge_template),
    (SELECT id FROM tmp_dge_versione),
    (SELECT sorgente_id FROM tmp_dge_ctx),
    (SELECT preventivo_uid FROM _dg_src), NULL, 1,
    'Doc per eventi', 'doc-evt.pdf',
    '{"tot": 100, "_meta": {"context_version": 1}}'::jsonb,
    repeat('1', 64), repeat('2', 64), repeat('3', 64),
    (SELECT emittente_id FROM tmp_dge_ctx)
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dge_doc FROM ins_dg;

-- 1) Pre-condizione setup
SELECT ok(
  (SELECT COUNT(*) FROM tmp_dge_doc) = 1,
  'Setup: documento generato di riferimento creato'
);

-- ============================================================
-- 2) INSERT evento GENERATO esito=OK
-- ============================================================
INSERT INTO documenti.documenti_generati_eventi (
  documento_generato_id, evento_tipo, esito, detail
)
SELECT (SELECT id FROM tmp_dge_doc), 'GENERATO', 'OK',
       jsonb_build_object('size_bytes', 1024);

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'GENERATO'),
  1,
  'INSERT evento GENERATO esito=OK passa'
);

-- ============================================================
-- 3) INSERT evento SCARICATO con messaggio
-- ============================================================
INSERT INTO documenti.documenti_generati_eventi (
  documento_generato_id, evento_tipo, esito, messaggio
)
SELECT (SELECT id FROM tmp_dge_doc), 'SCARICATO', 'OK',
       'Download da utente API';

SELECT is(
  (SELECT messaggio FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'SCARICATO'),
  'Download da utente API',
  'INSERT evento SCARICATO con messaggio passa'
);

-- ============================================================
-- 4) INSERT evento STORAGE_ORPHAN user_id NULL esito=KO
-- ============================================================
INSERT INTO documenti.documenti_generati_eventi (
  documento_generato_id, evento_tipo, esito, user_id, messaggio, detail
)
SELECT (SELECT id FROM tmp_dge_doc), 'STORAGE_ORPHAN', 'KO',
       NULL, 'File orfano post-fail commit',
       jsonb_build_object('storage_key', 's3://bucket/orphan.pdf');

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'STORAGE_ORPHAN'
      AND esito = 'KO'
      AND user_id IS NULL),
  1,
  'INSERT evento STORAGE_ORPHAN user_id=NULL esito=KO passa'
);

-- ============================================================
-- 5) CHECK evento_tipo: ANTEPRIMA non ammesso (Decisione 30)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'ANTEPRIMA', 'OK'$$,
  '23514',
  NULL,
  'CHECK evento_tipo: ANTEPRIMA non ammesso in v1'
);

-- ============================================================
-- 6) CHECK evento_tipo: RENDER_KO non ammesso
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'RENDER_KO', 'KO'$$,
  '23514',
  NULL,
  'CHECK evento_tipo: RENDER_KO non ammesso (set chiuso v1)'
);

-- ============================================================
-- 7) CHECK esito: valore non in (OK,KO,WARN)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'GENERATO', 'INVALID'$$,
  '23514',
  NULL,
  'CHECK esito: valore non in (OK,KO,WARN) rifiutato'
);

-- ============================================================
-- 8) CHECK messaggio: stringa solo whitespace
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito, messaggio
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'GENERATO', 'OK', '   '$$,
  '23514',
  NULL,
  'CHECK messaggio: stringa solo whitespace rifiutata'
);

-- ============================================================
-- 9) CHECK detail: jsonb non-object (array)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito, detail
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'GENERATO', 'OK', '[]'::jsonb$$,
  '23514',
  NULL,
  'CHECK detail: jsonb non-object (array) rifiutato'
);

-- ============================================================
-- 10) Guard block UPDATE: UPDATE messaggio bloccato
-- ============================================================
SELECT throws_ok(
  $$UPDATE documenti.documenti_generati_eventi
       SET messaggio = 'modificato'
     WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
       AND evento_tipo = 'SCARICATO'$$,
  NULL,
  NULL,
  'Guard block UPDATE: UPDATE messaggio bloccato'
);

-- ============================================================
-- 11) Guard block DELETE: DELETE evento bloccato
-- ============================================================
SELECT throws_ok(
  $$DELETE FROM documenti.documenti_generati_eventi
     WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
       AND evento_tipo = 'GENERATO'$$,
  NULL,
  NULL,
  'Guard block DELETE: DELETE evento bloccato'
);

-- ============================================================
-- 12) FK documento_generato_id -> documenti_generati
--
-- ⛔ SI ASSERISCE DAL CATALOGO, e non provando a violarla. Fino al
--   2026-09-10 questo test faceva un INSERT con `documento_generato_id =
--   999999999` e pretendeva `23503`. Da quando la tabella e' in RLS
--   (slice 20260910-31..34) quell'INSERT prende **42501**: la `WITH CHECK`
--   risale a un documento che non esiste, l'adattatore risponde `false`, e
--   il perimetro parla PRIMA che la foreign key possa dire la sua.
--
-- ⭐ E' la forma nota del guard che oscura il vincolo, in versione row level
--   security — e non e' riparabile costruendo il caso: **un id inesistente e'
--   fuori dal perimetro di chiunque**, per definizione. Non esiste un contesto
--   in cui la FK torni a parlare, salvo girare come owner, che vorrebbe dire
--   non esercitare nessuna policy.
--
-- ⇒ La copertura si spezza in due: qui la FK si asserisce dove e' **scritta**
--   (il catalogo, che non dipende dal ruolo di chi guarda), e il comportamento
--   che l'applicazione vede davvero diventa il test 16.
-- ============================================================
SELECT is(
  (SELECT c.confrelid::regclass::text
     FROM pg_constraint c
    WHERE c.conrelid = 'documenti.documenti_generati_eventi'::regclass
      AND c.contype  = 'f'
      AND c.conkey   = ARRAY[(SELECT a.attnum FROM pg_attribute a
                               WHERE a.attrelid = 'documenti.documenti_generati_eventi'::regclass
                                 AND a.attname  = 'documento_generato_id')]::smallint[]),
  'documenti.documenti_generati',
  'FK: documento_generato_id dichiarata a catalogo verso documenti_generati'
);

-- ============================================================
-- 13) Storico OFF: storico.documenti_generati_eventi NON esiste
-- ============================================================
SELECT is(
  to_regclass('storico.documenti_generati_eventi'),
  NULL,
  'Storico OFF: storico.documenti_generati_eventi non provisionato'
);

-- ============================================================
-- 14) Default audit popolati su INSERT minimo
-- ============================================================
SELECT ok(
  (SELECT data_insert IS NOT NULL AND user_insert IS NOT NULL
     FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'GENERATO'),
  'Default audit: data_insert e user_insert popolati su INSERT minimo'
);

-- ============================================================
-- 15) RISTAMPA_FEDELE ammesso, con esito WARN
--
-- La ristampa fedele ri-produce un documento dallo snapshot congelato e NON
-- crea righe in `documenti_generati`: l'evento e' la sua UNICA scrittura
-- (20260803-04). Va presidiato che il valore sia ammesso, altrimenti il CHECK
-- lo rifiuta e il servizio si limita a loggare — un rosso che si vede solo nei
-- log, cioe' uno che si smette di guardare.
--
-- `WARN` e' il caso normale, non l'eccezione: significa «fedele nel contenuto,
-- non nei byte» (decisione Tid, brief ristampa fedele §8.2) e capita ogni volta
-- che il motore di render cambia fra l'emissione e la ristampa.
-- ============================================================
INSERT INTO documenti.documenti_generati_eventi (
  documento_generato_id, evento_tipo, esito, messaggio, detail
)
SELECT (SELECT id FROM tmp_dge_doc), 'RISTAMPA_FEDELE', 'WARN',
       'Ristampa fedele: contenuto identico, byte diversi',
       jsonb_build_object('pdf_hash_match', false);

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'RISTAMPA_FEDELE'
      AND esito = 'WARN'
      AND (detail->>'pdf_hash_match')::boolean IS FALSE),
  1,
  'CHECK evento_tipo: RISTAMPA_FEDELE ammesso, con esito WARN'
);

-- ============================================================
-- 16) RLS: un documento fuori perimetro e' rifiutato PRIMA della FK
--
-- ⭐ E' la meta' comportamentale di cio' che il test 12 asseriva prima della
--   slice 20260910-31..34: l'INSERT viene rifiutato, ma il codice che
--   l'applicazione legge e' quello del PERIMETRO, non quello della foreign key.
--   Scriverlo qui e' il modo di non perdere la copertura fingendo che il
--   comportamento non sia cambiato.
--
-- ⚠️ Lo SQLSTATE e' esplicito: `throws_ok` senza discriminante accetterebbe
--   QUALUNQUE errore — compreso il 23503 di prima, cioe' proprio la cosa che
--   questo test deve distinguere.
--
-- ⛔ E il verso positivo che lo tiene onesto e' gia' nel file: i test 2, 3 e 4
--   inseriscono sul documento del setup e PASSANO. Senza di loro un `42501` su
--   tutto sarebbe indistinguibile da una policy rotta che chiude ogni cosa.
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito
    )
    VALUES (999999999, 'GENERATO', 'OK')$$,
  '42501',
  NULL,
  'RLS: un documento fuori perimetro e'' rifiutato prima della FK -> 42501'
);

SELECT * FROM finish();
ROLLBACK;
