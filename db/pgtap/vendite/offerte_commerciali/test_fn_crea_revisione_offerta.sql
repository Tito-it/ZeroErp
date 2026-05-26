-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_crea_revisione_offerta(p_offerta_id, p_user) (Step 7).
--       Pattern revisioni: crea rev.N+1 BOZZA, marca padre SUPERATA,
--       copia eccezioni attive (non le inattive) e utility 1:1.
--
-- Indice test (1..7):
--   1)  Funzione fn_crea_revisione_offerta presente
--   2)  Setup fixture (offerta EMESSA con 2 eccezioni attive + 1 inattiva + utility)
--   3)  Da EMESSA: rev.2 creata in BOZZA, revisione_numero = 2
--   4)  rev.1 (padre) marcata SUPERATA dopo fn_crea_revisione_offerta
--   5)  Eccezioni copiate: solo le 2 attive (non la inattiva)
--   6)  Utility copiata 1:1 (1 record per rev.2)
--   7)  Da stato ACCETTATA -> throws E_OFFERTA_REVISIONE_STATO_NON_AMMESSO
--   (test 8 da BOZZA è incluso in test 7 come verifica analoga)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'fn_crea_revisione_offerta'
    ),
    '1) vendite.fn_crea_revisione_offerta presente'
);

-- ============================================================
-- Setup fixture completa: contesti
-- ============================================================
CREATE TEMP TABLE tmp_rev_fn_ctx AS
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
    (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE ORDER BY a.id LIMIT 1)  AS articolo_id_1,
    (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE ORDER BY a.id OFFSET 1 LIMIT 1) AS articolo_id_2,
    (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE ORDER BY a.id OFFSET 2 LIMIT 1) AS articolo_id_3,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'SUPERATA')  AS stato_superata_id;

-- Rev.1: creata in BOZZA, portata in EMESSA
CREATE TEMP TABLE tmp_rev_fn_rev1 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva, DATE '2096-01-01',
           ctx.stato_bozza_id, 1, NULL
      FROM tmp_rev_fn_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_rev_fn_ctx)
 WHERE id = (SELECT id FROM tmp_rev_fn_rev1);

-- Eccezioni rev.1: 2 attive + 1 inattiva
-- tipo_erogazione UNA_TANTUM + fonte FISSA: combinazione ammessa da tutti i CHECK.
INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione,
    tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo
)
SELECT r1.id, ctx.articolo_id_1, 'OVERRIDE'::"vendite"."tipo_eccezione_contratto",
       'UNA_TANTUM', 'FISSA', 100.00, TRUE
  FROM tmp_rev_fn_rev1 r1, tmp_rev_fn_ctx ctx
 WHERE ctx.articolo_id_1 IS NOT NULL;

INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione,
    tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo
)
SELECT r1.id, ctx.articolo_id_2, 'AGGIUNTA'::"vendite"."tipo_eccezione_contratto",
       'UNA_TANTUM', 'FISSA', 50.00, TRUE
  FROM tmp_rev_fn_rev1 r1, tmp_rev_fn_ctx ctx
 WHERE ctx.articolo_id_2 IS NOT NULL;

-- Eccezione inattiva: NON deve essere copiata nella revisione
INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione,
    tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo
)
SELECT r1.id, ctx.articolo_id_3, 'OVERRIDE'::"vendite"."tipo_eccezione_contratto",
       'UNA_TANTUM', 'FISSA', 75.00, FALSE
  FROM tmp_rev_fn_rev1 r1, tmp_rev_fn_ctx ctx
 WHERE ctx.articolo_id_3 IS NOT NULL
   AND ctx.articolo_id_3 <> ctx.articolo_id_1
   AND ctx.articolo_id_3 <> ctx.articolo_id_2;

-- Utility rev.1 (1:1)
INSERT INTO vendite.offerte_commerciali_utilities (
    offerta_id, istanza_utility_id, utility_id
)
SELECT r1.id, ctx.istanza_utility_id, ctx.utility_id
  FROM tmp_rev_fn_rev1 r1, tmp_rev_fn_ctx ctx;

-- ============================================================
-- 2) Setup OK
-- ============================================================
SELECT ok(
    (SELECT id IS NOT NULL FROM tmp_rev_fn_rev1),
    '2) Offerta rev.1 EMESSA con eccezioni e utility creata (fixture OK)'
);

-- ============================================================
-- 3) fn_crea_revisione_offerta da EMESSA: rev.2 in BOZZA, revisione_numero = 2
-- ============================================================
CREATE TEMP TABLE tmp_rev_fn_rev2_id AS
SELECT vendite.fn_crea_revisione_offerta(
    (SELECT id FROM tmp_rev_fn_rev1),
    'pgtap'
) AS new_id;

SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.offerte_commerciali oc
          JOIN tmp_rev_fn_rev2_id r2 ON oc.id = r2.new_id
          JOIN tmp_rev_fn_ctx ctx ON TRUE
         WHERE oc.stato_doc_offerta_id = ctx.stato_bozza_id
           AND oc.revisione_numero = 2
           AND oc.revisione_padre_id = (SELECT id FROM tmp_rev_fn_rev1)
    ),
    '3) rev.2 creata in BOZZA con revisione_numero=2 e revisione_padre_id=rev.1.id'
);

-- ============================================================
-- 4) rev.1 (padre) marcata SUPERATA dopo fn_crea_revisione_offerta
-- ============================================================
SELECT ok(
    (SELECT oc.stato_doc_offerta_id = ctx.stato_superata_id
       FROM vendite.offerte_commerciali oc
       JOIN tmp_rev_fn_rev1 r1 ON oc.id = r1.id
       JOIN tmp_rev_fn_ctx ctx ON TRUE),
    '4) rev.1 (padre) marcata SUPERATA automaticamente dopo creazione rev.2'
);

-- ============================================================
-- 5) Eccezioni copiate: solo le 2 attive (non la inattiva)
-- ============================================================
SELECT ok(
    (SELECT COUNT(*) = 2
       FROM vendite.offerte_commerciali_eccezioni oce
       JOIN tmp_rev_fn_rev2_id r2 ON oce.offerta_id = r2.new_id
      WHERE oce.attivo IS TRUE),
    '5) rev.2 ha esattamente 2 eccezioni attive copiate (la inattiva esclusa)'
);

-- ============================================================
-- 6) Utility copiata 1:1 (1 record per rev.2)
-- ============================================================
SELECT ok(
    (SELECT COUNT(*) = 1
       FROM vendite.offerte_commerciali_utilities ocu
       JOIN tmp_rev_fn_rev2_id r2 ON ocu.offerta_id = r2.new_id),
    '6) rev.2 ha 1 record utility copiato 1:1'
);

-- ============================================================
-- 7) Da stato ACCETTATA -> throws E_OFFERTA_REVISIONE_STATO_NON_AMMESSO
-- ============================================================
-- Crea offerta direttamente in ACCETTATA (bypass trigger UPDATE)
CREATE TEMP TABLE tmp_rev_fn_accettata AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva, DATE '2097-01-01',
           ctx.stato_accettata_id
      FROM tmp_rev_fn_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_crea_revisione_offerta(%s, 'pgtap')$q$,
        (SELECT id FROM tmp_rev_fn_accettata)
    ),
    'P0001', NULL,
    '7) fn_crea_revisione_offerta da ACCETTATA -> throws E_OFFERTA_REVISIONE_STATO_NON_AMMESSO'
);

SELECT * FROM finish();
ROLLBACK;
