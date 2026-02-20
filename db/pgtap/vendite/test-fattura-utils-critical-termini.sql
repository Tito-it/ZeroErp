-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: utilita fattura (critical, termini, fondi, wrapper sync)
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento fattura di test
-- 3) Tipo fondo fattura disponibile
-- 4) Totale fondi iniziale a zero
-- 5) Totale fondi considera solo righe attive
-- 6) Sync critical senza log critical
-- 7) Sync critical con log critical attivo
-- 8) Sync critical dopo disabilitazione log
-- 9) Resolve termini fallback su TP_1RATA
-- 10) Resolve termini errore su fattura_id non valido
-- 11) Sync pagamento fondo errore su fattura_id non valido
-- 12) Cleanup completato
-- ------------------------------------------------------------

BEGIN;

SELECT plan(15);

-- ============================================================
-- 0) Costanti e riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_costanti_fu AS
SELECT
  'pgtap_fattura_utils_critical_termini'::text AS test_scope;

CREATE TEMP TABLE tmp_tp_default_fu AS
WITH existing AS (
  SELECT tp.id, false AS created_by_test
  FROM config.termini_pagamento tp
  WHERE tp.codice_interno = 'TP_1RATA'
    AND tp.attivo IS TRUE
  ORDER BY tp.id
  LIMIT 1
), ins AS (
  INSERT INTO config.termini_pagamento (
    codice,
    codice_interno,
    descrizione,
    numero_rate,
    unita_intervallo,
    intervallo,
    primo_offset_giorni,
    tipo_offset,
    ripartizione,
    arrotondamento_metodo,
    arrotondamento_decimali,
    attivo
  )
  SELECT
    'TP1RATA_TEST_' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'),
    'TP_1RATA',
    'Termine default test pgTap',
    1,
    'G',
    0,
    0,
    'N',
    'UGUALI',
    'HALF_UP',
    2,
    TRUE
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id, true AS created_by_test
)
SELECT * FROM existing
UNION ALL
SELECT * FROM ins;

CREATE TEMP TABLE tmp_refs_fu AS
WITH ba AS (
  SELECT b.id
  FROM anagrafiche.billing_account b
  ORDER BY b.data_insert DESC NULLS LAST
  LIMIT 1
)
SELECT
  (
    SELECT id
    FROM vendite.registri_fatturazione
    WHERE attivo IS TRUE
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1
  ) AS registro_id,
  (
    SELECT m.emittente_soggetto_ruolo_id
    FROM anagrafiche.emittenti_fiscali_billing_account m
    WHERE m.billing_account_id = (SELECT id FROM ba)
       OR m.is_default IS TRUE
    ORDER BY CASE WHEN m.billing_account_id = (SELECT id FROM ba) THEN 0 ELSE 1 END,
             m.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
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
    SELECT t.id
    FROM tmp_tp_default_fu t
    LIMIT 1
  ) AS tp_default_id,
  (SELECT id FROM ba) AS billing_account_id;

SELECT ok(
  (
    SELECT registro_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
       AND tipo_doc_fiscale_id IS NOT NULL
       AND valuta_id IS NOT NULL
       AND tp_default_id IS NOT NULL
       AND billing_account_id IS NOT NULL
    FROM tmp_refs_fu
  ),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- 1) Fattura di test
-- ============================================================
CREATE TEMP TABLE tmp_fattura_fu AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    valuta_id,
    totale_a_pagare,
    meta
  )
  SELECT
    r.registro_id,
    current_date,
    r.emittente_soggetto_ruolo_id,
    r.billing_account_id,
    r.tipo_doc_fiscale_id,
    r.valuta_id,
    50.00,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_fu))
  FROM tmp_refs_fu r
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_fattura_fu),
  'Inserimento fattura di test'
);

-- ============================================================
-- 2) Tipo fondo fattura
-- ============================================================
CREATE TEMP TABLE tmp_tipo_fondo_fu AS
SELECT t.id
FROM vendite.tipi_fondi_fattura t
WHERE t.attivo IS TRUE
  AND t.codice_interno = 'F_F_ADD_ACC'
ORDER BY t.id
LIMIT 1;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_tipo_fondo_fu),
  'Tipo fondo fattura disponibile'
);

-- ============================================================
-- 3) Totale fondi fattura
-- ============================================================
SELECT is(
  vendite.fn_get_totale_fondi_fattura((SELECT id FROM tmp_fattura_fu)),
  0::numeric,
  'Totale fondi iniziale a zero'
);

INSERT INTO vendite.fatture_fondi_fattura (
  fattura_id,
  riferimento_fattura_id,
  tipo_fondo_fattura_id,
  importo,
  meta,
  attivo
)
SELECT
  (SELECT id FROM tmp_fattura_fu),
  NULL,
  (SELECT id FROM tmp_tipo_fondo_fu),
  x.importo,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_fu), 'idx', x.idx),
  x.attivo
FROM (VALUES
  (1, 10.50::numeric, true),
  (2, 2.25::numeric, false)
) AS x(idx, importo, attivo);

SELECT is(
  vendite.fn_get_totale_fondi_fattura((SELECT id FROM tmp_fattura_fu)),
  10.50::numeric,
  'Totale fondi considera solo righe attive'
);

-- ============================================================
-- 4) Sync critical su fattura
-- ============================================================
SELECT lives_ok(
  format(
    'SELECT vendite.fn_sync_fattura_critical(%s)',
    (SELECT id::text FROM tmp_fattura_fu)
  ),
  'Sync critical senza log critical'
);

SELECT is(
  (SELECT critical FROM vendite.fatture WHERE id = (SELECT id FROM tmp_fattura_fu)),
  false,
  'Sync critical con stato iniziale false'
);

INSERT INTO vendite.fatture_log (
  fattura_id,
  data_ora,
  messaggio,
  status,
  disabilitato,
  meta
)
SELECT
  (SELECT id FROM tmp_fattura_fu),
  now(),
  'Errore critico test',
  'C',
  false,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_fu));

SELECT lives_ok(
  format(
    'SELECT vendite.fn_sync_fattura_critical(%s)',
    (SELECT id::text FROM tmp_fattura_fu)
  ),
  'Sync critical con log critical attivo'
);

SELECT is(
  (SELECT critical FROM vendite.fatture WHERE id = (SELECT id FROM tmp_fattura_fu)),
  true,
  'Sync critical imposta true'
);

UPDATE vendite.fatture_log
SET disabilitato = true,
    data_update = now(),
    user_update = current_user
WHERE fattura_id = (SELECT id FROM tmp_fattura_fu)
  AND status = 'C';

SELECT lives_ok(
  format(
    'SELECT vendite.fn_sync_fattura_critical(%s)',
    (SELECT id::text FROM tmp_fattura_fu)
  ),
  'Sync critical dopo disabilitazione log'
);

SELECT is(
  (SELECT critical FROM vendite.fatture WHERE id = (SELECT id FROM tmp_fattura_fu)),
  false,
  'Sync critical torna false dopo disabilitazione'
);

-- ============================================================
-- 5) Resolve termini pagamento
-- ============================================================
SELECT is(
  (
    SELECT x.termini_pagamento_id
    FROM vendite.fn_resolve_termini_pagamento(
      p_fattura_id => NULL,
      p_billing_account_id => NULL,
      p_attivita_ids => NULL
    ) x
    LIMIT 1
  ),
  (SELECT tp_default_id FROM tmp_refs_fu),
  'Resolve termini fallback su TP_1RATA'
);

SELECT throws_ok(
  $$
    SELECT *
    FROM vendite.fn_resolve_termini_pagamento(
      p_fattura_id => -1,
      p_billing_account_id => NULL,
      p_attivita_ids => NULL
    );
  $$,
  'P0001',
  NULL,
  'Resolve termini errore su fattura_id non valido'
);

-- ============================================================
-- 6) Wrapper sync pagamento fondo (guard)
-- ============================================================
SELECT throws_ok(
  $$
    SELECT *
    FROM vendite.fn_sync_pagamento_fondo_fattura(
      p_fattura_figlia_id => 0
    );
  $$,
  'P0001',
  NULL,
  'Sync pagamento fondo errore su fattura_id non valido'
);

-- ============================================================
-- Cleanup
-- ============================================================
DELETE FROM vendite.fatture_log
WHERE fattura_id = (SELECT id FROM tmp_fattura_fu);

DELETE FROM vendite.fatture_fondi_fattura
WHERE fattura_id = (SELECT id FROM tmp_fattura_fu);

UPDATE vendite.fatture
SET storicizza = false
WHERE id = (SELECT id FROM tmp_fattura_fu);

DELETE FROM vendite.fatture
WHERE id = (SELECT id FROM tmp_fattura_fu);

DELETE FROM config.termini_pagamento
WHERE id IN (
  SELECT t.id
  FROM tmp_tp_default_fu t
  WHERE t.created_by_test IS TRUE
);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
