-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_list_preventivi_da_pushare con p_righe_ids
--       (20260612-06): push commessa per sottoinsieme righe,
--       simmetrico al ramo ordine. Brief:
--       brief-db-smistamento-preventivi.md, Richiesta C.
--
-- Indice test (0..5):
--   0) Precondizioni (refs + nature)
--   1) p_righe_ids=[A] -> solo la riga A
--   2) p_righe_ids=[A, merce] -> solo A (skip silenzioso riga non eleggibile)
--   3) p_righe_ids senza p_preventivo_id -> throws (E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO)
--   4) p_righe_ids NULL -> comportamento invariato (tutte le eleggibili: A+B)
--   5) p_righe_ids=[B] con B gia' EMESSA -> lista vuota (skip silenzioso)
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

SELECT plan(6);

-- ============================================================
-- 0) Riferimenti minimi + classificazione nature
-- ============================================================
CREATE TEMP TABLE tmp_ri_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1 OFFSET 0) AS art_merce_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1 OFFSET 1) AS art_serv_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE) AS stato_bozza_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT sc.id FROM vendite.stati_commessa sc WHERE sc.attivo IS TRUE
    ORDER BY sc.id LIMIT 1) AS stato_commessa_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND art_merce_id IS NOT NULL
      AND art_serv_id IS NOT NULL AND stato_accettato_id IS NOT NULL
      AND natura_merce_id IS NOT NULL AND natura_serv_id IS NOT NULL
     FROM tmp_ri_refs),
  '0. Precondizioni soddisfatte'
);

UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_ri_refs)
 WHERE id = (SELECT art_merce_id FROM tmp_ri_refs);
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_serv_id FROM tmp_ri_refs)
 WHERE id = (SELECT art_serv_id FROM tmp_ri_refs);

-- Preventivo ACCETTATO: servizio A + servizio B + merce.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende le tre righe, poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_ri_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-RIGHE-IDS', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_list_righe_ids'), r.emittente_fiscale_id
    FROM tmp_ri_refs r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ri_riga_a AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 1.000000, 10.000000, r.iva_id, true
    FROM tmp_ri_prev p, tmp_ri_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ri_riga_b AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 20.000000, r.iva_id, true
    FROM tmp_ri_prev p, tmp_ri_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ri_riga_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
    FROM tmp_ri_prev p, tmp_ri_refs r
  RETURNING id)
SELECT * FROM ins;

DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ri_prev), 'ACCETTATO'); END $porta$;

-- ============================================================
-- 1) p_righe_ids=[A] -> solo la riga A
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1 AND bool_and(f.riga_id = (SELECT id FROM tmp_ri_riga_a))
     FROM vendite.fn_list_preventivi_da_pushare(
            NULL, NULL, NULL,
            (SELECT id FROM tmp_ri_prev),
            ARRAY[(SELECT id FROM tmp_ri_riga_a)]) f),
  '1. Sottoinsieme [A]: ritorna solo la riga A'
);

-- ============================================================
-- 2) p_righe_ids=[A, merce] -> solo A (skip silenzioso non eleggibile)
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1 AND bool_and(f.riga_id = (SELECT id FROM tmp_ri_riga_a))
     FROM vendite.fn_list_preventivi_da_pushare(
            NULL, NULL, NULL,
            (SELECT id FROM tmp_ri_prev),
            ARRAY[(SELECT id FROM tmp_ri_riga_a), (SELECT id FROM tmp_ri_riga_merce)]) f),
  '2. Sottoinsieme [A, merce]: la merce e'' skippata in silenzio (D5), torna solo A'
);

-- ============================================================
-- 3) p_righe_ids senza p_preventivo_id -> throws
-- ============================================================
SELECT throws_ok(
  format('SELECT * FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, NULL, ARRAY[%s]::bigint[])',
         (SELECT id FROM tmp_ri_riga_a)),
  NULL, NULL,
  '3. p_righe_ids senza p_preventivo_id rifiutato (E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO)'
);

-- ============================================================
-- 4) p_righe_ids NULL -> invariato (tutte le eleggibili: A+B)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.fn_list_preventivi_da_pushare(
            NULL, NULL, NULL, (SELECT id FROM tmp_ri_prev)) f),
  2,
  '4. p_righe_ids NULL: comportamento invariato (A+B eleggibili, merce esclusa)'
);

-- ============================================================
-- 5) p_righe_ids=[B] con B gia' EMESSA -> lista vuota
-- ============================================================
CREATE TEMP TABLE tmp_ri_commessa AS
WITH ins AS (
  -- ⚠️ L'emittente NON si omette: vedi la nota in
  -- test-drop-uq-commesse-attivita-src-uid-partial-v1 — con la RLS attiva
  -- la policy rls_commesse_ef_whitelist respinge l'SR NULL (fail-closed).
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id, stato_commessa_id,
                                emittente_soggetto_ruolo_id)
  SELECT 'PGTAP-RI-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.stato_commessa_id,
         script.fn_pgtap_emittente_sr_operatore()
    FROM tmp_ri_refs r
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid
)
SELECT
  (SELECT id FROM tmp_ri_commessa),
  'PREVENTIVO:' || (SELECT uid FROM tmp_ri_prev)::text || ':R:' || (SELECT id FROM tmp_ri_riga_b)::text,
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 2,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31',
  r.tipo_doc_fiscale_id, r.valuta_id, 20.000000,
  'FIXED', 'BOZZA', 'EMESSA',
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1),
  (SELECT uid FROM tmp_ri_prev)::text
FROM tmp_ri_refs r;

SELECT is(
  (SELECT count(*)::integer
     FROM vendite.fn_list_preventivi_da_pushare(
            NULL, NULL, NULL,
            (SELECT id FROM tmp_ri_prev),
            ARRAY[(SELECT id FROM tmp_ri_riga_b)]) f),
  0,
  '5. Sottoinsieme [B] con B gia'' EMESSA: lista vuota (skip silenzioso, idempotenza a monte)'
);

SELECT * FROM finish();
ROLLBACK;
