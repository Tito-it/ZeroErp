-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: sync automatico documenti_fatturazione_canali via trigger documento
-- ------------------------------------------------------------
-- Indice test (1..14):
-- 1) funzione trigger presente
-- 2) trigger su ordini presente
-- 3) trigger su ddt presente
-- 4) trigger su contratti presente
-- 5) prerequisiti minimi disponibili (incluso preventivi.uid)
-- 6) preventivo di test creato
-- 7) ordine da preventivo creato
-- 8) ordine apre canale ORDINE_VENDITA
-- 9) preventivo consumato verso ordine
-- 10) ddt da ordine creato
-- 11) ddt apre canale DDT_VENDITA
-- 12) ordine consumato verso ddt
-- 13) contratto di test creato
-- 14) contratto apre canale DIRETTO
-- 15) anti-regressione: rename codice sorgenti -> trigger apre comunque canale (risoluzione per codice_interno)
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

SELECT plan(15);

-- rev 2026-10-27 (lotto 4 di D7): niente piu' GUC fissata a mano. Prima
--   app.current_user_id si puntava sul primo utente di
--   config.user_emittenti_fiscali, scavalcando l'operatore del contesto; da
--   zero non c'era nessuno, su dev era un utente qualunque. L'emittente di
--   default dei documenti e' quello dell'operatore aperto da
--   fn_pgtap_set_contesto_operatore().

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_documenti_sync_canali'
  ),
  'funzione trigger presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'ordini'
      AND t.tgname = 'trg_ordini_z90_sync_canali_ins_upd'
      AND NOT t.tgisinternal
  ),
  'trigger su ordini presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'ddt'
      AND t.tgname = 'trg_ddt_z90_sync_canali_ins_upd'
      AND NOT t.tgisinternal
  ),
  'trigger su ddt presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'contratti'
      AND t.tgname = 'trg_contratti_z90_sync_canali_ins'
      AND NOT t.tgisinternal
  ),
  'trigger su contratti presente'
);

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba: BA legato all'azienda di chi agisce).
--   Prima BA, ruolo, istanza e utility si pescavano col primo id: da zero non
--   c'era niente. Le testate restano INSERT a mano: il trigger di sync che
--   scatta sull'INSERT e' il caso. Dal catalogo di seed restano sorgenti e
--   stati.
CREATE TEMP TABLE tmp_canali_sync_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('canali sync');

CREATE TEMP TABLE tmp_canali_sync_refs AS
SELECT
  (SELECT id FROM config.sorgenti WHERE codice = 'PREVENTIVO' AND attivo IS TRUE ORDER BY id LIMIT 1) AS src_preventivo_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'ORDINE_VENDITA' AND attivo IS TRUE ORDER BY id LIMIT 1) AS src_ordine_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'DDT_VENDITA' AND attivo IS TRUE ORDER BY id LIMIT 1) AS src_ddt_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'CONTRATTO' AND attivo IS TRUE ORDER BY id LIMIT 1) AS src_contratto_id,
  (SELECT id FROM config.stati_doc_preventivi WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS stato_preventivo_id,
  (SELECT id FROM config.stati_doc_ordini WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS stato_ordine_id,
  (SELECT id FROM config.stati_doc_ddt WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS stato_ddt_id,
  (SELECT id FROM config.stati_doc_contratti WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS stato_contratto_id,
  cli.billing_account_id,
  cli.soggetto_ruolo_id,
  cli.istanza_utility_id,
  cli.utility_id,
  ('PGTAP-' || substr(md5(clock_timestamp()::text), 1, 18))::text AS token
FROM tmp_canali_sync_cli cli;

SELECT ok(
  (
    SELECT src_preventivo_id IS NOT NULL
       AND src_ordine_id IS NOT NULL
       AND src_ddt_id IS NOT NULL
       AND src_contratto_id IS NOT NULL
       AND stato_preventivo_id IS NOT NULL
       AND stato_ordine_id IS NOT NULL
       AND stato_ddt_id IS NOT NULL
       AND stato_contratto_id IS NOT NULL
       AND billing_account_id IS NOT NULL
       AND soggetto_ruolo_id IS NOT NULL
       AND istanza_utility_id IS NOT NULL
       AND utility_id IS NOT NULL
       AND EXISTS (
         SELECT 1
         FROM information_schema.columns c
         WHERE c.table_schema = 'vendite'
           AND c.table_name = 'preventivi'
           AND c.column_name = 'uid'
       )
    FROM tmp_canali_sync_refs
  ),
  'prerequisiti minimi disponibili (incluso preventivi.uid)'
);

CREATE TEMP TABLE tmp_sync_preventivo AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero,
    rev,
    billing_account_id,
    istanza_utility_id,
    utility_id,
    stato_doc_preventivo_id
  )
  SELECT
    'PRE-' || token,
    0,
    billing_account_id,
    istanza_utility_id,
    utility_id,
    stato_preventivo_id
  FROM tmp_canali_sync_refs
  RETURNING id, uid
)
SELECT id, uid FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_sync_preventivo),
  'preventivo di test creato'
);

CREATE TEMP TABLE tmp_sync_ordine AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id,
    billing_account_id,
    stato_doc_ordine_id,
    sorgente_tipo_id,
    sorgente_uid
  )
  SELECT
    r.soggetto_ruolo_id,
    r.billing_account_id,
    r.stato_ordine_id,
    r.src_preventivo_id,
    p.uid
  FROM tmp_canali_sync_refs r
  CROSS JOIN tmp_sync_preventivo p
  RETURNING id, uid
)
SELECT id, uid FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_sync_ordine),
  'ordine da preventivo creato'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.documenti_fatturazione_canali c
    WHERE c.sorgente_tipo_id = (SELECT src_ordine_id FROM tmp_canali_sync_refs)
      AND c.sorgente_uid = (SELECT uid::text FROM tmp_sync_ordine)
      AND c.canale_codice = 'ORDINE_VENDITA'
      AND c.stato_canale = 'APERTO'
  ),
  'ordine apre canale ORDINE_VENDITA'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.documenti_fatturazione_canali c
    WHERE c.sorgente_tipo_id = (SELECT src_preventivo_id FROM tmp_canali_sync_refs)
      AND c.sorgente_uid = (SELECT uid::text FROM tmp_sync_preventivo)
      AND c.canale_codice = 'PREVENTIVO'
      AND c.stato_canale = 'CONSUMATO'
      AND c.target_sorgente_tipo_id = (SELECT src_ordine_id FROM tmp_canali_sync_refs)
      AND c.target_sorgente_uid = (SELECT uid::text FROM tmp_sync_ordine)
  ),
  'preventivo consumato verso ordine'
);

CREATE TEMP TABLE tmp_sync_ddt AS
WITH ins AS (
  INSERT INTO vendite.ddt (
    stato_doc_ddt_id,
    destinatario_soggetto_ruolo_id,
    sorgente_tipo_id,
    sorgente_uid
  )
  SELECT
    r.stato_ddt_id,
    r.soggetto_ruolo_id,
    r.src_ordine_id,
    o.uid
  FROM tmp_canali_sync_refs r
  CROSS JOIN tmp_sync_ordine o
  RETURNING id, uid
)
SELECT id, uid FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_sync_ddt),
  'ddt da ordine creato'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.documenti_fatturazione_canali c
    WHERE c.sorgente_tipo_id = (SELECT src_ddt_id FROM tmp_canali_sync_refs)
      AND c.sorgente_uid = (SELECT uid::text FROM tmp_sync_ddt)
      AND c.canale_codice = 'DDT_VENDITA'
      AND c.stato_canale = 'APERTO'
  ),
  'ddt apre canale DDT_VENDITA'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.documenti_fatturazione_canali c
    WHERE c.sorgente_tipo_id = (SELECT src_ordine_id FROM tmp_canali_sync_refs)
      AND c.sorgente_uid = (SELECT uid::text FROM tmp_sync_ordine)
      AND c.canale_codice = 'ORDINE_VENDITA'
      AND c.stato_canale = 'CONSUMATO'
      AND c.target_sorgente_tipo_id = (SELECT src_ddt_id FROM tmp_canali_sync_refs)
      AND c.target_sorgente_uid = (SELECT uid::text FROM tmp_sync_ddt)
  ),
  'ordine consumato verso ddt'
);

CREATE TEMP TABLE tmp_sync_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero,
    billing_account_id,
    istanza_utility_id,
    utility_id,
    stato_doc_contratto_id
  )
  SELECT
    'CTR-' || token,
    billing_account_id,
    istanza_utility_id,
    utility_id,
    stato_contratto_id
  FROM tmp_canali_sync_refs
  RETURNING id, uid
)
SELECT id, uid FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_sync_contratto),
  'contratto di test creato'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.documenti_fatturazione_canali c
    WHERE c.sorgente_tipo_id = (SELECT src_contratto_id FROM tmp_canali_sync_refs)
      AND c.sorgente_uid = (SELECT uid::text FROM tmp_sync_contratto)
      AND c.canale_codice = 'DIRETTO'
      AND c.stato_canale = 'APERTO'
  ),
  'contratto apre canale DIRETTO'
);

-- ============================================================
-- TEST 15) Anti-regressione codice_interno (analisi-hardcoded-codice §3a #13/#14):
--   dopo rename del `codice` (mutabile) delle 4 sorgenti, il trigger di sync
--   (write, file 20260628-18) e fn_set_documento_canale_stato (read, 20260628-19)
--   DEVONO continuare a risolverle per `codice_interno`: il canale si apre comunque.
-- ============================================================
UPDATE config.sorgenti
   SET codice = codice || '_RENAMED'
 WHERE codice_interno IN ('PREVENTIVO', 'ORDINE_VENDITA', 'DDT_VENDITA', 'CONTRATTO');

CREATE TEMP TABLE tmp_sync_prev_antireg AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero,
    rev,
    billing_account_id,
    istanza_utility_id,
    utility_id,
    stato_doc_preventivo_id
  )
  SELECT
    'PAR-' || token,
    0,
    billing_account_id,
    istanza_utility_id,
    utility_id,
    stato_preventivo_id
  FROM tmp_canali_sync_refs
  RETURNING id, uid
)
SELECT id, uid FROM ins;

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.documenti_fatturazione_canali c
    WHERE c.sorgente_tipo_id = (SELECT src_preventivo_id FROM tmp_canali_sync_refs)
      AND c.sorgente_uid = (SELECT uid::text FROM tmp_sync_prev_antireg)
      AND c.canale_codice = 'PREVENTIVO'
      AND c.stato_canale = 'APERTO'
  ),
  '15. anti-regressione: rename codice sorgenti -> il trigger apre comunque il canale PREVENTIVO (risoluzione per codice_interno)'
);

SELECT * FROM finish();
ROLLBACK;
