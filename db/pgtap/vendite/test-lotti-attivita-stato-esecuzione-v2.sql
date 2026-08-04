-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: allineamento lotti/attivita stato_esecuzione (changeset 20260222-01..07)
-- ------------------------------------------------------------
-- Indice test (1..15):
-- 1) Riferimenti minimi presenti
-- 2) Colonna attivita_fatturabili.stato_esecuzione presente
-- 3) attivita_fatturabili.stato_esecuzione nullable
-- 4) CHECK stato_esecuzione ammette COMPLETED e rifiuta OK
-- 5) stato_esecuzione=OK non ammesso su fatturazione_lotti_fatture
-- 6) fn_set_fatturazione_lotto_stato IN_ESECUZIONE
-- 7) Non critical -> RUNNING
-- 8) Critical -> ERRORE
-- 9) fn_set_fatturazione_lotto_stato COMPLETATO
-- 10) Non critical -> COMPLETED
-- 11) Critical resta ERRORE
-- 12) fn_resolve_lotto_utility_emittente risolve utility
-- 13) fn_resolve_lotto_utility_emittente blocca utility incoerente
-- 14) fn_resolve_stato_esecuzione: IN_ESECUZIONE -> RUNNING
-- ------------------------------------------------------------

BEGIN;
SELECT plan(14);

CREATE TEMP TABLE tmp_costanti_las AS
SELECT
  ('pgtap_las_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS test_scope,
  uuidv7() AS lock_batch_id;

CREATE TEMP TABLE tmp_refs_las AS
SELECT
  (
    SELECT m.registro_id
    FROM vendite.tipi_doc_fiscale_registri m
    JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE
    ORDER BY m.id
    LIMIT 1
  ) AS registro_id,
  (
    SELECT m.tipo_doc_fiscale_id
    FROM vendite.tipi_doc_fiscale_registri m
    JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE
    ORDER BY m.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id)
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (
    SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  (
    SELECT s.id
    FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
    ORDER BY s.id
    LIMIT 1
  ) AS stato_draft_id,
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT ba.istanza_utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS istanza_utility_id;

SELECT ok(
  (
    SELECT registro_id IS NOT NULL
       AND tipo_doc_fiscale_id IS NOT NULL
       AND billing_account_id IS NOT NULL
       AND utility_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
       AND valuta_id IS NOT NULL
       AND stato_draft_id IS NOT NULL
       AND articolo_id IS NOT NULL
       AND istanza_utility_id IS NOT NULL
    FROM tmp_refs_las
  ),
  'Riferimenti minimi presenti'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'stato_esecuzione'
  ),
  'Colonna attivita_fatturabili.stato_esecuzione presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'stato_esecuzione'
      AND c.is_nullable = 'YES'
  ),
  'attivita_fatturabili.stato_esecuzione ammessa a NULL fuori pipeline'
);

SELECT ok(
  (
    SELECT pg_get_constraintdef(c.oid) ~ '''COMPLETED'''
       AND pg_get_constraintdef(c.oid) NOT LIKE '%''OK''%'
    FROM pg_constraint c
    WHERE c.conrelid = 'vendite.attivita_fatturabili'::regclass
      AND c.conname = 'chk_attivita_fatt_stato_esecuzione'
  ),
  'CHECK stato_esecuzione ammette COMPLETED e rifiuta OK'
);

CREATE TEMP TABLE tmp_lotto_fat_las AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese => date_trunc('month', current_date)::date,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_las),
  p_utility_id => (SELECT utility_id FROM tmp_refs_las),
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_las),
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'lotto_fat'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_las)
) AS lotto_id;

CREATE TEMP TABLE tmp_fatture_las AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    stato_doc_fiscale_id,
    valuta_id,
    totale_a_pagare,
    critical,
    meta
  )
  SELECT
    (SELECT registro_id FROM tmp_refs_las),
    current_date,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_las),
    (SELECT billing_account_id FROM tmp_refs_las),
    (SELECT tipo_doc_fiscale_id FROM tmp_refs_las),
    (SELECT stato_draft_id FROM tmp_refs_las),
    (SELECT valuta_id FROM tmp_refs_las),
    10.00,
    false,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'non_critical')
  UNION ALL
  SELECT
    (SELECT registro_id FROM tmp_refs_las),
    current_date,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_las),
    (SELECT billing_account_id FROM tmp_refs_las),
    (SELECT tipo_doc_fiscale_id FROM tmp_refs_las),
    (SELECT stato_draft_id FROM tmp_refs_las),
    (SELECT valuta_id FROM tmp_refs_las),
    12.00,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'critical')
  RETURNING id, critical, stato_doc_fiscale_id
)
SELECT * FROM ins;

SELECT throws_ok(
  $$
  INSERT INTO vendite.fatturazione_lotti_fatture (
    lotto_id,
    fattura_id,
    stato_doc_fiscale_id,
    stato_esecuzione,
    meta
  )
  SELECT
    (SELECT lotto_id FROM tmp_lotto_fat_las),
    (SELECT id FROM tmp_fatture_las ORDER BY id LIMIT 1),
    (SELECT stato_draft_id FROM tmp_refs_las),
    'OK',
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'invalid_enum_lotto_fatture');
  $$,
  '23514',
  NULL,
  'stato_esecuzione=OK non ammesso su fatturazione_lotti_fatture'
);

INSERT INTO vendite.fatturazione_lotti_fatture (
  lotto_id,
  fattura_id,
  stato_doc_fiscale_id,
  stato_esecuzione,
  meta
)
SELECT
  (SELECT lotto_id FROM tmp_lotto_fat_las),
  f.id,
  f.stato_doc_fiscale_id,
  'PENDING',
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'seed_pendente')
FROM tmp_fatture_las f;

UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'COMPLETATO',
       stato_operativo = 'APERTO',
       data_update = now(),
       user_update = current_user
 WHERE id = (SELECT lotto_id FROM tmp_lotto_fat_las);

SELECT lives_ok(
  $$
  SELECT vendite.fn_set_fatturazione_lotto_stato(
    p_lotto_id => (SELECT lotto_id FROM tmp_lotto_fat_las),
    p_stato_lotto => 'IN_ESECUZIONE',
    p_note => 'pgtap in esecuzione'
  );
  $$,
  'fn_set_fatturazione_lotto_stato IN_ESECUZIONE eseguita'
);

SELECT ok(
  (
    SELECT lf.stato_esecuzione = 'RUNNING'
    FROM vendite.fatturazione_lotti_fatture lf
    JOIN tmp_fatture_las f ON f.id = lf.fattura_id
    WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_lotto_fat_las)
      AND f.critical IS FALSE
    LIMIT 1
  ),
  'Non critical -> RUNNING con lotto IN_ESECUZIONE'
);

SELECT ok(
  (
    SELECT lf.stato_esecuzione = 'ERRORE'
    FROM vendite.fatturazione_lotti_fatture lf
    JOIN tmp_fatture_las f ON f.id = lf.fattura_id
    WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_lotto_fat_las)
      AND f.critical IS TRUE
    LIMIT 1
  ),
  'Critical -> ERRORE con lotto IN_ESECUZIONE'
);

SELECT lives_ok(
  $$
  SELECT vendite.fn_set_fatturazione_lotto_stato(
    p_lotto_id => (SELECT lotto_id FROM tmp_lotto_fat_las),
    p_stato_lotto => 'COMPLETATO',
    p_note => 'pgtap completato'
  );
  $$,
  'fn_set_fatturazione_lotto_stato COMPLETATO eseguita'
);

SELECT ok(
  (
    SELECT lf.stato_esecuzione = 'COMPLETED'
    FROM vendite.fatturazione_lotti_fatture lf
    JOIN tmp_fatture_las f ON f.id = lf.fattura_id
    WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_lotto_fat_las)
      AND f.critical IS FALSE
    LIMIT 1
  ),
  'Non critical -> COMPLETED con lotto COMPLETATO'
);

SELECT ok(
  (
    SELECT lf.stato_esecuzione = 'ERRORE'
    FROM vendite.fatturazione_lotti_fatture lf
    JOIN tmp_fatture_las f ON f.id = lf.fattura_id
    WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_lotto_fat_las)
      AND f.critical IS TRUE
    LIMIT 1
  ),
  'Critical resta ERRORE con lotto COMPLETATO'
);

SELECT is(
  (
    SELECT r.resolved_utility_id
    FROM vendite.fn_resolve_lotto_utility_emittente(
      p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_las),
      p_utility_id => NULL,
      p_emittente_soggetto_ruolo_id => NULL,
      p_scope => 'TEST',
      p_caller => 'test_lotti_attivita_stato_esecuzione_v2',
      p_check_emittente_attivo => true
    ) r
  ),
  (SELECT utility_id FROM tmp_refs_las),
  'fn_resolve_lotto_utility_emittente risolve utility da BA'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_lotto_utility_emittente(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_las),
    p_utility_id => (SELECT utility_id + 99999 FROM tmp_refs_las),
    p_emittente_soggetto_ruolo_id => NULL,
    p_scope => 'TEST',
    p_caller => 'test_lotti_attivita_stato_esecuzione_v2',
    p_check_emittente_attivo => true
  );
  $$,
  'P0001',
  NULL,
  'fn_resolve_lotto_utility_emittente blocca utility incoerente con BA'
);

SELECT is(
  vendite.fn_resolve_stato_esecuzione(
    p_stato_source => 'IN_ESECUZIONE',
    p_has_critical => false,
    p_fatturato => false,
    p_default_stato_esecuzione => 'PENDING'
  ),
  'RUNNING'::varchar,
  'fn_resolve_stato_esecuzione mappa IN_ESECUZIONE -> RUNNING'
);

-- Adeguamento 2026-08-04 (D-M, changeSet 20260804-19): il test
-- «esclusa=true mantiene stato corrente» E' STATO RIMOSSO, non riscritto.
-- Verificava il primo ramo dell'helper, che con il flag `esclusa` e' stato
-- eliminato: `p_esclusa` e `p_current_stato_esecuzione` non esistono piu'
-- nella firma (da sei parametri a quattro). Non c'e' un comportamento
-- equivalente da spostare altrove — il ramo non c'e' proprio piu', quindi
-- riscrivere il test vorrebbe dire inventargli un soggetto.
-- Il plan scende da 15 a 14.

SELECT * FROM finish();
ROLLBACK;
