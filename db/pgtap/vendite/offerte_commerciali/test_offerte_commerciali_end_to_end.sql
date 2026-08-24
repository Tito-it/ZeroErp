-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test integrativo end-to-end: dominio offerte_commerciali (Step 9).
--       Verifica i tre flussi principali del dominio:
--         A) BOZZA -> EMESSA -> ACCETTATA -> push -> contratto DRAFT
--         B) EMESSA -> fn_crea_revisione -> rev.2 BOZZA + rev.1 SUPERATA
--         C) EMESSA -> RIFIUTATA -> tentativo push -> fallisce
--
-- Indice test (1..8):
--   1)  Riferimenti minimi disponibili nel seed (fixture sanity check)
--   2)  Flusso A: BOZZA -> EMESSA -> ACCETTATA -> contratto DRAFT generato
--   3)  Flusso A: contratto ha offerta_id e sorgente_uid corretti
--   4)  Flusso A: istanza_utility_id e utility_id copiati 1:1 sul contratto
--   5)  Flusso B: fn_crea_revisione da EMESSA -> rev.2 in BOZZA
--   6)  Flusso B: rev.1 marcata SUPERATA dopo fn_crea_revisione
--   7)  Flusso C: EMESSA -> RIFIUTATA ok
--   8)  Flusso C: tentativo push su RIFIUTATA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(8);

-- ============================================================
-- Setup fixture comune
-- ============================================================
CREATE TEMP TABLE tmp_e2e_ctx AS
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
    (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato = 'ATTIVA' ORDER BY lv.id LIMIT 1) AS listino_versione_id_attiva,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'RIFIUTATA') AS stato_rifiutata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'SUPERATA')  AS stato_superata_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')   AS stato_draft_contratto_id;

-- ============================================================
-- 1) Riferimenti minimi disponibili
-- ============================================================
SELECT ok(
    (SELECT billing_account_id IS NOT NULL
           AND emittente_fiscale_id IS NOT NULL
           AND listino_id IS NOT NULL
           AND listino_versione_id_attiva IS NOT NULL
           AND stato_bozza_id IS NOT NULL
           AND stato_emessa_id IS NOT NULL
           AND stato_accettata_id IS NOT NULL
           AND stato_draft_contratto_id IS NOT NULL
       FROM tmp_e2e_ctx),
    '1) Riferimenti minimi disponibili nel seed (BA, emittente, listino ATTIVA, stati)'
);

-- ============================================================
-- Flusso A: BOZZA -> EMESSA -> ACCETTATA -> push a contratto
-- ============================================================

-- Offerta A in BOZZA con utility
CREATE TEMP TABLE tmp_e2e_ofc_a AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, validita_al,
        stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2102-01-01', DATE '2102-12-31',
           ctx.stato_bozza_id
      FROM tmp_e2e_ctx ctx
    RETURNING id, uid, istanza_utility_id, utility_id
)
SELECT * FROM ins;

-- Aggiunge utility 1:1
INSERT INTO vendite.offerte_commerciali_utilities (
    offerta_id, istanza_utility_id, utility_id
)
SELECT a.id, a.istanza_utility_id, a.utility_id
  FROM tmp_e2e_ofc_a a;

-- BOZZA -> EMESSA
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_e2e_ctx)
 WHERE id = (SELECT id FROM tmp_e2e_ofc_a);

-- EMESSA -> ACCETTATA
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_accettata_id FROM tmp_e2e_ctx)
 WHERE id = (SELECT id FROM tmp_e2e_ofc_a);

-- Push a contratto
CREATE TEMP TABLE tmp_e2e_contratto_a AS
SELECT vendite.fn_push_offerta_a_contratto(
    (SELECT id FROM tmp_e2e_ofc_a),
    NULL::bigint
) AS contratto_id;

-- ============================================================
-- 2) Flusso A: contratto DRAFT generato
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_e2e_contratto_a ca ON c.id = ca.contratto_id
          JOIN tmp_e2e_ctx ctx ON TRUE
         WHERE c.stato_doc_contratto_id = ctx.stato_draft_contratto_id
    ),
    '2) Flusso A: push -> contratto in stato DRAFT generato'
);

-- ============================================================
-- 3) Flusso A: offerta_id e sorgente_uid corretti sul contratto
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_e2e_contratto_a ca ON c.id = ca.contratto_id
          JOIN tmp_e2e_ofc_a oa ON TRUE
         WHERE c.offerta_id   = oa.id
           AND c.sorgente_uid = oa.uid
    ),
    '3) Flusso A: contratto.offerta_id e sorgente_uid valorizzati correttamente'
);

-- ============================================================
-- 4) Flusso A: istanza_utility_id e utility_id copiati 1:1
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_e2e_contratto_a ca ON c.id = ca.contratto_id
          JOIN tmp_e2e_ofc_a oa ON TRUE
         WHERE c.istanza_utility_id = oa.istanza_utility_id
           AND c.utility_id         = oa.utility_id
    ),
    '4) Flusso A: istanza_utility_id e utility_id copiati 1:1 dal push (B2)'
);

-- ============================================================
-- Flusso B: offerta EMESSA -> fn_crea_revisione -> rev.2 + rev.1 SUPERATA
-- ============================================================

-- Offerta B in BOZZA -> EMESSA
CREATE TEMP TABLE tmp_e2e_ofc_b AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2103-01-01', ctx.stato_bozza_id
      FROM tmp_e2e_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_e2e_ctx)
 WHERE id = (SELECT id FROM tmp_e2e_ofc_b);

CREATE TEMP TABLE tmp_e2e_rev2_id AS
SELECT vendite.fn_crea_revisione_offerta(
    (SELECT id FROM tmp_e2e_ofc_b),
    'pgtap_e2e'
) AS new_id;

-- ============================================================
-- 5) Flusso B: rev.2 in BOZZA con revisione_numero = 2
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.offerte_commerciali oc
          JOIN tmp_e2e_rev2_id r2 ON oc.id = r2.new_id
          JOIN tmp_e2e_ctx ctx ON TRUE
         WHERE oc.stato_doc_offerta_id = ctx.stato_bozza_id
           AND oc.revisione_numero = 2
           AND oc.revisione_padre_id = (SELECT id FROM tmp_e2e_ofc_b)
    ),
    '5) Flusso B: rev.2 in BOZZA con revisione_numero=2 e padre corretto'
);

-- ============================================================
-- 6) Flusso B: rev.1 marcata SUPERATA
-- ============================================================
SELECT ok(
    (SELECT oc.stato_doc_offerta_id = ctx.stato_superata_id
       FROM vendite.offerte_commerciali oc
       JOIN tmp_e2e_ofc_b ob ON oc.id = ob.id
       JOIN tmp_e2e_ctx ctx ON TRUE),
    '6) Flusso B: rev.1 marcata SUPERATA dopo creazione rev.2'
);

-- ============================================================
-- Flusso C: EMESSA -> RIFIUTATA -> tentativo push -> fallisce
-- ============================================================

-- Offerta C in BOZZA -> EMESSA -> RIFIUTATA
CREATE TEMP TABLE tmp_e2e_ofc_c AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2104-01-01', ctx.stato_bozza_id
      FROM tmp_e2e_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_e2e_ctx)
 WHERE id = (SELECT id FROM tmp_e2e_ofc_c);

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_rifiutata_id FROM tmp_e2e_ctx)
 WHERE id = (SELECT id FROM tmp_e2e_ofc_c);

-- ============================================================
-- 7) Flusso C: EMESSA -> RIFIUTATA ok
-- ============================================================
SELECT ok(
    (SELECT stato_doc_offerta_id = (SELECT stato_rifiutata_id FROM tmp_e2e_ctx)
       FROM vendite.offerte_commerciali
      WHERE id = (SELECT id FROM tmp_e2e_ofc_c)),
    '7) Flusso C: offerta portata in RIFIUTATA con successo'
);

-- ============================================================
-- 8) Flusso C: tentativo push su RIFIUTATA -> throws
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint)$q$,
        (SELECT id FROM tmp_e2e_ofc_c)
    ),
    'P0001', NULL,
    '8) Flusso C: push su offerta RIFIUTATA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO'
);

SELECT * FROM finish();
ROLLBACK;
