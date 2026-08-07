-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: colonna prezzo_bloccato su vendite.attivita_fatturabili (changeset 20260224-04)
-- ------------------------------------------------------------
-- Indice test (1..4):
-- 1) Colonna prezzo_bloccato presente
-- 2) Colonna prezzo_bloccato NOT NULL
-- 3) Default prezzo_bloccato = false
-- 4) Inserimento base valorizza prezzo_bloccato=false di default
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

SELECT plan(4);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'prezzo_bloccato'
  ),
  'Colonna prezzo_bloccato presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'prezzo_bloccato'
      AND c.is_nullable = 'NO'
  ),
  'Colonna prezzo_bloccato NOT NULL'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'prezzo_bloccato'
      AND c.column_default ILIKE '%false%'
  ),
  'Default prezzo_bloccato = false'
);

CREATE TEMP TABLE tmp_refs_apb AS
SELECT
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.istanza_utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS istanza_utility_id,
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
  ) AS valuta_id;

CREATE TEMP TABLE tmp_ins_apb AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id,
    istanza_utility_id,
    billing_account_id,
    data_attivita,
    quantita,
    competenza_mese,
    tipo_doc_fiscale_id,
    valuta_id,
    meta
  )
  SELECT
    r.articolo_id,
    r.istanza_utility_id,
    r.billing_account_id,
    current_date,
    1,
    date_trunc('month', current_date)::date,
    r.tipo_doc_fiscale_id,
    r.valuta_id,
    jsonb_build_object('test_scope', 'pgtap_attivita_prezzo_bloccato')
  FROM tmp_refs_apb r
  RETURNING prezzo_bloccato
)
SELECT * FROM ins;

SELECT is(
  (SELECT prezzo_bloccato FROM tmp_ins_apb),
  false,
  'Inserimento base valorizza prezzo_bloccato=false di default'
);

SELECT * FROM finish();
ROLLBACK;
