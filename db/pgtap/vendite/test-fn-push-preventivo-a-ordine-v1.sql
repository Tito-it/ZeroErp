-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_push_preventivo_a_ordine (20260609-06) — ramo ORDINE dello
--       split preventivo (brief-preventivi-ordini.md D8). Copia le righe di
--       natura MERCE (destinazione ORDINE) verso un nuovo ordine DRAFT con
--       documento_origine=(PREVENTIVO, id), snapshot prezzi, idempotenza di
--       riga via ordini_righe.preventivo_riga_id.
--
-- Scope test: righe NON composite (il ramo BoM compositi via
-- fn_ordine_riga_componenti_init e' coperto altrove).
--
-- Indice test (1..6):
--   1) la funzione esiste con 4 parametri
--   2) push preventivo ACCETTATO -> ammesso (lives)
--   3) creato un ordine con documento_origine=(PREVENTIVO, id)
--   4) la riga ordine e' collegata alla riga preventivo (preventivo_riga_id)
--   5) idempotenza: secondo push stesse righe -> E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE
--   6) preventivo non ACCETTATO (DRAFT) -> E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

-- ============================================================
-- 1) Firma funzione: 4 parametri
-- ============================================================
SELECT ok(
  (SELECT p.pronargs = 4
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_push_preventivo_a_ordine'
    LIMIT 1),
  '1) vendite.fn_push_preventivo_a_ordine esiste con 4 parametri'
);

-- ============================================================
-- Fixture: riferimenti + articolo MERCE non composito
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE
    ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1) AS stato_draft_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id;

-- Articolo classificato MERCE (destinazione ORDINE) per il test.
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_refs)
 WHERE id = (SELECT articolo_id FROM tmp_refs);

-- Preventivo ACCETTATO + 1 riga MERCE.
CREATE TEMP TABLE tmp_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-PUSHORD', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_push_ordine'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id, uid
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_riga AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo, meta)
  SELECT p.id, r.articolo_id, 4.000000, 25.500000, r.iva_id, true,
         jsonb_build_object('test_scope','pgtap_push_ordine')
    FROM tmp_prev p, tmp_refs r
  RETURNING id
)
SELECT * FROM ins;

-- Preventivo DRAFT (per test 6).
CREATE TEMP TABLE tmp_prev_draft AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-PUSHORD-DRAFT', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_draft_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_push_ordine_draft'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id
)
SELECT * FROM ins;

-- ============================================================
-- 2) Push preventivo ACCETTATO -> ammesso
-- ============================================================
SELECT lives_ok(
  format('SELECT vendite.fn_push_preventivo_a_ordine(%s)',
         (SELECT id FROM tmp_prev)),
  '2) push preventivo ACCETTATO -> ammesso'
);

-- ============================================================
-- 3) Ordine creato con documento_origine = (PREVENTIVO, id)
-- ============================================================
SELECT ok(
  EXISTS(SELECT 1 FROM vendite.ordini o
          WHERE o.documento_origine_tipo = 'PREVENTIVO'
            AND o.documento_origine_id = (SELECT id FROM tmp_prev)),
  '3) creato ordine con documento_origine=(PREVENTIVO, id)'
);

-- ============================================================
-- 4) La riga ordine e' collegata alla riga preventivo
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.ordini_righe orr
    WHERE orr.preventivo_riga_id = (SELECT id FROM tmp_riga)),
  1::bigint,
  '4) riga ordine collegata alla riga preventivo (preventivo_riga_id)'
);

-- ============================================================
-- 5) Idempotenza: secondo push -> nessuna riga residua
-- ============================================================
SELECT throws_like(
  format('SELECT vendite.fn_push_preventivo_a_ordine(%s)',
         (SELECT id FROM tmp_prev)),
  '%nessuna riga merce%',
  '5) secondo push (righe gia'' allocate) -> E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE'
);

-- ============================================================
-- 6) Preventivo non ACCETTATO (DRAFT) -> stato non ammesso
-- ============================================================
SELECT throws_like(
  format('SELECT vendite.fn_push_preventivo_a_ordine(%s)',
         (SELECT id FROM tmp_prev_draft)),
  '%ACCETTATO%',
  '6) preventivo DRAFT -> E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO'
);

SELECT * FROM finish();
ROLLBACK;
