-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_ddt_da_pushare (Caso A: da ordine, Caso B: autonomo)
--       + trgfn_ddt_normalize (ereditarieta` billing fields)
-- ------------------------------------------------------------
-- Indice test (1..12):
-- 1) fn_list_ddt_da_pushare presente
-- 2) Riferimenti minimi disponibili
-- 3) Caso A: DDT da ordine (trigger SPEDITO, DDT SPEDITO) restituito
-- 4) Caso A: billing_account ereditato da ordine sorgente
-- 5) Caso A: prezzo ereditato da ordine riga via fulfillment
-- 6) Caso A: DDT da ordine con trigger CONFERMATO escluso
-- 7) Caso B: DDT autonomo SPEDITO con billing_account restituito
-- 8) Caso B: prezzo da ddt_righe.prezzo_unitario
-- 9) Caso B: DDT autonomo senza billing_account escluso
-- 10) Segment key formato corretto (DDT:<uid>:R:<riga_id>)
-- 11) prezzo_bloccato = TRUE se prezzo presente
-- 12) Filtro p_billing_account_id rispettato
-- ------------------------------------------------------------

BEGIN;
SELECT plan(12);

-- ============================================================
-- 0) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_ddt_da_pushare'
  ),
  'fn_list_ddt_da_pushare presente'
);

-- ============================================================
-- 0b) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_ddt AS
SELECT
  (SELECT ba.id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS billing_account_id,
  (SELECT sr.id
     FROM anagrafiche.soggetti_ruoli sr
    ORDER BY sr.id LIMIT 1
  ) AS soggetto_ruolo_id,
  (SELECT a.id
     FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1
  ) AS articolo_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  -- Stato ordine
  (SELECT s.id
     FROM config.stati_doc_ordini s
    WHERE s.codice = 'CONFERMATO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_ordine_confermato_id,
  -- Stati DDT
  (SELECT s.id
     FROM config.stati_doc_ddt s
    WHERE s.codice = 'SPEDITO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_ddt_spedito_id,
  (SELECT s.id
     FROM config.stati_doc_ddt s
    WHERE s.codice = 'CONSEGNATO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_ddt_consegnato_id,
  (SELECT s.id
     FROM config.stati_doc_ddt s
    WHERE s.codice = 'EMESSO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_ddt_emesso_id,
  -- Sorgenti
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice = 'DDT_VENDITA' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_ddt_tipo_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice = 'ORDINE_VENDITA' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_ordine_tipo_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_ordine_confermato_id IS NOT NULL
      AND stato_ddt_spedito_id IS NOT NULL
      AND sorgente_ddt_tipo_id IS NOT NULL
   FROM tmp_refs_ddt),
  'Riferimenti minimi disponibili'
);

-- ============================================================
-- Caso A: Setup ordine + DDT + fulfillment
--   Ordine con fatturazione_trigger = SPEDITO
--   DDT con stato SPEDITO, collegato via fulfillment
-- ============================================================

-- 1. Crea ordine
CREATE TEMP TABLE tmp_ordine_a AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id,
    stato_doc_ordine_id, valuta_id, data,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, r.billing_account_id,
    r.stato_ordine_confermato_id, r.valuta_id, DATE '2026-07-01',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt')
  FROM tmp_refs_ddt r
  RETURNING id, uid, billing_account_id
)
SELECT * FROM ins;

-- Imposta fatturazione_trigger = SPEDITO
-- (il trigger normalize non cambia se billing_account_id non cambia)
UPDATE vendite.ordini
SET fatturazione_trigger = 'SPEDITO'
WHERE id = (SELECT id FROM tmp_ordine_a);

-- 2. Crea riga ordine con prezzo
CREATE TEMP TABLE tmp_ordine_a_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo,
    storicizza, meta
  )
  SELECT
    o.id, 1, r.articolo_id, 'Riga test DDT caso A',
    10.000000, 10.000000, 30.000000, true,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt')
  FROM tmp_ordine_a o, tmp_refs_ddt r
  RETURNING id
)
SELECT * FROM ins;

-- 3. Crea DDT con stato SPEDITO (senza billing_account proprio)
CREATE TEMP TABLE tmp_ddt_a AS
WITH ins AS (
  INSERT INTO vendite.ddt (
    destinatario_soggetto_ruolo_id,
    stato_doc_ddt_id, data,
    sorgente_tipo_id, sorgente_uid,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id,
    r.stato_ddt_spedito_id, DATE '2026-07-05',
    r.sorgente_ordine_tipo_id,
    (SELECT uid FROM tmp_ordine_a),
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt')
  FROM tmp_refs_ddt r
  RETURNING id, uid, billing_account_id
)
SELECT * FROM ins;

-- 4. Crea riga DDT (senza prezzo; sara` ereditato da ordine riga)
CREATE TEMP TABLE tmp_ddt_a_riga AS
WITH ins AS (
  INSERT INTO vendite.ddt_righe (
    ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, attivo,
    storicizza, meta
  )
  SELECT
    d.id, 1, r.articolo_id, 'Riga DDT test caso A',
    10.000000, 10.000000, true,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt')
  FROM tmp_ddt_a d, tmp_refs_ddt r
  RETURNING id
)
SELECT * FROM ins;

-- 5. Crea fulfillment (collega riga ordine a riga DDT)
INSERT INTO vendite.ordini_righe_fulfillment (
  ordine_riga_id, ddt_riga_id, qta_evasa,
  storicizza, meta
)
SELECT
  (SELECT id FROM tmp_ordine_a_riga),
  (SELECT id FROM tmp_ddt_a_riga),
  10.000000,
  false,
  jsonb_build_object('test_scope', 'pgtap_fn_list_ddt');

-- ============================================================
-- Test 3: Caso A restituito
-- ============================================================
CREATE TEMP TABLE tmp_result_ddt AS
SELECT *
FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_ddt rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_a)
  ),
  'Caso A: DDT da ordine (trigger SPEDITO, DDT SPEDITO) restituito'
);

-- ============================================================
-- Test 4: billing_account ereditato da ordine
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_ddt rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_a)
      AND rd.billing_account_id = (SELECT billing_account_id FROM tmp_ordine_a)
  ),
  'Caso A: billing_account ereditato da ordine sorgente'
);

-- ============================================================
-- Test 5: prezzo ereditato da ordine riga via fulfillment
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_ddt rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_a)
      AND rd.prezzo_snapshot = 30.000000
  ),
  'Caso A: prezzo ereditato da ordine riga via fulfillment'
);

-- ============================================================
-- Test 6: DDT da ordine con fatturazione_trigger=CONFERMATO escluso
--   Creo un altro ordine con trigger CONFERMATO e DDT collegato.
--   L'ordine pusha su conferma, il DDT non deve pushare.
-- ============================================================
CREATE TEMP TABLE tmp_ordine_conf AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id,
    stato_doc_ordine_id, valuta_id, data,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, r.billing_account_id,
    r.stato_ordine_confermato_id, r.valuta_id, DATE '2026-07-01',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'conf')
  FROM tmp_refs_ddt r
  RETURNING id, uid
)
SELECT * FROM ins;
-- fatturazione_trigger rimane CONFERMATO (default da BA)

CREATE TEMP TABLE tmp_ordine_conf_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo,
    storicizza, meta
  )
  SELECT
    o.id, 1, r.articolo_id, 'Riga ordine test conf',
    5.000000, 5.000000, 20.000000, true,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'conf')
  FROM tmp_ordine_conf o, tmp_refs_ddt r
  RETURNING id
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ddt_conf AS
WITH ins AS (
  INSERT INTO vendite.ddt (
    destinatario_soggetto_ruolo_id,
    stato_doc_ddt_id, data,
    sorgente_tipo_id, sorgente_uid,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id,
    r.stato_ddt_spedito_id, DATE '2026-07-10',
    r.sorgente_ordine_tipo_id,
    (SELECT uid FROM tmp_ordine_conf),
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'conf')
  FROM tmp_refs_ddt r
  RETURNING id, uid
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ddt_conf_riga AS
WITH ins AS (
  INSERT INTO vendite.ddt_righe (
    ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, attivo,
    storicizza, meta
  )
  SELECT
    d.id, 1, r.articolo_id, 'Riga DDT conf',
    5.000000, 5.000000, true,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'conf')
  FROM tmp_ddt_conf d, tmp_refs_ddt r
  RETURNING id
)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe_fulfillment (
  ordine_riga_id, ddt_riga_id, qta_evasa,
  storicizza, meta
)
SELECT
  (SELECT id FROM tmp_ordine_conf_riga),
  (SELECT id FROM tmp_ddt_conf_riga),
  5.000000,
  false,
  jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'conf');

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_conf)
  ),
  'Caso A: DDT da ordine con fatturazione_trigger CONFERMATO escluso'
);

-- ============================================================
-- Caso B: DDT autonomo
-- ============================================================

-- DDT autonomo con billing_account_id e stato SPEDITO
CREATE TEMP TABLE tmp_ddt_b AS
WITH ins AS (
  INSERT INTO vendite.ddt (
    destinatario_soggetto_ruolo_id,
    stato_doc_ddt_id, data,
    billing_account_id, valuta_id,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id,
    r.stato_ddt_spedito_id, DATE '2026-07-15',
    r.billing_account_id, r.valuta_id,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'autonomo')
  FROM tmp_refs_ddt r
  RETURNING id, uid
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ddt_b_riga AS
WITH ins AS (
  INSERT INTO vendite.ddt_righe (
    ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo,
    storicizza, meta
  )
  SELECT
    d.id, 1, r.articolo_id, 'Riga DDT autonomo',
    8.000000, 8.000000, 45.000000, true,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'autonomo')
  FROM tmp_ddt_b d, tmp_refs_ddt r
  RETURNING id
)
SELECT * FROM ins;

-- ============================================================
-- Test 7: Caso B restituito
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_b)
  ),
  'Caso B: DDT autonomo SPEDITO con billing_account restituito'
);

-- ============================================================
-- Test 8: prezzo da ddt_righe.prezzo_unitario
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_b)
      AND rd.prezzo_snapshot = 45.000000
  ),
  'Caso B: prezzo da ddt_righe.prezzo_unitario'
);

-- ============================================================
-- Test 9: DDT autonomo senza billing_account escluso
-- ============================================================
CREATE TEMP TABLE tmp_ddt_no_ba AS
WITH ins AS (
  INSERT INTO vendite.ddt (
    destinatario_soggetto_ruolo_id,
    stato_doc_ddt_id, data,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id,
    r.stato_ddt_spedito_id, DATE '2026-07-20',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'no_ba')
  FROM tmp_refs_ddt r
  RETURNING id, uid
)
SELECT * FROM ins;

INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, attivo,
  storicizza, meta
)
SELECT
  d.id, 1, r.articolo_id, 'Riga DDT senza BA',
  3.000000, 3.000000, true,
  false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'no_ba')
FROM tmp_ddt_no_ba d, tmp_refs_ddt r;

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_no_ba)
  ),
  'Caso B: DDT autonomo senza billing_account escluso'
);

-- ============================================================
-- Test 10: Segment key formato corretto
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_b)
      AND rd.segment_key = 'DDT:' || (SELECT uid FROM tmp_ddt_b)::text
                            || ':R:' || (SELECT id FROM tmp_ddt_b_riga)::text
  ),
  'Segment key formato corretto (DDT:<uid>:R:<riga_id>)'
);

-- ============================================================
-- Test 11: prezzo_bloccato = TRUE se prezzo presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_b)
      AND rd.prezzo_bloccato IS TRUE
      AND rd.prezzo_snapshot IS NOT NULL
  ),
  'prezzo_bloccato = TRUE se prezzo presente'
);

-- ============================================================
-- Test 12: Filtro p_billing_account_id rispettato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, -999999, NULL) rd
    WHERE rd.ddt_id IN (
      (SELECT id FROM tmp_ddt_a),
      (SELECT id FROM tmp_ddt_b)
    )
  ),
  'Filtro p_billing_account_id rispettato'
);

SELECT * FROM finish();
ROLLBACK;
