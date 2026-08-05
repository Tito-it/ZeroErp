-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: selezione attivita_fatturabili per pipeline DRAFT
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento attivita_fatturabili di test
-- 3) Selezione + lock ritorna 1 riga
-- 4) Lock attivato sulla riga
-- 5) Lock_batch_id valorizzato
-- 6) Cleanup completato
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_fd AS
SELECT
  'pgtap_fatturazione_draft'::text AS test_scope,
  uuidv7() AS lock_batch_id,
  uuidv7() AS sorgente_uid;

CREATE TEMP TABLE tmp_refs_fd AS
SELECT
  (SELECT id
     FROM catalogo.articoli
    WHERE attivo IS TRUE
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS articolo_id,
  (SELECT id
     FROM anagrafiche.istanze_utilities
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS istanza_utility_id,
  (SELECT id
     FROM anagrafiche.billing_account
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS billing_account_id,
  (SELECT utility_id
     FROM anagrafiche.billing_account
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS utility_id,
  (SELECT id
     FROM config.sorgenti
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1) AS sorgente_tipo_id,
  (SELECT id
     FROM catalogo.unita_misura
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1) AS uom_id,
  (SELECT id
     FROM config.tipi_doc_fiscale
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id
     FROM config.valute
    ORDER BY id
    LIMIT 1) AS valuta_id;

SELECT ok(
  (SELECT articolo_id IS NOT NULL
     AND istanza_utility_id IS NOT NULL
     AND billing_account_id IS NOT NULL
     AND sorgente_tipo_id IS NOT NULL
     AND tipo_doc_fiscale_id IS NOT NULL
     AND valuta_id IS NOT NULL
   FROM tmp_refs_fd),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- 1) Inserimento attivita_fatturabili di test
-- ============================================================
CREATE TEMP TABLE tmp_attivita_fd AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id,
    istanza_utility_id,
    billing_account_id,
    data_attivita,
    competenza_mese,
    quantita,
    approvato,
    fatturato,
    sospesa,
    tipo_doc_fiscale_id,
    valuta_id,
    sorgente_tipo_id,
    sorgente_uid,
    sorgente_riga,
    meta
  )
  SELECT
    r.articolo_id,
    r.istanza_utility_id,
    r.billing_account_id,
    current_date,
    date_trunc('month', current_date)::date,
    1,
    true,
    false,
    false,
    r.tipo_doc_fiscale_id,
    r.valuta_id,
    NULL,
    NULL,
    NULL,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_fd))
  FROM tmp_refs_fd r
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_attivita_fd),
  'Inserimento attivita_fatturabili di test'
);

-- ============================================================
-- 2) Selezione + lock
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM vendite.fn_select_attivita_fatturabili(
      p_competenza_mese => date_trunc('month', current_date)::date,
      p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_fd),
      p_lock_batch_id => (SELECT lock_batch_id FROM tmp_costanti_fd),
      p_lock => true,
      p_data_fatturazione => current_date,
      p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_fd),
      p_utility_id => (SELECT utility_id FROM tmp_refs_fd),
      p_valuta_id => (SELECT valuta_id FROM tmp_refs_fd),
      p_emittente_soggetto_ruolo_id => NULL,
      p_area_geografica_id => NULL,
      p_limit => 10
    )
  ),
  1,
  'Selezione + lock ritorna 1 riga'
);

SELECT is(
  (
    SELECT lock_in_fatturazione
    FROM vendite.attivita_fatturabili
    WHERE id = (SELECT id FROM tmp_attivita_fd)
  ),
  true,
  'Lock attivato sulla riga'
);

SELECT is(
  (
    SELECT lock_batch_id
    FROM vendite.attivita_fatturabili
    WHERE id = (SELECT id FROM tmp_attivita_fd)
  ),
  (SELECT lock_batch_id FROM tmp_costanti_fd),
  'Lock_batch_id valorizzato'
);

-- ============================================================
-- Cleanup
-- ============================================================
DELETE FROM vendite.attivita_fatturabili
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_fd);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
