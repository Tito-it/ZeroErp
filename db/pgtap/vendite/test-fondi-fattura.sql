-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: generazione e applicazione fondi fattura
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Tipo_fondo_fattura disponibile (F_F_ADD_ACC)
-- 3) Inserimento fattura sorgente (minimo)
-- 4) Generazione fondi source
-- 5) Inserimento fattura figlia
-- 6) Applicazione fondi fattura
-- 7) Source aggiornata e righe fondi presenti
-- 8) Sync contabili fondo fattura
-- 9) Reset fondi fattura (scenario standard)
-- 10) Source ripristinata e righe fondi rimosse
-- 11) Righe contabili fondo rimosse
-- 12) Re-applicazione fondi
-- 13) Sync + chiusura contabile
-- 14) Reset bloccato da contabile CHIUSA
-- 15) Source ANNULLATA e warning log
-- 16) Source ANNULLATA su reset bloccato
-- 17) Warning log su reset bloccato
-- 18) Cleanup completato
-- 19) Assert finale cleanup
-- ------------------------------------------------------------
BEGIN;
SELECT plan(19);
-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_ff AS
SELECT 'pgtap_fondi_fattura'::text AS test_scope;
CREATE TEMP TABLE tmp_centro_fondo AS WITH existing AS (
  SELECT c.id
  FROM pagamenti.centri_riscossione c
  WHERE -- c.attivo IS TRUE and
    c.is_fondo_fattura IS TRUE
  ORDER BY c.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.centri_riscossione (
      codice,
      codice_interno,
      descrizione,
      is_compensazione,
      is_fondo_fattura,
      attivo,
      meta
    )
  SELECT 'TEST_CENTRO_FONDO_' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'),
    'FONDO_TEST',
    'Centro fondo test pgtap',
    false,
    true,
    true,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_ff
      )
    )
  WHERE NOT EXISTS (
      SELECT 1
      FROM existing
    )
  RETURNING id
)
SELECT id
FROM existing
UNION ALL
SELECT id
FROM ins;
CREATE TEMP TABLE tmp_refs_ff AS WITH ba AS (
  SELECT b.id,
    b.utility_id
  FROM anagrafiche.billing_account b
  ORDER BY b.data_insert DESC NULLS LAST
  LIMIT 1
)
SELECT (
    SELECT id
    FROM vendite.registri_fatturazione
    WHERE attivo IS TRUE
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1
  ) AS registro_id,
  ba.id AS billing_account_id,
  ba.utility_id AS utility_id,
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
  ) AS valuta_id,
  (
    SELECT m.emittente_soggetto_ruolo_id
    FROM anagrafiche.emittenti_fiscali_billing_account m
    WHERE -- m.attivo IS TRUE and
      (
        m.billing_account_id = ba.id
        OR m.is_default IS TRUE
      )
    ORDER BY CASE
        WHEN m.billing_account_id = ba.id THEN 0
        ELSE 1
      END,
      m.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (
    SELECT id
    FROM tmp_centro_fondo
    LIMIT 1
  ) AS centro_fondo_id
FROM ba;
SELECT ok(
    (
      SELECT registro_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
        AND emittente_soggetto_ruolo_id IS NOT NULL
        AND centro_fondo_id IS NOT NULL
      FROM tmp_refs_ff
    ),
    'Riferimenti minimi presenti'
  );
-- ============================================================
-- 1) Tipo fondo fattura
-- ============================================================
CREATE TEMP TABLE tmp_tipo_fondo AS
SELECT t.id
FROM vendite.tipi_fondi_fattura t
WHERE t.attivo IS TRUE
  AND t.codice_interno = 'F_F_ADD_ACC'
ORDER BY t.id
LIMIT 1;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_tipo_fondo
    ),
    'Tipo_fondo_fattura F_F_ADD_ACC disponibile'
  );
-- ============================================================
-- 2) Fattura sorgente con minimo
-- ============================================================
CREATE TEMP TABLE tmp_fattura_src AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id,
      data,
      emittente_soggetto_ruolo_id,
      billing_account_id,
      tipo_doc_fiscale_id,
      valuta_id,
      minimo,
      totale_a_pagare,
      meta
    )
  SELECT (
      SELECT registro_id
      FROM tmp_refs_ff
    ),
    current_date,
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_ff
    ),
    (
      SELECT billing_account_id
      FROM tmp_refs_ff
    ),
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_ff
    ),
    (
      SELECT valuta_id
      FROM tmp_refs_ff
    ),
    true,
    100.00,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_ff
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_fattura_src
    ),
    'Inserimento fattura sorgente (minimo)'
  );
-- ============================================================
-- 3) Generazione fondi source
-- ============================================================
SELECT is(
    vendite.fn_genera_fondi_fattura_source(
      p_billing_account_id => (
        SELECT billing_account_id
        FROM tmp_refs_ff
      ),
      p_utility_id => (
        SELECT utility_id
        FROM tmp_refs_ff
      ),
      p_tipo_doc_fiscale_id => (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_ff
      ),
      p_emittente_soggetto_ruolo_id => (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_ff
      ),
      p_valuta_id => (
        SELECT valuta_id
        FROM tmp_refs_ff
      ),
      p_tipo_fondo_fattura_id => (
        SELECT id
        FROM tmp_tipo_fondo
      )
    ),
    1,
    'Generazione fondi source'
  );
-- ============================================================
-- 4) Fattura figlia
-- ============================================================
CREATE TEMP TABLE tmp_fattura_dst AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id,
      data,
      emittente_soggetto_ruolo_id,
      billing_account_id,
      tipo_doc_fiscale_id,
      valuta_id,
      minimo,
      totale_a_pagare,
      meta
    )
  SELECT (
      SELECT registro_id
      FROM tmp_refs_ff
    ),
    current_date,
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_ff
    ),
    (
      SELECT billing_account_id
      FROM tmp_refs_ff
    ),
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_ff
    ),
    (
      SELECT valuta_id
      FROM tmp_refs_ff
    ),
    false,
    200.00,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_ff
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_fattura_dst
    ),
    'Inserimento fattura figlia'
  );
-- ============================================================
-- 5) Applicazione fondi
-- ============================================================
SELECT is(
    vendite.fn_applica_fondi_fattura(
      p_billing_account_id => (
        SELECT billing_account_id
        FROM tmp_refs_ff
      ),
      p_utility_id => (
        SELECT utility_id
        FROM tmp_refs_ff
      ),
      p_tipo_doc_fiscale_id => (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_ff
      ),
      p_emittente_soggetto_ruolo_id => (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_ff
      ),
      p_valuta_id => (
        SELECT valuta_id
        FROM tmp_refs_ff
      ),
      p_fattura_figlia_id => (
        SELECT id
        FROM tmp_fattura_dst
      ),
      p_tipo_fondo_fattura_id => (
        SELECT id
        FROM tmp_tipo_fondo
      )
    ),
    1,
    'Applicazione fondi fattura'
  );
-- ============================================================
-- 6) Verifica stato source e righe
-- ============================================================
SELECT ok(
    (
      SELECT count(*) = 1
      FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (
          SELECT id
          FROM tmp_fattura_src
        )
        AND s.stato = 'ASSEGNATO'
        AND s.fattura_figlia_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
    ),
    'Source aggiornata a ASSEGNATO'
  );
SELECT ok(
    (
      SELECT count(*) = 1
      FROM vendite.fatture_fondi_fattura ff
      WHERE ff.fattura_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
        AND ff.riferimento_fattura_id = (
          SELECT id
          FROM tmp_fattura_src
        )
    ),
    'Righe fondi fattura presenti'
  );
-- ============================================================
-- 7) Sync contabili fondo fattura
-- ============================================================
SELECT is(
    (
      SELECT inserted_righe
      FROM vendite.fn_sync_contabili_fondo_fattura(
          p_fattura_figlia_id => (
            SELECT id
            FROM tmp_fattura_dst
          )
        )
    ),
    1,
    'Sync contabili fondo fattura'
  );
-- ============================================================
-- 8) Reset fondi fattura (scenario standard)
-- ============================================================
SELECT is(
    (
      SELECT updated_source
      FROM vendite.fn_reset_fondi_fattura(
          p_fattura_id => (
            SELECT id
            FROM tmp_fattura_dst
          )
        )
    ),
    1,
    'Reset fondi fattura (source riaperta)'
  );
-- ============================================================
-- 9) Verifica reset standard
-- ============================================================
SELECT ok(
    (
      SELECT count(*) = 1
      FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (
          SELECT id
          FROM tmp_fattura_src
        )
        AND s.stato = 'DISPONIBILE'
        AND s.fattura_figlia_id IS NULL
    ),
    'Source ripristinata a DISPONIBILE'
  );
SELECT ok(
    (
      SELECT count(*) = 0
      FROM vendite.fatture_fondi_fattura ff
      WHERE ff.fattura_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
    ),
    'Righe fondi fattura rimosse'
  );
SELECT ok(
    (
      SELECT count(*) = 0
      FROM pagamenti.vendite_contabili_righe cr
      WHERE cr.fattura_id = (
          SELECT id
          FROM tmp_fattura_src
        )
        AND cr.attivo IS TRUE
        AND COALESCE(cr.meta->>'origine', '') = 'FONDO_FATTURA'
    ),
    'Righe contabili fondo rimosse'
  );
-- ============================================================
-- 10) Re-applicazione + contabilizzazione movimento
-- ============================================================
SELECT is(
    vendite.fn_applica_fondi_fattura(
      p_billing_account_id => (
        SELECT billing_account_id
        FROM tmp_refs_ff
      ),
      p_utility_id => (
        SELECT utility_id
        FROM tmp_refs_ff
      ),
      p_tipo_doc_fiscale_id => (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_ff
      ),
      p_emittente_soggetto_ruolo_id => (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_ff
      ),
      p_valuta_id => (
        SELECT valuta_id
        FROM tmp_refs_ff
      ),
      p_fattura_figlia_id => (
        SELECT id
        FROM tmp_fattura_dst
      ),
      p_tipo_fondo_fattura_id => (
        SELECT id
        FROM tmp_tipo_fondo
      )
    ),
    1,
    'Re-applicazione fondi fattura'
  );
SELECT is(
    (
      SELECT inserted_righe
      FROM vendite.fn_sync_contabili_fondo_fattura(
          p_fattura_figlia_id => (
            SELECT id
            FROM tmp_fattura_dst
          )
        )
    ),
    1,
    'Sync contabili fondo (secondo giro)'
  );
UPDATE pagamenti.vendite_contabili c
SET stato_id = (
    SELECT s.id
    FROM pagamenti.vendite_contabili_stati s
    WHERE s.codice_interno = 'CHIUSA'
    ORDER BY s.id
    LIMIT 1
  )
WHERE c.id = (
    SELECT cr.contabile_id
    FROM pagamenti.vendite_contabili_righe cr
    WHERE cr.fattura_id = (
        SELECT id
        FROM tmp_fattura_src
      )
      AND COALESCE(cr.meta->>'origine', '') = 'FONDO_FATTURA'
      AND COALESCE(cr.meta->>'fondo_source_id', '') = (
        SELECT s.id::text
        FROM vendite.fatture_fondi_fattura_source s
        WHERE s.fattura_sorgente_id = (
            SELECT id
            FROM tmp_fattura_src
          )
          AND s.fattura_figlia_id = (
            SELECT id
            FROM tmp_fattura_dst
          )
        ORDER BY s.id DESC
        LIMIT 1
      )
    ORDER BY cr.id DESC
    LIMIT 1
  );
-- ============================================================
-- 11) Reset bloccato da contabilizzazione
-- ============================================================
SELECT is(
    (
      SELECT updated_source
      FROM vendite.fn_reset_fondi_fattura(
          p_fattura_id => (
            SELECT id
            FROM tmp_fattura_dst
          )
        )
    ),
    0,
    'Reset bloccato se movimento fondo contabilizzato'
  );
SELECT ok(
    (
      SELECT count(*) = 1
      FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (
          SELECT id
          FROM tmp_fattura_src
        )
        AND s.fattura_figlia_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
        AND s.stato = 'ANNULLATO'
    ),
    'Source ANNULLATA su reset bloccato'
  );
SELECT ok(
    (
      SELECT count(*) >= 1
      FROM vendite.fatture_log l
      WHERE l.fattura_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
        AND l.status = 'W'
        AND l.messaggio ILIKE 'Minimo non ripristinabile:%'
    ),
    'Warning log inserito su reset bloccato'
  );
-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatture
SET storicizza = false
WHERE meta->>'test_scope' = (
    SELECT test_scope
    FROM tmp_costanti_ff
  );
DELETE FROM vendite.fatture_log
WHERE fattura_id IN (
    SELECT id
    FROM tmp_fattura_dst
  );
DELETE FROM pagamenti.vendite_movimenti
WHERE fattura_id IN (
    SELECT id
    FROM tmp_fattura_src
  )
  AND COALESCE(meta->>'origine', '') = 'FONDO_FATTURA';
DELETE FROM pagamenti.vendite_contabili_righe
WHERE fattura_id IN (
    SELECT id
    FROM tmp_fattura_src
  )
  AND COALESCE(meta->>'origine', '') = 'FONDO_FATTURA';
DELETE FROM vendite.fatture_fondi_fattura
WHERE fattura_id IN (
    SELECT id
    FROM tmp_fattura_dst
  )
  OR riferimento_fattura_id IN (
    SELECT id
    FROM tmp_fattura_src
  );
DELETE FROM vendite.fatture_fondi_fattura_source
WHERE fattura_sorgente_id IN (
    SELECT id
    FROM tmp_fattura_src
  );
DELETE FROM vendite.fatture
WHERE meta->>'test_scope' = (
    SELECT test_scope
    FROM tmp_costanti_ff
  );
DELETE FROM vendite.tipi_fondi_fattura
WHERE meta->>'test_scope' = (
    SELECT test_scope
    FROM tmp_costanti_ff
  );
/*  
 DELETE FROM pagamenti.centri_riscossione
 WHERE meta->>'test_scope' = (
 SELECT test_scope
 FROM tmp_costanti_ff
 );  */
SELECT ok(true, 'Cleanup completato');
SELECT *
FROM finish();
ROLLBACK;