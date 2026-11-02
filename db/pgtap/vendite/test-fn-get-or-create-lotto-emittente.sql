-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_get_or_create_lotto (emittente fiscale)
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Creazione lotto con emittente esplicito
-- 3) Emittente valorizzato correttamente sul lotto
-- 4) Re-use stesso lotto con stesso emittente
-- 5) Re-use consentito con lotto IN_ESECUZIONE ma stato_operativo APERTO
-- 6) Guard riuso bloccato con IN_ESECUZIONE + stato_operativo CHIUSO
-- 7) Guard coerenza su emittente differente
-- 8) Guard su emittente non valido (<= 0)
-- 9) Re-use via lock_batch consentito con IN_ESECUZIONE + APERTO
-- 10) Re-use via lock_batch bloccato con IN_ESECUZIONE + CHIUSO
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

SELECT plan(10);

CREATE TEMP TABLE tmp_costanti_gocl AS
SELECT
  ('pgtap_gocl_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS'))::text AS test_scope;

CREATE TEMP TABLE tmp_refs_gocl AS
SELECT
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT u.id
    FROM config.utilities u
    ORDER BY u.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT ef.soggetto_ruolo_id
    FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id;

SELECT ok(
  (
    SELECT tipo_doc_fiscale_id IS NOT NULL
       AND utility_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
    FROM tmp_refs_gocl
  ),
  'Riferimenti minimi presenti'
);

CREATE TEMP TABLE tmp_lotto_gocl AS
SELECT vendite.fn_get_or_create_lotto(
  p_lotto_id => NULL,
  p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
  p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
  p_billing_account_id => NULL,
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl)),
  p_tipo_lotto => 'MASSIVO',
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl)
) AS lotto_id;

SELECT ok(
  (SELECT lotto_id IS NOT NULL AND lotto_id > 0 FROM tmp_lotto_gocl),
  'Creazione lotto con emittente esplicito'
);

SELECT is(
  (
    SELECT fl.emittente_soggetto_ruolo_id
    FROM vendite.fatturazione_lotti fl
    WHERE fl.id = (SELECT lotto_id FROM tmp_lotto_gocl)
  ),
  (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl),
  'Emittente valorizzato correttamente sul lotto'
);

-- Porto il lotto fuori da IN_ESECUZIONE per verificare il riuso coerente.
UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'COMPLETATO',
       data_update = now(),
       user_update = current_user
 WHERE id = (SELECT lotto_id FROM tmp_lotto_gocl);

SELECT is(
  vendite.fn_get_or_create_lotto(
    p_lotto_id => (SELECT lotto_id FROM tmp_lotto_gocl),
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
    p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
    p_billing_account_id => NULL,
    p_lock_batch_id => NULL,
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl)),
    p_tipo_lotto => 'MASSIVO',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl)
  ),
  (SELECT lotto_id FROM tmp_lotto_gocl),
  'Re-use stesso lotto con stesso emittente'
);

UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'IN_ESECUZIONE',
       stato_operativo = 'APERTO',
       data_update = now(),
       user_update = current_user
 WHERE id = (SELECT lotto_id FROM tmp_lotto_gocl);

SELECT is(
  vendite.fn_get_or_create_lotto(
    p_lotto_id => (SELECT lotto_id FROM tmp_lotto_gocl),
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
    p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
    p_billing_account_id => NULL,
    p_lock_batch_id => NULL,
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl)),
    p_tipo_lotto => 'MASSIVO',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl)
  ),
  (SELECT lotto_id FROM tmp_lotto_gocl),
  'Re-use consentito con lotto IN_ESECUZIONE ma stato_operativo APERTO'
);

UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'IN_ESECUZIONE',
       stato_operativo = 'CHIUSO',
       data_update = now(),
       user_update = current_user
 WHERE id = (SELECT lotto_id FROM tmp_lotto_gocl);

SELECT throws_ok(
  $$
  SELECT vendite.fn_get_or_create_lotto(
    p_lotto_id => (SELECT lotto_id FROM tmp_lotto_gocl),
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
    p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
    p_billing_account_id => NULL,
    p_lock_batch_id => NULL,
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl)),
    p_tipo_lotto => 'MASSIVO',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl)
  );
  $$,
  'P0001',
  NULL,
  'Guard riuso bloccato con IN_ESECUZIONE + stato_operativo CHIUSO'
);

UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'COMPLETATO',
       stato_operativo = 'APERTO',
       data_update = now(),
       user_update = current_user
 WHERE id = (SELECT lotto_id FROM tmp_lotto_gocl);

SELECT throws_ok(
  $$
  SELECT vendite.fn_get_or_create_lotto(
    p_lotto_id => (SELECT lotto_id FROM tmp_lotto_gocl),
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
    p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
    p_billing_account_id => NULL,
    p_lock_batch_id => NULL,
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl)),
    p_tipo_lotto => 'MASSIVO',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl) + 999999
  );
  $$,
  'P0001',
  NULL,
  'Guard coerenza su emittente differente'
);

SELECT throws_ok(
  $$
  SELECT vendite.fn_get_or_create_lotto(
    p_lotto_id => NULL,
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
    p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
    p_billing_account_id => NULL,
    p_lock_batch_id => NULL,
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl)),
    p_tipo_lotto => 'MASSIVO',
    p_emittente_soggetto_ruolo_id => 0
  );
  $$,
  'P0001',
  NULL,
  'Guard su emittente non valido (<= 0)'
);

-- ============================================================
-- 9-10) Ramo lock_batch_id con doppia condizione stato
-- ============================================================
CREATE TEMP TABLE tmp_lock_batch_gocl AS
SELECT uuidv7() AS lock_batch_id;

CREATE TEMP TABLE tmp_lotto_lock_gocl AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
  p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
  p_billing_account_id => NULL,
  p_lock_batch_id => (SELECT lock_batch_id FROM tmp_lock_batch_gocl),
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl), 'branch', 'lock_batch'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl)
) AS lotto_id;

UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'IN_ESECUZIONE',
       stato_operativo = 'APERTO',
       data_update = now(),
       user_update = current_user
 WHERE id = (SELECT lotto_id FROM tmp_lotto_lock_gocl);

SELECT is(
  vendite.fn_get_or_create_lotto(
    p_lotto_id => NULL,
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
    p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
    p_billing_account_id => NULL,
    p_lock_batch_id => (SELECT lock_batch_id FROM tmp_lock_batch_gocl),
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl)),
    p_tipo_lotto => 'MASSIVO',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl)
  ),
  (SELECT lotto_id FROM tmp_lotto_lock_gocl),
  'Re-use via lock_batch consentito con IN_ESECUZIONE + APERTO'
);

UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'IN_ESECUZIONE',
       stato_operativo = 'CHIUSO',
       data_update = now(),
       user_update = current_user
 WHERE id = (SELECT lotto_id FROM tmp_lotto_lock_gocl);

SELECT throws_ok(
  $$
  SELECT vendite.fn_get_or_create_lotto(
    p_lotto_id => NULL,
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_gocl),
    p_utility_id => (SELECT utility_id FROM tmp_refs_gocl),
    p_billing_account_id => NULL,
    p_lock_batch_id => (SELECT lock_batch_id FROM tmp_lock_batch_gocl),
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_gocl)),
    p_tipo_lotto => 'MASSIVO',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_gocl)
  );
  $$,
  'P0001',
  NULL,
  'Re-use via lock_batch bloccato con IN_ESECUZIONE + CHIUSO'
);

SELECT * FROM finish();

ROLLBACK;
