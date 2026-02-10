-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_ricalcola_riepilogo_iva_fattura / vendite.fn_ricalcola_riepiloghi_iva_lotto
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento registro di test
-- 3) Inserimento fattura di test
-- 4) Inserimento righe fattura di test
-- 5) Ricalcolo IVA fattura (inserted_rows=1)
-- 6) Imposta ricalcolata da imponibile * aliquota_iva
-- 7) Override iva_stati applicato
-- 8) Ricalcolo IVA fattura idempotente (deleted_rows=1)
-- 9) Inserimento lotto + collegamento fattura
-- 10) Ricalcolo IVA lotto (fatture_count=1)
-- 11) Totali testata aggiornati
-- 12) Cleanup completato
-- ------------------------------------------------------------
BEGIN;
SELECT plan(12);
-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_iva AS
SELECT 'pgtap_ricalcola_iva'::text AS test_scope;
CREATE TEMP TABLE tmp_refs_iva AS
SELECT (
    SELECT soggetto_ruolo_id
    FROM anagrafiche.emittenti_fiscali
    WHERE attivo IS TRUE
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (
    SELECT id
    FROM anagrafiche.billing_account
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT id
    FROM config.iva
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1
  ) AS iva_id,
  (
    SELECT id
    FROM config.tipi_doc_fiscale
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT id
    FROM config.stati_doc_fiscale
    WHERE codice_interno IN ('DRAFT')
    ORDER BY id
    LIMIT 1
  ) AS stato_doc_fiscale_id;
SELECT ok(
    (
      SELECT emittente_soggetto_ruolo_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND iva_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND stato_doc_fiscale_id IS NOT NULL
      FROM tmp_refs_iva
    ),
    'Riferimenti minimi presenti'
  );
-- ============================================================
-- 1) Registro di test
-- ============================================================
CREATE TEMP TABLE tmp_reg_iva AS WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (
      codice,
      descrizione,
      reset_policy,
      attivo,
      meta
    )
  SELECT left(
      'REGIVA_' || (
        SELECT test_scope
        FROM tmp_costanti_iva
      ),
      16
    ),
    'Registro test IVA',
    'ANNUALE',
    true,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_iva
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_reg_iva
    ),
    'Inserimento registro di test'
  );
-- ============================================================
-- 2) Fattura di test
-- ============================================================
CREATE TEMP TABLE tmp_fattura_iva AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id,
      data,
      emittente_soggetto_ruolo_id,
      billing_account_id,
      tipo_doc_fiscale_id,
      stato_doc_fiscale_id,
      meta
    )
  SELECT (
      SELECT id
      FROM tmp_reg_iva
    ),
    current_date,
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_iva
    ),
    (
      SELECT billing_account_id
      FROM tmp_refs_iva
    ),
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_iva
    ),
    (
      SELECT stato_doc_fiscale_id
      FROM tmp_refs_iva
    ),
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_iva
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_fattura_iva
    ),
    'Inserimento fattura di test'
  );
-- ============================================================
-- 3) Righe fattura di test
-- ============================================================
INSERT INTO vendite.fatture_righe (
    fattura_id,
    riga_nr,
    descrizione,
    qta,
    prezzo_unitario,
    iva_id,
    imponibile_riga,
    imposta_riga,
    totale_riga,
    meta
  )
SELECT (
    SELECT id
    FROM tmp_fattura_iva
  ),
  v.riga_nr,
  v.descrizione,
  v.qta,
  v.prezzo_unitario,
  (
    SELECT iva_id
    FROM tmp_refs_iva
  ),
  v.imponibile_riga,
  v.imposta_riga,
  v.totale_riga,
  jsonb_build_object(
    'test_scope',
    (
      SELECT test_scope
      FROM tmp_costanti_iva
    )
  )
FROM (
    VALUES (
        1,
        'Riga IVA 1',
        1::numeric,
        100::numeric,
        100::numeric,
        22::numeric,
        122::numeric
      ),
      (
        2,
        'Riga IVA 2',
        1::numeric,
        50::numeric,
        50::numeric,
        11::numeric,
        61::numeric
      )
  ) AS v(
    riga_nr,
    descrizione,
    qta,
    prezzo_unitario,
    imponibile_riga,
    imposta_riga,
    totale_riga
  );
SELECT ok(true, 'Inserimento righe fattura di test');
-- ============================================================
-- 4) Ricalcolo IVA su fattura (prima volta)
-- ============================================================
SELECT is(
    (
      SELECT inserted_rows
      FROM vendite.fn_ricalcola_riepilogo_iva_fattura(
          (
            SELECT id
            FROM tmp_fattura_iva
          )
        )
    ),
    1::int,
    'Ricalcolo IVA fattura (inserted_rows=1)'
  );
SELECT is(
    (
      SELECT imposta
      FROM vendite.fatture_riepiloghi_iva
      WHERE fattura_id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    (
      SELECT ROUND(
          ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2) * (
            COALESCE(MAX(i.aliquota_iva), 0)::numeric / 100::numeric
          ),
          2
        )
      FROM vendite.fatture_righe r
        LEFT JOIN config.iva i ON i.id = r.iva_id
      WHERE r.fattura_id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    'Imposta ricalcolata da imponibile * aliquota_iva'
  );
-- ============================================================
-- 6) Override iva_stati
-- ============================================================
INSERT INTO config.iva_stati (
    iva_id,
    stato_id,
    aliquota_override,
    assoggettamento_id_override
  )
SELECT (
    SELECT iva_id
    FROM tmp_refs_iva
  ),
  s.stato_id,
  5::numeric,
  null
  /*
   (
   SELECT assoggettamento_id
   FROM config.iva
   WHERE id = (
   SELECT iva_id
   FROM tmp_refs_iva
   )
   )*/
FROM vendite.fatture f
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.emittente_soggetto_ruolo_id
  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
WHERE f.id = (
    SELECT id
    FROM tmp_fattura_iva
  );
SELECT *
FROM vendite.fn_ricalcola_riepilogo_iva_fattura(
    (
      SELECT id
      FROM tmp_fattura_iva
    )
  );
SELECT is(
    (
      SELECT imposta
      FROM vendite.fatture_riepiloghi_iva
      WHERE fattura_id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    (
      SELECT ROUND(
          ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2) * (5::numeric / 100::numeric),
          2
        )
      FROM vendite.fatture_righe r
      WHERE r.fattura_id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    'Override iva_stati applicato'
  );
-- ============================================================
-- 5) Ricalcolo IVA su fattura (idempotente)
-- ============================================================
SELECT is(
    (
      SELECT deleted_rows
      FROM vendite.fn_ricalcola_riepilogo_iva_fattura(
          (
            SELECT id
            FROM tmp_fattura_iva
          )
        )
    ),
    1::int,
    'Ricalcolo IVA fattura idempotente (deleted_rows=1)'
  );
-- ============================================================
-- 6) Lotto + collegamento fattura
-- ============================================================
CREATE TEMP TABLE tmp_lotto_iva AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      competenza_mese,
      tipo_doc_fiscale_id,
      meta
    )
  SELECT date_trunc('month', current_date)::date,
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_iva
    ),
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_iva
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, meta)
SELECT (
    SELECT id
    FROM tmp_lotto_iva
  ),
  (
    SELECT id
    FROM tmp_fattura_iva
  ),
  jsonb_build_object(
    'test_scope',
    (
      SELECT test_scope
      FROM tmp_costanti_iva
    )
  );
SELECT ok(true, 'Inserimento lotto + collegamento fattura');
-- ============================================================
-- 7) Ricalcolo IVA su lotto
-- ============================================================
SELECT is(
    (
      SELECT fatture_count
      FROM vendite.fn_ricalcola_riepiloghi_iva_lotto(
          (
            SELECT id
            FROM tmp_lotto_iva
          ),
          1000
        )
    ),
    1::int,
    'Ricalcolo IVA lotto (fatture_count=1)'
  );

SELECT ok(
    (
      SELECT imponibile_tot IS NOT NULL
         AND imposta_tot IS NOT NULL
         AND totale_doc IS NOT NULL
      FROM vendite.fatture
      WHERE id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    'Totali testata aggiornati'
  );
-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatture_riepiloghi_iva
SET data_update = now()
WHERE fattura_id = (
    SELECT id
    FROM tmp_fattura_iva
  );
UPDATE vendite.fatture_righe
SET storicizza = false
WHERE fattura_id = (
    SELECT id
    FROM tmp_fattura_iva
  );
UPDATE vendite.fatture
SET storicizza = false
WHERE id = (
    SELECT id
    FROM tmp_fattura_iva
  );
UPDATE vendite.fatturazione_lotti_fatture
SET storicizza = false
WHERE lotto_id = (
    SELECT id
    FROM tmp_lotto_iva
  );
UPDATE vendite.fatturazione_lotti
SET storicizza = false
WHERE id = (
    SELECT id
    FROM tmp_lotto_iva
  );
UPDATE vendite.registri_fatturazione
SET storicizza = false
WHERE id = (
    SELECT id
    FROM tmp_reg_iva
  );
DELETE FROM vendite.fatture_riepiloghi_iva
WHERE fattura_id = (
    SELECT id
    FROM tmp_fattura_iva
  );
DELETE FROM vendite.fatture_righe
WHERE fattura_id = (
    SELECT id
    FROM tmp_fattura_iva
  );
DELETE FROM vendite.fatturazione_lotti_fatture
WHERE lotto_id = (
    SELECT id
    FROM tmp_lotto_iva
  );
DELETE FROM vendite.fatturazione_lotti
WHERE id = (
    SELECT id
    FROM tmp_lotto_iva
  );
DELETE FROM vendite.fatture
WHERE id = (
    SELECT id
    FROM tmp_fattura_iva
  );
DELETE FROM vendite.registri_fatturazione_progressivi
WHERE registro_id = (
    SELECT id
    FROM tmp_reg_iva
  );
DELETE FROM vendite.registri_fatturazione
WHERE id = (
    SELECT id
    FROM tmp_reg_iva
  );
DELETE FROM config.iva_stati
WHERE iva_id = (
    SELECT iva_id
    FROM tmp_refs_iva
  )
  AND stato_id IN (
    SELECT s.stato_id
    FROM vendite.fatture f
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.emittente_soggetto_ruolo_id
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
    WHERE f.id = (
        SELECT id
        FROM tmp_fattura_iva
      )
  );
SELECT ok(true, 'Cleanup completato');
SELECT *
FROM finish();
ROLLBACK;
