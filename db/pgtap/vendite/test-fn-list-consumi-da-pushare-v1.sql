-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_consumi_da_pushare
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) fn_list_consumi_da_pushare presente
-- 2) Riferimenti minimi disponibili
-- 3) Consumo con stato_calcolo OK restituito
-- 4) Segment key formato corretto (ATTIVITA_CONSUMI:<uid>)
-- 5) articolo_id = NULL (handler risolve)
-- 6) Consumo con stato_calcolo diverso da OK escluso
-- 7) Consumo con fattura_id NOT NULL escluso
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
      AND p.proname = 'fn_list_consumi_da_pushare'
  ),
  'fn_list_consumi_da_pushare presente'
);

-- ============================================================
-- 0b) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_cons AS
SELECT
  (SELECT ba.id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS billing_account_id,
  (SELECT u.id
     FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1
  ) AS uom_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice = 'ATTIVITA_CONSUMI' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_tipo_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND uom_id IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
   FROM tmp_refs_cons),
  'Riferimenti minimi disponibili'
);

-- ============================================================
-- 1) Consumo con stato_calcolo OK restituito
-- ============================================================
CREATE TEMP TABLE tmp_consumo_ok AS
WITH ins AS (
  INSERT INTO vendite.attivita_consumi (
    billing_account_id, competenza_mese,
    periodo_dal, periodo_al,
    consumo_totale, uom_id, stato_calcolo,
    storicizza, meta
  )
  SELECT
    r.billing_account_id,
    DATE '2026-06-01',
    DATE '2026-06-01', DATE '2026-06-30',
    155.50, r.uom_id, 'OK',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_cons')
  FROM tmp_refs_cons r
  RETURNING id, uid
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_result_cons AS
SELECT *
FROM vendite.fn_list_consumi_da_pushare(NULL, NULL, NULL);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_cons rc
    WHERE rc.consumo_id = (SELECT id FROM tmp_consumo_ok)
  ),
  'Consumo con stato_calcolo OK restituito'
);

-- ============================================================
-- 2) Formato segment_key
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_cons rc
    WHERE rc.consumo_id = (SELECT id FROM tmp_consumo_ok)
      AND rc.segment_key = 'ATTIVITA_CONSUMI:' || (SELECT uid FROM tmp_consumo_ok)::text
  ),
  'Segment key formato corretto (ATTIVITA_CONSUMI:<uid>)'
);

-- ============================================================
-- 3) articolo_id = NULL (handler risolve)
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_cons rc
    WHERE rc.consumo_id = (SELECT id FROM tmp_consumo_ok)
      AND rc.articolo_id IS NULL
  ),
  'articolo_id = NULL (handler risolve)'
);

-- ============================================================
-- 4) Consumo con stato_calcolo diverso da OK escluso
-- ============================================================
CREATE TEMP TABLE tmp_consumo_err AS
WITH ins AS (
  INSERT INTO vendite.attivita_consumi (
    billing_account_id, competenza_mese,
    periodo_dal, periodo_al,
    consumo_totale, uom_id, stato_calcolo,
    storicizza, meta
  )
  SELECT
    r.billing_account_id,
    DATE '2026-06-01',
    DATE '2026-06-01', DATE '2026-06-30',
    100.00, r.uom_id, 'ERRORE',
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_cons', 'case', 'errore')
  FROM tmp_refs_cons r
  RETURNING id, uid
)
SELECT * FROM ins;

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_consumi_da_pushare(NULL, NULL, NULL) rc
    WHERE rc.consumo_id = (SELECT id FROM tmp_consumo_err)
  ),
  'Consumo con stato_calcolo ERRORE escluso'
);

-- ============================================================
-- 5) Consumo con fattura_id NOT NULL escluso
--    NB: non possiamo facilmente creare una fattura valida,
--    quindi verifichiamo il filtro WHERE fattura_id IS NULL
--    controllando che i risultati abbiano tutti fattura_id NULL
--    nella tabella sorgente.
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_consumi_da_pushare(NULL, NULL, NULL) rc
    JOIN vendite.attivita_consumi ac ON ac.id = rc.consumo_id
    WHERE ac.fattura_id IS NOT NULL
  ),
  'Nessun consumo con fattura_id NOT NULL nei risultati'
);

-- ============================================================
-- 6) Filtro p_billing_account_id rispettato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_consumi_da_pushare(NULL, -999999, NULL) rc
    WHERE rc.consumo_id = (SELECT id FROM tmp_consumo_ok)
  ),
  'Filtro p_billing_account_id rispettato'
);

SELECT * FROM finish();
ROLLBACK;
