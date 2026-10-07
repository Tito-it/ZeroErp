-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: regressione smoke 8b del refactor quantita/qta_operativa.
--       Prima del refactor un'offerta FISSA aveva qta_operativa NULL: al push
--       verso contratto il trigger contratti sollevava E_QTA_MISSING.
--       Dopo il refactor (trigger qta_from_operativa installato sull'offerta,
--       20260531-11) l'eccezione FISSA valorizza qta_operativa gia' a monte ->
--       il push copia valori coerenti e NON solleva E_QTA_MISSING.
--
-- Indice test (1..4):
--   1) fixture: offerta ACCETTATA con eccezione FISSA (qta_operativa valorizzata)
--   2) push -> NON solleva E_QTA_MISSING (lives)  [regressione 8b]
--   3) contratto DRAFT creato dall'offerta
--   4) riga contratto copiata: qta_operativa e quantita coerenti (=3)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(4);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe di
--   offerta stanno nel PERIMETRO dell'articolo, e la tipologia dell'articolo dev'essere fra
--   quelle della utility del cliente. Gli articoli si COSTRUISCONO (dbops.fn_pgtap_crea_articolo:
--   MERCE senza tipologia, ammette UNA_TANTUM): prima erano i primi per id del database,
--   che su dbdev sono PRODOTTI, e la utility del cliente preso dai dati (TEL) non li prevede.
CREATE TEMP TABLE tmp_pfq_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PFQ-1') AS a1;

CREATE TEMP TABLE tmp_pf_ctx AS
SELECT
    (SELECT ba.id FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id)
      ORDER BY ba.id LIMIT 1) AS billing_account_id,
    (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id)
      ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
    (SELECT ba.utility_id FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id)
      ORDER BY ba.id LIMIT 1) AS utility_id,
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
    (SELECT l.id FROM vendite.listini l WHERE l.attivo IS TRUE ORDER BY l.id LIMIT 1) AS listino_id,
    (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato='ATTIVA' ORDER BY lv.id LIMIT 1) AS listino_versione_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno='BOZZA') AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno='EMESSA') AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno='ACCETTATA') AS stato_accettata_id,
    (SELECT a1 FROM tmp_pfq_art) AS articolo_id;

-- Offerta in BOZZA (date lontane per non collidere con altri pgTAP/overlap)
INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, validita_al,
    stato_doc_offerta_id, meta)
SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
       ctx.listino_id, ctx.listino_versione_id, DATE '2096-01-01', DATE '2096-12-31',
       ctx.stato_bozza_id, jsonb_build_object('pgtap_pushfissa','1')
  FROM tmp_pf_ctx ctx
 WHERE ctx.billing_account_id IS NOT NULL AND ctx.stato_bozza_id IS NOT NULL
   AND ctx.articolo_id IS NOT NULL;

-- Eccezione FISSA con qta_operativa valorizzata (il trigger deriva quantita)
INSERT INTO vendite.offerte_commerciali_eccezioni
    (offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
SELECT o.id, ctx.articolo_id, 'AGGIUNTA', 'UNA_TANTUM', 'FISSA', 100, 3
  FROM vendite.offerte_commerciali o, tmp_pf_ctx ctx
 WHERE o.meta->>'pgtap_pushfissa'='1';

-- Transizioni BOZZA -> EMESSA -> ACCETTATA
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_pf_ctx)
 WHERE meta->>'pgtap_pushfissa'='1';
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_accettata_id FROM tmp_pf_ctx)
 WHERE meta->>'pgtap_pushfissa'='1';

SELECT ok(
    EXISTS(SELECT 1 FROM vendite.offerte_commerciali o
             JOIN vendite.offerte_commerciali_eccezioni e ON e.offerta_id=o.id
            WHERE o.meta->>'pgtap_pushfissa'='1'
              AND e.fonte_quantita_attesa='FISSA' AND e.qta_operativa = 3),
    '1) fixture: offerta ACCETTATA con eccezione FISSA, qta_operativa=3 valorizzata');

-- ============================================================
-- 2) push -> non solleva E_QTA_MISSING (regressione 8b)
-- ============================================================
SELECT lives_ok(
    format(
        $$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint, false)$$,
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_pushfissa'='1')
    ),
    '2) push offerta FISSA -> NON solleva E_QTA_MISSING (regressione smoke 8b)');

-- ============================================================
-- 3) contratto creato dall'offerta
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM vendite.contratti
            WHERE offerta_id = (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_pushfissa'='1')),
    '3) push -> contratto DRAFT creato dall''offerta');

-- ============================================================
-- 4) riga contratto: qta_operativa e quantita coerenti (=3)
-- ============================================================
SELECT ok(
    (SELECT cr.qta_operativa = 3 AND cr.quantita = 3
       FROM vendite.contratti_righe cr
       JOIN vendite.contratti c ON c.id = cr.contratto_id
      WHERE c.offerta_id = (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_pushfissa'='1')
      LIMIT 1),
    '4) riga contratto copiata: qta_operativa=3 e quantita=3 coerenti');

SELECT * FROM finish();
ROLLBACK;
