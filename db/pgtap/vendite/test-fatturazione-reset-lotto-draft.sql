-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: rollback tecnico lotto MASSIVO in DRAFT
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti (stati, anagrafiche, catalogo)
-- 2) Inserimento lotto DRAFT
-- 3) Inserimento attivita_fatturabili di test
-- 4) Creazione fattura bozza + link lotto
-- 5) Inserimento riga fattura
-- 6) Reset lotto DRAFT
-- 7) Lotto annullato e chiuso
-- 8) Documenti e righe eliminati
-- 9) Attivita_fatturabili ripristinate
-- 10) Cleanup completato
-- ------------------------------------------------------------
BEGIN;
SELECT plan(10);
-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_rl AS
SELECT 'pgtap_reset_lotto_draft'::text AS test_scope,
  uuidv7() AS lock_batch_id;
CREATE TEMP TABLE tmp_refs_rl AS
SELECT (
    SELECT id
    FROM config.stati_doc_fiscale
    WHERE upper(btrim(codice)) = 'DRAFT'
    LIMIT 1
  ) AS stato_draft_id,
  (
    SELECT id
    FROM config.stati_doc_fiscale
    WHERE upper(btrim(codice)) = 'ANNULLATA'
    LIMIT 1
  ) AS stato_annullata_id,
  (
    SELECT id
    FROM catalogo.articoli
    WHERE attivo IS TRUE
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT id
    FROM anagrafiche.istanze_utilities
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1
  ) AS istanza_utility_id,
  (
    SELECT id
    FROM anagrafiche.billing_account
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT utility_id
    FROM anagrafiche.billing_account
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1
  ) AS utility_id,
  (
    SELECT id
    FROM config.tipi_doc_fiscale
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT id
    FROM config.valute
    ORDER BY id
    LIMIT 1
  ) AS valuta_id;
SELECT ok(
    (
      SELECT stato_draft_id IS NOT NULL
        AND stato_annullata_id IS NOT NULL
        AND articolo_id IS NOT NULL
        AND istanza_utility_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
      FROM tmp_refs_rl
    ),
    'Riferimenti minimi presenti'
  );
-- ============================================================
-- 1) Inserimento lotto DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_lotto_rl AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      lock_batch_id,
      competenza_mese,
      tipo_doc_fiscale_id,
      utility_id,
      billing_account_id,
      stato_doc_fiscale_id
    )
  SELECT (
      SELECT lock_batch_id
      FROM tmp_costanti_rl
    ),
    date_trunc('month', current_date)::date,
    r.tipo_doc_fiscale_id,
    r.utility_id,
    r.billing_account_id,
    r.stato_draft_id
  FROM tmp_refs_rl r
  RETURNING id,
    lock_batch_id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_lotto_rl
    ),
    'Inserimento lotto DRAFT'
  );
-- ============================================================
-- 2) Inserimento attivita_fatturabili di test
-- ============================================================
CREATE TEMP TABLE tmp_attivita_rl AS WITH ins AS (
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
      meta
    )
  SELECT r.articolo_id,
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
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_rl
      )
    )
  FROM tmp_refs_rl r
  RETURNING id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_attivita_rl
    ),
    'Inserimento attivita_fatturabili di test'
  );
-- ============================================================
-- 3) Creazione fattura bozza + link lotto
-- ============================================================
CREATE TEMP TABLE tmp_fattura_rl AS
SELECT vendite.fn_get_or_create_fattura_header(
    p_lotto_id => (
      SELECT id
      FROM tmp_lotto_rl
    ),
    p_attivita_id => (
      SELECT id
      FROM tmp_attivita_rl
    )
  ) AS fattura_id;
SELECT ok(
    (
      SELECT fattura_id IS NOT NULL
      FROM tmp_fattura_rl
    ),
    'Creazione fattura bozza + link lotto'
  );
-- ============================================================
-- 4) Inserimento riga fattura
-- ============================================================
CREATE TEMP TABLE tmp_fattura_riga_rl AS WITH ins AS (
  INSERT INTO vendite.fatture_righe (
      fattura_id,
      riga_nr,
      descrizione,
      qta,
      prezzo_unitario,
      meta
    )
  VALUES (
      (
        SELECT fattura_id
        FROM tmp_fattura_rl
      ),
      1,
      'Riga test rollback',
      1,
      10,
      jsonb_build_object(
        'test_scope',
        (
          SELECT test_scope
          FROM tmp_costanti_rl
        )
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
UPDATE vendite.attivita_fatturabili
SET lock_in_fatturazione = true,
  lock_batch_id = (
    SELECT lock_batch_id
    FROM tmp_lotto_rl
  ),
  fatturato = true,
  fattura_riga_id = (
    SELECT id
    FROM tmp_fattura_riga_rl
  )
WHERE id = (
    SELECT id
    FROM tmp_attivita_rl
  );
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_fattura_riga_rl
    ),
    'Inserimento riga fattura'
  );
-- ============================================================
-- 5) Reset lotto DRAFT
-- ============================================================
SELECT ok(
    (
      SELECT updated_lotti = 1
      FROM vendite.fn_reset_lotto_draft(
          (
            SELECT id
            FROM tmp_lotto_rl
          )
        )
    ),
    'Reset lotto DRAFT'
  );
-- ============================================================
-- 6) Lotto annullato e chiuso
-- ============================================================
SELECT ok(
    (
      SELECT fl.stato_doc_fiscale_id = (
          SELECT stato_annullata_id
          FROM tmp_refs_rl
        )
        AND fl.stato_operativo = 'CHIUSO'
        AND fl.stato_lotto = 'COMPLETATO'
      FROM vendite.fatturazione_lotti fl
      WHERE fl.id = (
          SELECT id
          FROM tmp_lotto_rl
        )
    ),
    'Lotto annullato e chiuso'
  );
-- ============================================================
-- 7) Documenti e righe eliminati
-- ============================================================
SELECT ok(
    (
      SELECT count(*) = 0
      FROM vendite.fatture f
      WHERE f.id = (
          SELECT fattura_id
          FROM tmp_fattura_rl
        )
    ),
    'Fatture eliminate'
  );
SELECT ok(
    (
      SELECT count(*) = 0
      FROM vendite.fatture_righe r
      WHERE r.id = (
          SELECT id
          FROM tmp_fattura_riga_rl
        )
    ),
    'Righe fattura eliminate'
  );
-- ============================================================
-- 8) Attivita_fatturabili ripristinate
-- ============================================================
SELECT ok(
    (
      SELECT lock_in_fatturazione IS FALSE
        AND lock_batch_id IS NULL
        AND fatturato IS FALSE
        AND fattura_riga_id IS NULL
      FROM vendite.attivita_fatturabili
      WHERE id = (
          SELECT id
          FROM tmp_attivita_rl
        )
    ),
    'Attivita_fatturabili ripristinate'
  );
SELECT *
FROM finish();
ROLLBACK;
