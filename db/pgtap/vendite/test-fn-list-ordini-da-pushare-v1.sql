-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_ordini_da_pushare + trgfn_ordini_normalize
-- ------------------------------------------------------------
-- Indice test (1..10):
-- 1) fn_list_ordini_da_pushare presente
-- 2) Riferimenti minimi disponibili
-- 3) Ordine CONFERMATO con fatturazione_trigger CONFERMATO restituito
-- 4) Segment key formato corretto (ORD:<uid>:R:<riga_id>)
-- 5) prezzo_bloccato = TRUE per ordini
-- 6) Ordine con fatturazione_trigger SPEDITO escluso
-- 7) Ordine con fatturazione_trigger CONSEGNATO escluso
-- 8) Ordine non CONFERMATO escluso
-- 9) Filtro p_billing_account_id rispettato
-- 10) trgfn_ordini_normalize eredita fatturazione_trigger da billing_account
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

-- ============================================================
-- 0) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_ordini_da_pushare'
  ),
  'fn_list_ordini_da_pushare presente'
);

-- ============================================================
-- 0b) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_ord AS
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
  (SELECT s.id
     FROM config.stati_doc_ordini s
    WHERE s.codice = 'CONFERMATO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_confermato_id,
  (SELECT s.id
     FROM config.stati_doc_ordini s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_bozza_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice = 'ORDINE_VENDITA' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_tipo_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_confermato_id IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
   FROM tmp_refs_ord),
  'Riferimenti minimi disponibili'
);

-- ============================================================
-- 1) Ordine CONFERMATO con fatturazione_trigger CONFERMATO
-- ============================================================
-- Il trigger trgfn_ordini_normalize imposta fatturazione_trigger
-- da billing_account.fatturazione_ordini (default CONFERMATO) su INSERT.
CREATE TEMP TABLE tmp_ordine AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id,
    stato_doc_ordine_id, valuta_id, data,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, r.billing_account_id,
    r.stato_confermato_id, r.valuta_id, DATE '2026-06-15',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ord')
  FROM tmp_refs_ord r
  RETURNING id, uid
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ordine_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo,
    storicizza, meta
  )
  SELECT
    o.id, 1, r.articolo_id, 'Riga test pgtap',
    10.000000, 10.000000, 25.500000, true,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ord')
  FROM tmp_ordine o, tmp_refs_ord r
  RETURNING id
)
SELECT * FROM ins;

-- Verifica che il trigger ha impostato CONFERMATO
-- (prerequisito per il test funzionale)
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT id FROM tmp_ordine)
  ),
  'Ordine CONFERMATO con fatturazione_trigger CONFERMATO restituito'
);

-- ============================================================
-- 2) Formato segment_key
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT id FROM tmp_ordine)
      AND rp.segment_key = 'ORD:' || (SELECT uid FROM tmp_ordine)::text
                           || ':R:' || (SELECT id FROM tmp_ordine_riga)::text
  ),
  'Segment key formato corretto (ORD:<uid>:R:<riga_id>)'
);

-- ============================================================
-- 3) prezzo_bloccato = TRUE
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT id FROM tmp_ordine)
      AND rp.prezzo_bloccato IS TRUE
  ),
  'prezzo_bloccato = TRUE per ordini'
);

-- ============================================================
-- 4) Ordine con fatturazione_trigger SPEDITO escluso
-- ============================================================
CREATE TEMP TABLE tmp_ordine_spedito AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id,
    stato_doc_ordine_id, valuta_id, data,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, r.billing_account_id,
    r.stato_confermato_id, r.valuta_id, DATE '2026-06-15',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ord', 'case', 'spedito')
  FROM tmp_refs_ord r
  RETURNING id, uid
)
SELECT * FROM ins;

-- Imposta fatturazione_trigger = SPEDITO via UPDATE
-- (il trigger normalize non tocca fatturazione_trigger se billing_account_id non cambia)
UPDATE vendite.ordini
SET fatturazione_trigger = 'SPEDITO'
WHERE id = (SELECT id FROM tmp_ordine_spedito);

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, attivo,
  storicizza, meta
)
SELECT
  o.id, 1, r.articolo_id, 'Riga test spedito',
  10.000000, 10.000000, 25.500000, true,
  false, jsonb_build_object('test_scope', 'pgtap_fn_list_ord', 'case', 'spedito')
FROM tmp_ordine_spedito o, tmp_refs_ord r;

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT id FROM tmp_ordine_spedito)
  ),
  'Ordine con fatturazione_trigger SPEDITO escluso'
);

-- ============================================================
-- 5) Ordine con fatturazione_trigger CONSEGNATO escluso
-- ============================================================
CREATE TEMP TABLE tmp_ordine_consegnato AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id,
    stato_doc_ordine_id, valuta_id, data,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, r.billing_account_id,
    r.stato_confermato_id, r.valuta_id, DATE '2026-06-15',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ord', 'case', 'consegnato')
  FROM tmp_refs_ord r
  RETURNING id, uid
)
SELECT * FROM ins;

UPDATE vendite.ordini
SET fatturazione_trigger = 'CONSEGNATO'
WHERE id = (SELECT id FROM tmp_ordine_consegnato);

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, attivo,
  storicizza, meta
)
SELECT
  o.id, 1, r.articolo_id, 'Riga test consegnato',
  10.000000, 10.000000, 25.500000, true,
  false, jsonb_build_object('test_scope', 'pgtap_fn_list_ord', 'case', 'consegnato')
FROM tmp_ordine_consegnato o, tmp_refs_ord r;

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT id FROM tmp_ordine_consegnato)
  ),
  'Ordine con fatturazione_trigger CONSEGNATO escluso'
);

-- ============================================================
-- 6) Ordine non CONFERMATO escluso
-- ============================================================
CREATE TEMP TABLE tmp_ordine_bozza AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id,
    stato_doc_ordine_id, valuta_id, data,
    storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, r.billing_account_id,
    COALESCE(r.stato_bozza_id, r.stato_confermato_id), r.valuta_id,
    DATE '2026-06-15',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ord', 'case', 'bozza')
  FROM tmp_refs_ord r
  RETURNING id, uid
)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, attivo,
  storicizza, meta
)
SELECT
  o.id, 1, r.articolo_id, 'Riga test bozza',
  10.000000, 10.000000, 25.500000, true,
  false, jsonb_build_object('test_scope', 'pgtap_fn_list_ord', 'case', 'bozza')
FROM tmp_ordine_bozza o, tmp_refs_ord r;

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT id FROM tmp_ordine_bozza)
  )
  OR (SELECT stato_bozza_id IS NULL FROM tmp_refs_ord),
  'Ordine non CONFERMATO escluso (o stato BOZZA non configurato)'
);

-- ============================================================
-- 7) Filtro p_billing_account_id rispettato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, -999999, NULL) rp
    WHERE rp.ordine_id = (SELECT id FROM tmp_ordine)
  ),
  'Filtro p_billing_account_id rispettato'
);

-- ============================================================
-- 8) trgfn_ordini_normalize eredita fatturazione_trigger da BA
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.ordini o
    WHERE o.id = (SELECT id FROM tmp_ordine)
      AND o.fatturazione_trigger = COALESCE(
        (SELECT ba.fatturazione_ordini
           FROM anagrafiche.billing_account ba
          WHERE ba.id = o.billing_account_id),
        'CONFERMATO'
      )
  ),
  'trgfn_ordini_normalize eredita fatturazione_trigger da billing_account'
);

SELECT * FROM finish();
ROLLBACK;
