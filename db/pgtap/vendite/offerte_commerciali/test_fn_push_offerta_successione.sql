-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id,
--       p_chiudi_contratto_esistente) — percorso SUCCESSIONE su overlap.
--       Il push e' consumatore del meccanismo generico (brief §3.4):
--       advisory lock + fn_contratto_sovrapposto + routing + backstop.
--
-- Riferimento: docs/it/dev/work-in-progress/brief-db-offerta-push-successione-contratto-overlap.md §4
--
-- Indice test (1..6):
--   1)  push offerta A (ACCETTATA) -> contratto DRAFT creato (baseline incumbent)
--   2)  push offerta B sovrapposta, chiudi=false -> throws E_CONTRATTO_OVERLAP_ESISTENTE
--   3)  dopo il fallimento (2) nessun contratto creato per l'offerta B
--   4)  push offerta B sovrapposta, chiudi=true -> contratto creato
--   5)  successione: il vecchio contratto A e' accorciato a (B.validita_dal - 1)
--   6)  push offerta C non sovrapposta, chiamata a 2 argomenti (default false) -> creato
--
-- Fixture: tre offerte ACCETTATE sullo stesso BA/istanza/utility.
--   A [2098-01-01..2098-12-31], B [2098-06-01..2098-12-31] (overlap su A),
--   C [2099-01-01..2099-12-31] (libera dopo la successione).
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

-- ============================================================
-- Setup fixture (contesto come test_fn_push_offerta_a_contratto)
-- ============================================================
CREATE TEMP TABLE tmp_pushsucc_ctx AS
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
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')   AS stato_draft_contratto_id;

-- Tre offerte in BOZZA (marker in meta->>'pgtap_succ')
INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, validita_al,
    stato_doc_offerta_id, meta
)
SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
       ctx.listino_id, ctx.listino_versione_id_attiva, v.dal, v.al,
       ctx.stato_bozza_id, jsonb_build_object('pgtap_succ', v.tag)
  FROM tmp_pushsucc_ctx ctx,
       (VALUES
            ('A', '2098-01-01'::date, '2098-12-31'::date),
            ('B', '2098-06-01'::date, '2098-12-31'::date),
            ('C', '2099-01-01'::date, '2099-12-31'::date)
       ) AS v(tag, dal, al);

-- Transizioni BOZZA -> EMESSA -> ACCETTATA (guard transizione richiede i passi)
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_pushsucc_ctx)
 WHERE meta->>'pgtap_succ' IN ('A','B','C');

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_accettata_id FROM tmp_pushsucc_ctx)
 WHERE meta->>'pgtap_succ' IN ('A','B','C');

-- Push offerta A (baseline): crea il contratto incumbent
CREATE TEMP TABLE tmp_pushsucc_a AS
SELECT vendite.fn_push_offerta_a_contratto(
    (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'A'),
    NULL::bigint,
    false
) AS contratto_id;

-- ============================================================
-- 1) Contratto A creato in stato DRAFT
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_pushsucc_a ta ON c.id = ta.contratto_id
         WHERE c.stato_doc_contratto_id = (SELECT stato_draft_contratto_id FROM tmp_pushsucc_ctx)
    ),
    '1) push offerta A -> contratto DRAFT creato (incumbent)'
);

-- ============================================================
-- 2) Push offerta B sovrapposta, chiudi=false -> throws E_CONTRATTO_OVERLAP_ESISTENTE
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint, false)$q$,
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'B')
    ),
    'P0001', NULL,
    '2) push offerta sovrapposta con chiudi=false -> throws E_CONTRATTO_OVERLAP_ESISTENTE'
);

-- ============================================================
-- 3) Dopo il fallimento nessun contratto creato per l'offerta B
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM vendite.contratti
         WHERE offerta_id = (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'B')
    ),
    '3) overlap con chiudi=false -> nessun contratto creato per l''offerta B'
);

-- ============================================================
-- 4) Push offerta B con chiudi=true -> contratto creato
-- ============================================================
SELECT ok(
    vendite.fn_push_offerta_a_contratto(
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'B'),
        NULL::bigint,
        true
    ) IS NOT NULL,
    '4) push offerta sovrapposta con chiudi=true -> contratto creato (successione)'
);

-- ============================================================
-- 5) Il vecchio contratto A e' accorciato a (B.validita_dal - 1) = 2098-05-31
-- ============================================================
SELECT is(
    (SELECT valido_al FROM vendite.contratti
      WHERE offerta_id = (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'A')),
    '2098-05-31'::date,
    '5) successione -> vecchio contratto A accorciato a validita_dal del nuovo - 1'
);

-- ============================================================
-- 6) Push offerta C non sovrapposta (chiamata a 2 argomenti, default false) -> creato
-- ============================================================
SELECT ok(
    vendite.fn_push_offerta_a_contratto(
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'C'),
        NULL::bigint
    ) IS NOT NULL,
    '6) push offerta senza overlap (chiamata a 2 argomenti, default chiudi=false) -> contratto creato'
);

SELECT * FROM finish();
ROLLBACK;
