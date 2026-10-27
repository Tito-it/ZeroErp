-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: schema base commesse_* (changeset 20260224-05..09)
-- ------------------------------------------------------------
-- Indice test (1..17):
-- 1) Tabella vendite.commesse presente
-- 2) Tabella vendite.commesse_sorgenti presente
-- 3) Tabella vendite.commesse_attivita presente
-- 4) Tabella vendite.commesse_attivita_log presente
-- 5) Check tipo_commessa invalido su commesse (chk_commesse_tipo)
-- 6) Check ruolo_link invalido su commesse_sorgenti
-- 7) Vincolo una sola ROOT per commessa
-- 8) Unicita` (commessa_id, segment_key) su commesse_attivita
-- 9) Pair sorgente_tipo_id/sorgente_uid coerente su commesse_attivita
-- 10) pricing_mode invalido bloccato su commesse_attivita
-- 10-bis) riga NORMALE senza sorgente bloccata (vincolo 20261012-27, rev 2026-10-12)
-- 11) Colonna attivita_fatturabili.commessa_id presente
-- 12) Colonna attivita_fatturabili.commessa_attivita_id presente
-- 13) attivita_fatturabili.commessa_id NOT NULL
-- 14) attivita_fatturabili.commessa_attivita_id NOT NULL
-- 15) indice legacy uq_attivita_fatturabili_v_sorgente_fk rimosso
-- 16) indice uq_attivita_fatturabili_commessa_attivita presente
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

SELECT plan(17);

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'vendite' AND table_name = 'commesse'
  ),
  'Tabella vendite.commesse presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'vendite' AND table_name = 'commesse_sorgenti'
  ),
  'Tabella vendite.commesse_sorgenti presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'vendite' AND table_name = 'commesse_attivita'
  ),
  'Tabella vendite.commesse_attivita presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'vendite' AND table_name = 'commesse_attivita_log'
  ),
  'Tabella vendite.commesse_attivita_log presente'
);

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba), l'emittente e' quello dell'operatore
--   (script.fn_pgtap_emittente_sr_operatore) e l'articolo si costruisce
--   (dbops.fn_pgtap_crea_articolo): prima si pescavano con LIMIT 1, e su un
--   database ricostruito da zero non c'erano.
CREATE TEMP TABLE tmp_cli_cs AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('schema commesse');

CREATE TEMP TABLE tmp_refs_cs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_cs) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_cs) AS utility_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
  (SELECT istanza_utility_id FROM tmp_cli_cs) AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo(
    ('PGT-CS-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar, false
  ) AS articolo_id,
  (
    SELECT u.id
    FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id
    LIMIT 1
  ) AS uom_id,
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT v.id
    FROM config.valute v
    ORDER BY v.id
    LIMIT 1
  ) AS valuta_id,
  (
    -- Tipo COMMESSA (key_selector='id'): il guard sorgente (20260718-17/19)
    -- valida formato ed esistenza, quindi le sorgenti dei test sono le
    -- commesse REALI create qui sotto (chiave canonica id::text).
    SELECT s.id
    FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA'
      AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_tipo_id;

CREATE TEMP TABLE tmp_codes_cs AS
SELECT
  ('CMS_' || substr(md5(clock_timestamp()::text), 1, 12))::varchar(64) AS codice1,
  ('CMS_' || substr(md5((clock_timestamp() + interval '1 sec')::text), 1, 12))::varchar(64) AS codice2;

-- NOTA 2026-07-18: allineato allo schema corrente di vendite.commesse —
-- lo stato e' stato_commessa_id (FK, default 1), non piu' la colonna testuale
-- stato_commessa; il CHECK testato e' chk_commesse_tipo.
SELECT throws_ok(
  $$
  INSERT INTO vendite.commesse (
    codice, tipo_commessa, billing_account_id, utility_id, emittente_soggetto_ruolo_id
  )
  SELECT
    c.codice1, 'INVALIDO',
    r.billing_account_id, r.utility_id, r.emittente_soggetto_ruolo_id
  FROM tmp_codes_cs c CROSS JOIN tmp_refs_cs r;
  $$,
  '23514',
  NULL,
  'Check tipo_commessa invalido su commesse (chk_commesse_tipo)'
);

-- rev 2026-10-27 (lotto 4 di D7): le due commesse di fixture le apre il
--   builder (dbops.fn_pgtap_crea_commessa, dalla madre) sul cliente costruito,
--   non piu' un INSERT a mano coi riferimenti pescati.
CREATE TEMP TABLE tmp_commessa_cs AS
SELECT c.commessa_id AS id
FROM dbops.fn_pgtap_crea_commessa(
  'schema commesse 1', NULL, (SELECT billing_account_id FROM tmp_cli_cs)) c;

-- Seconda commessa: serve come sorgente REALE distinta per il test
-- "una sola ROOT" (il guard sorgente valida l'esistenza della chiave).
CREATE TEMP TABLE tmp_commessa_cs2 AS
SELECT c.commessa_id AS id
FROM dbops.fn_pgtap_crea_commessa(
  'schema commesse 2', NULL, (SELECT billing_account_id FROM tmp_cli_cs)) c;

SELECT throws_ok(
  $$
  INSERT INTO vendite.commesse_sorgenti (
    commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link
  )
  SELECT
    (SELECT id FROM tmp_commessa_cs), (SELECT sorgente_tipo_id FROM tmp_refs_cs),
    (SELECT id::text FROM tmp_commessa_cs), 'SECONDARIA';
  $$,
  '23514',
  NULL,
  'Check ruolo_link invalido su commesse_sorgenti'
);

INSERT INTO vendite.commesse_sorgenti (
  commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link
)
SELECT
  (SELECT id FROM tmp_commessa_cs), (SELECT sorgente_tipo_id FROM tmp_refs_cs),
  (SELECT id::text FROM tmp_commessa_cs), 'ROOT';

SELECT throws_ok(
  $$
  INSERT INTO vendite.commesse_sorgenti (
    commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link
  )
  SELECT
    (SELECT id FROM tmp_commessa_cs), (SELECT sorgente_tipo_id FROM tmp_refs_cs),
    (SELECT id::text FROM tmp_commessa_cs2), 'ROOT';
  $$,
  '23505',
  NULL,
  'Vincolo una sola ROOT per commessa'
);

CREATE TEMP TABLE tmp_attivita_commessa_cs AS
WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
    competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id,
    prezzo_snapshot, pricing_mode, stato_approvazione, stato_emissione,
    sorgente_tipo_id, sorgente_uid   -- la riga NORMALE ha la sua sorgente (vincolo 20261012-27)
  )
  SELECT
    (SELECT id FROM tmp_commessa_cs), 'SEG-001', r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
    date_trunc('month', script.fn_data_operativa())::date, script.fn_data_operativa(), script.fn_data_operativa(), r.tipo_doc_fiscale_id, r.valuta_id,
    1.2300000000, 'FIXED', 'BOZZA', 'NON_EMESSA',
    r.sorgente_tipo_id, (SELECT id FROM tmp_commessa_cs)::text
  FROM tmp_refs_cs r
  RETURNING id
)
SELECT id FROM ins;

SELECT throws_ok(
  $$
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
    competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id,
    prezzo_snapshot, pricing_mode, stato_approvazione, stato_emissione,
    sorgente_tipo_id, sorgente_uid   -- la riga NORMALE ha la sua sorgente (vincolo 20261012-27)
  )
  SELECT
    (SELECT id FROM tmp_commessa_cs), 'SEG-001', r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
    date_trunc('month', script.fn_data_operativa())::date, script.fn_data_operativa(), script.fn_data_operativa(), r.tipo_doc_fiscale_id, r.valuta_id,
    1.2300000000, 'FIXED', 'BOZZA', 'NON_EMESSA',
    r.sorgente_tipo_id, (SELECT id FROM tmp_commessa_cs)::text
  FROM tmp_refs_cs r;
  $$,
  '23505',
  NULL,
  'Unicita` (commessa_id, segment_key) su commesse_attivita'
);

SELECT throws_ok(
  $$
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
    competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id,
    prezzo_snapshot, pricing_mode, stato_approvazione, stato_emissione,
    sorgente_tipo_id, sorgente_uid
  )
  SELECT
    (SELECT id FROM tmp_commessa_cs), 'SEG-PAIR-001', r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
    date_trunc('month', script.fn_data_operativa())::date, script.fn_data_operativa(), script.fn_data_operativa(), r.tipo_doc_fiscale_id, r.valuta_id,
    1.2300000000, 'FIXED', 'BOZZA', 'NON_EMESSA',
    r.sorgente_tipo_id, NULL
  FROM tmp_refs_cs r;
  $$,
  '23514',
  NULL,
  'Pair sorgente_tipo_id/sorgente_uid coerente su commesse_attivita'
);

SELECT throws_ok(
  $$
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
    competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id,
    prezzo_snapshot, pricing_mode, stato_approvazione, stato_emissione,
    sorgente_tipo_id, sorgente_uid   -- la riga NORMALE ha la sua sorgente (vincolo 20261012-27)
  )
  SELECT
    (SELECT id FROM tmp_commessa_cs), 'SEG-MODE-001', r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
    date_trunc('month', script.fn_data_operativa())::date, script.fn_data_operativa(), script.fn_data_operativa(), r.tipo_doc_fiscale_id, r.valuta_id,
    1.2300000000, 'DYNAMIC', 'BOZZA', 'NON_EMESSA',
    r.sorgente_tipo_id, (SELECT id FROM tmp_commessa_cs)::text
  FROM tmp_refs_cs r;
  $$,
  '23514',
  NULL,
  'pricing_mode invalido bloccato su commesse_attivita'
);

-- Una riga senza documento d'origine e' un ONERE o una RETTIFICA: una NORMALE
-- senza sorgente si rifiuta (vincolo 20261012-27,
-- brief-db-annullo-a-valle-riapre-a-monte §8.5).
SELECT throws_like(
  $$
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
    competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id,
    prezzo_snapshot, pricing_mode, stato_approvazione, stato_emissione
  )
  SELECT
    (SELECT id FROM tmp_commessa_cs), 'SEG-SENZA-SORGENTE-001', r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
    date_trunc('month', script.fn_data_operativa())::date, script.fn_data_operativa(), script.fn_data_operativa(), r.tipo_doc_fiscale_id, r.valuta_id,
    1.2300000000, 'FIXED', 'BOZZA', 'NON_EMESSA'
  FROM tmp_refs_cs r;
  $$,
  '%chk_commesse_attivita_senza_sorgente_onere_rettifica%',
  'riga NORMALE senza sorgente bloccata su commesse_attivita (solo ONERE e RETTIFICA nascono senza)'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'commessa_id'
  ),
  'Colonna attivita_fatturabili.commessa_id presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'commessa_attivita_id'
  ),
  'Colonna attivita_fatturabili.commessa_attivita_id presente'
);



SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'commessa_id'
      AND c.is_nullable = 'NO'
  ),
  'attivita_fatturabili.commessa_id NOT NULL'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'commessa_attivita_id'
      AND c.is_nullable = 'NO'
  ),
  'attivita_fatturabili.commessa_attivita_id NOT NULL'
);

SELECT ok(
  to_regclass('vendite.uq_attivita_fatturabili_v_sorgente_fk') IS NULL,
  'indice legacy uq_attivita_fatturabili_v_sorgente_fk rimosso'
);

SELECT ok(
  to_regclass('vendite.uq_attivita_fatturabili_commessa_attivita') IS NOT NULL,
  'indice uq_attivita_fatturabili_commessa_attivita presente'
);

SELECT * FROM finish();
ROLLBACK;
