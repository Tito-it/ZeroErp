-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_contratti_da_pushare
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) fn_list_contratti_da_pushare presente
-- 2) Riferimenti minimi disponibili
-- 3) Contratto ATTIVO in validita restituito
-- 4) Segment key include competenza_mese (CONTR:<uid>:R:<id>:M:<YYYY-MM>)
-- 5) tipo_consumo = CANONE default (quando tipo_erogazione NULL)
-- 6) prezzo_bloccato = TRUE quando prezzo_unitario presente
-- 7) Contratto non ATTIVO escluso
-- 8) Filtro p_billing_account_id rispettato
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

SELECT plan(8);

-- ============================================================
-- 0) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_contratti_da_pushare'
  ),
  'fn_list_contratti_da_pushare presente'
);

-- ============================================================
-- 0b) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_contr AS
SELECT
  (SELECT ba.id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS billing_account_id,
  (SELECT ba.utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS utility_id,
  (SELECT ba.istanza_utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS istanza_utility_id,
  (SELECT a.id
     FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1
  ) AS articolo_id,
  (SELECT s.id
     FROM config.stati_doc_contratti s
    WHERE s.codice = 'ATTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_attivo_id,
  (SELECT s.id
     FROM config.stati_doc_contratti s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_draft_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice = 'CONTRATTO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_tipo_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND istanza_utility_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_attivo_id IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
   FROM tmp_refs_contr),
  'Riferimenti minimi disponibili'
);

-- ============================================================
-- 1) Contratto ATTIVO in validita restituito
-- ============================================================
CREATE TEMP TABLE tmp_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id,
    utility_id, valido_dal, valido_al,
    stato_doc_contratto_id, data, meta
  )
  SELECT
    'PGTAP-CONTR-' || substr(md5(clock_timestamp()::text), 1, 8),
    r.billing_account_id, r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01', DATE '2026-12-31',
    r.stato_attivo_id, DATE '2026-06-01',
    jsonb_build_object('test_scope', 'pgtap_fn_list_contr')
  FROM tmp_refs_contr r
  RETURNING id, uid, valido_dal, data
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_contratto_riga AS
WITH ins AS (
  INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, prezzo_unitario,
    qta_operativa, quantita_fissa, attivo, meta
  )
  SELECT
    c.id, r.articolo_id, 50.000000,
    1.000000, 1.000000, true,
    jsonb_build_object('test_scope', 'pgtap_fn_list_contr')
  FROM tmp_contratto c, tmp_refs_contr r
  RETURNING id
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_result_contr AS
SELECT *
FROM vendite.fn_list_contratti_da_pushare(NULL, NULL, NULL);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_contr rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
  ),
  'Contratto ATTIVO in validita restituito'
);

-- ============================================================
-- 2) Segment key include competenza_mese
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_contr rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
      AND rc.segment_key = 'CONTR:' || (SELECT uid FROM tmp_contratto)::text
                            || ':R:' || (SELECT id FROM tmp_contratto_riga)::text
                            || ':M:' || to_char(
                                date_trunc('month',
                                  COALESCE(
                                    (SELECT valido_dal FROM tmp_contratto),
                                    (SELECT data FROM tmp_contratto)
                                  )
                                )::date,
                                'YYYY-MM'
                              )
  ),
  'Segment key include competenza_mese (CONTR:<uid>:R:<id>:M:<YYYY-MM>)'
);

-- ============================================================
-- 3) tipo_consumo = CANONE default (tipo_erogazione NULL)
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_contr rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
      AND rc.tipo_consumo = 'CANONE'
  ),
  'tipo_consumo = CANONE default (quando tipo_erogazione NULL)'
);

-- ============================================================
-- 4) prezzo_bloccato = TRUE quando prezzo_unitario presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_contr rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
      AND rc.prezzo_bloccato IS TRUE
      AND rc.prezzo_snapshot IS NOT NULL
  ),
  'prezzo_bloccato = TRUE quando prezzo_unitario presente'
);

-- ============================================================
-- 5) Contratto non ATTIVO escluso
-- ============================================================
CREATE TEMP TABLE tmp_contratto_draft AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id,
    utility_id, valido_dal, valido_al,
    stato_doc_contratto_id, data, meta
  )
  SELECT
    'PGTAP-CONTR-D-' || substr(md5(clock_timestamp()::text), 1, 8),
    r.billing_account_id, r.istanza_utility_id,
    r.utility_id,
    DATE '2027-01-01', DATE '2027-06-30',
    COALESCE(r.stato_draft_id, r.stato_attivo_id), DATE '2027-01-01',
    jsonb_build_object('test_scope', 'pgtap_fn_list_contr', 'case', 'draft')
  FROM tmp_refs_contr r
  RETURNING id, uid
)
SELECT * FROM ins;

INSERT INTO vendite.contratti_righe (
  contratto_id, articolo_id, prezzo_unitario,
  qta_operativa, quantita_fissa, attivo, meta
)
SELECT
  c.id, r.articolo_id, 30.000000,
  1.000000, 1.000000, true,
  jsonb_build_object('test_scope', 'pgtap_fn_list_contr', 'case', 'draft')
FROM tmp_contratto_draft c, tmp_refs_contr r;

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_contratti_da_pushare(NULL, NULL, NULL) rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto_draft)
  )
  OR (SELECT stato_draft_id IS NULL FROM tmp_refs_contr),
  'Contratto non ATTIVO escluso (o stato DRAFT non configurato)'
);

-- ============================================================
-- 6) Filtro p_billing_account_id rispettato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_contratti_da_pushare(NULL, -999999, NULL) rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
  ),
  'Filtro p_billing_account_id rispettato'
);

SELECT * FROM finish();
ROLLBACK;
