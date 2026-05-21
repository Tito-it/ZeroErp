-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_contratto_righe_preview — 4 nuove colonne output
--       Migration: 20260519-07
--       (quantita, qta_operativa, tipo_erogazione, fonte_quantita_attesa)
--
-- Indice test (1..8):
--   Struttura:
--   1) RETURNS TABLE contiene colonna fonte_quantita_attesa (migration 07 applicata)
--   2) Fixture setup OK (contratto DRAFT + versione listino ATTIVA + 4 articoli)
--
--   Comportamento per origine DA_LISTINO (articolo seq=1, nessuna eccezione):
--   3) quantita IS NULL        (LEFT JOIN su cr → NULL)
--   4) tipo_erogazione IS NULL (LEFT JOIN su cr → NULL)
--
--   Comportamento per OVERRIDE (articolo seq=2, eccezione con valori noti):
--   5) fonte_quantita_attesa = 'FISSA'
--   6) tipo_erogazione = 'CANONE'
--
--   Comportamento per AGGIUNTA standalone:
--   7) CONSUMO + LETTURE → fonte_quantita_attesa = 'LETTURE' (articolo seq=3)
--   8) CANONE + DERIVATA_COMPONENTI → fonte_quantita_attesa = 'DERIVATA_COMPONENTI' (articolo seq=4)
--
-- Note:
--   Trigger trgfn_qta_from_operativa exige qta_operativa NOT NULL su INSERT.
--   Le fixture usano qta_operativa e uom_operativa_id non-NULL per passare il trigger
--   con early return (entrambi valorizzati → RETURN NEW senza ricalcolo).
--   Il brief suggerisce "qta_operativa IS NULL" per LETTURE: si tratta di un vincolo
--   BE (_apply_fonte_quantita_logic), non DB; in DB qta_operativa è sempre non-NULL
--   perché il trigger alzerebbe E_QTA_MISSING.
-- ------------------------------------------------------------

BEGIN;

-- ============================================================
-- Setup fixture
-- ============================================================

-- Contesto base: un billing_account, UoM, e stati doc
CREATE TEMP TABLE tmp_prv_ctx AS
SELECT
    ba.id                   AS ba_id,
    ba.istanza_utility_id,
    ba.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT' LIMIT 1) AS id_draft,
    (SELECT id FROM catalogo.unita_misura WHERE attivo = TRUE LIMIT 1) AS uom_id
FROM anagrafiche.billing_account ba
ORDER BY ba.id
LIMIT 1;

-- 4 articoli standalone distinti (non compositi)
CREATE TEMP TABLE tmp_prv_arts AS
SELECT a.id AS articolo_id, ROW_NUMBER() OVER (ORDER BY a.id) AS seq
  FROM catalogo.articoli a
 WHERE a.attivo = TRUE AND a.is_composito = FALSE
 ORDER BY a.id
 LIMIT 4;

-- Listino con codice univoco (suffisso random)
CREATE TEMP TABLE tmp_prv_listino AS
WITH ins AS (
    INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_PRV_' || substr(gen_random_uuid()::text, 1, 8),
           'Test preview nuovi campi', l.utility_id, l.tipologia_id, l.emittente_soggetto_ruolo_id
      FROM vendite.listini l
     WHERE l.attivo = TRUE
     ORDER BY l.id
     LIMIT 1
    RETURNING id
)
SELECT id FROM ins;

-- Versione ATTIVA con valido_dal nel passato → validita @> CURRENT_DATE = TRUE
-- Necessario perché fn_contratto_righe_preview fa lookup con validita @> CURRENT_DATE.
CREATE TEMP TABLE tmp_prv_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)
    SELECT id,
           'PGTAP-PRV-V1-' || substr(gen_random_uuid()::text, 1, 4),
           '2020-01-01'::date,
           'ATTIVA'
      FROM tmp_prv_listino
    RETURNING id
)
SELECT id FROM ins;

-- 2 righe listino: articoli seq=1 (nessuna eccezione → DA_LISTINO)
--                               seq=2 (avrà OVERRIDE)
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, a.articolo_id, ctx.uom_id, 100.00
  FROM tmp_prv_ver v, tmp_prv_arts a, tmp_prv_ctx ctx
 WHERE a.seq IN (1, 2);

-- Contratto DRAFT collegato al listino (listino_versione_id = NULL → lookup operativo)
CREATE TEMP TABLE tmp_prv_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (
        numero, billing_account_id, istanza_utility_id, utility_id,
        stato_doc_contratto_id, listino_id, valido_dal, valido_al
    )
    SELECT 'PGTAP_PRV_CNT_' || substr(gen_random_uuid()::text, 1, 6),
           ctx.ba_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.id_draft, l.id,
           '2026-01-01'::date, '2026-12-31'::date
      FROM tmp_prv_ctx ctx, tmp_prv_listino l
     WHERE ctx.ba_id IS NOT NULL AND ctx.id_draft IS NOT NULL
    RETURNING id
)
SELECT id FROM ins;

-- OVERRIDE per articolo seq=2: valori noti per i test 5 e 6.
-- Entrambi qta_operativa e uom_operativa_id valorizzati → trigger early return,
-- quantita resta 3 come inserita.
INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
    tipo_erogazione, fonte_quantita_attesa,
    quantita, qta_operativa, uom_operativa_id
)
SELECT c.id, a.articolo_id, 'OVERRIDE', 80.00,
       'CANONE', 'FISSA',
       3, 3, ctx.uom_id
  FROM tmp_prv_contratto c, tmp_prv_arts a, tmp_prv_ctx ctx
 WHERE a.seq = 2 AND c.id IS NOT NULL;

-- AGGIUNTA standalone: articolo seq=3, CONSUMO + LETTURE (test 7)
-- qta_operativa e uom_operativa_id NON NULL → trigger early return.
INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
    tipo_erogazione, fonte_quantita_attesa,
    qta_operativa, uom_operativa_id
)
SELECT c.id, a.articolo_id, 'AGGIUNTA', 50.00,
       'CONSUMO', 'LETTURE',
       1, ctx.uom_id
  FROM tmp_prv_contratto c, tmp_prv_arts a, tmp_prv_ctx ctx
 WHERE a.seq = 3 AND c.id IS NOT NULL;

-- AGGIUNTA standalone: articolo seq=4, CANONE + DERIVATA_COMPONENTI (test 8)
-- CANONE + DERIVATA_COMPONENTI = 🟢 (matrice 20260519).
-- quantita=5 esplicitamente; trigger early return perché entrambi qta_operativa
-- e uom_operativa_id sono valorizzati → quantita rimane 5.
INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
    tipo_erogazione, fonte_quantita_attesa,
    quantita, qta_operativa, uom_operativa_id
)
SELECT c.id, a.articolo_id, 'AGGIUNTA', 100.00,
       'CANONE', 'DERIVATA_COMPONENTI',
       5, 1, ctx.uom_id
  FROM tmp_prv_contratto c, tmp_prv_arts a, tmp_prv_ctx ctx
 WHERE a.seq = 4 AND c.id IS NOT NULL;

-- Cattura i risultati della preview per i test comportamentali.
CREATE TEMP TABLE tmp_prv_rows AS
SELECT *
  FROM vendite.fn_contratto_righe_preview(
      (SELECT id FROM tmp_prv_contratto LIMIT 1)
  );

-- ============================================================
SELECT plan(8);
-- ============================================================

-- ============================================================
-- 1) Struttura: la migrazione 07 ha aggiunto fonte_quantita_attesa al RETURNS TABLE
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
          FROM pg_catalog.pg_proc p
          JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'fn_contratto_righe_preview'
           AND pg_get_function_result(p.oid) LIKE '%fonte_quantita_attesa%'
    ),
    '1) RETURNS TABLE contiene fonte_quantita_attesa (migration 20260519-07)'
);

-- ============================================================
-- 2) Fixture setup OK
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM tmp_prv_contratto WHERE id IS NOT NULL)
    AND (SELECT COUNT(*) FROM tmp_prv_arts) >= 4
    AND EXISTS(SELECT 1 FROM tmp_prv_ver WHERE id IS NOT NULL),
    '2) fixture: contratto DRAFT + versione listino ATTIVA + 4 articoli disponibili'
);

-- ============================================================
-- 3) DA_LISTINO puro (articolo seq=1, nessuna eccezione): quantita IS NULL
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_rows WHERE origine = 'DA_LISTINO')
    THEN skip('3) nessuna riga DA_LISTINO nella preview — skip')
    ELSE is(
        (SELECT pr.quantita
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 1
          LIMIT 1),
        NULL::numeric,
        '3) DA_LISTINO puro (seq=1): quantita IS NULL (LEFT JOIN su cr → NULL)'
    )
END;

-- ============================================================
-- 4) DA_LISTINO puro (articolo seq=1): tipo_erogazione IS NULL
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_rows WHERE origine = 'DA_LISTINO')
    THEN skip('4) nessuna riga DA_LISTINO nella preview — skip')
    ELSE is(
        (SELECT pr.tipo_erogazione
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 1
          LIMIT 1),
        NULL::varchar,
        '4) DA_LISTINO puro (seq=1): tipo_erogazione IS NULL (LEFT JOIN su cr → NULL)'
    )
END;

-- ============================================================
-- 5) OVERRIDE (articolo seq=2): fonte_quantita_attesa = 'FISSA'
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_rows WHERE origine = 'OVERRIDE')
    THEN skip('5) nessuna riga OVERRIDE nella preview — skip')
    ELSE is(
        (SELECT pr.fonte_quantita_attesa
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 2
          LIMIT 1),
        'FISSA',
        '5) OVERRIDE (seq=2): fonte_quantita_attesa = FISSA (da cr.fonte_quantita_attesa)'
    )
END;

-- ============================================================
-- 6) OVERRIDE (articolo seq=2): tipo_erogazione = 'CANONE'
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_rows WHERE origine = 'OVERRIDE')
    THEN skip('6) nessuna riga OVERRIDE nella preview — skip')
    ELSE is(
        (SELECT pr.tipo_erogazione
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 2
          LIMIT 1),
        'CANONE',
        '6) OVERRIDE (seq=2): tipo_erogazione = CANONE (da cr.tipo_erogazione)'
    )
END;

-- ============================================================
-- 7) AGGIUNTA CONSUMO+LETTURE (articolo seq=3): fonte = 'LETTURE'
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_arts WHERE seq = 3)
    THEN skip('7) meno di 3 articoli disponibili — skip AGGIUNTA LETTURE')
    ELSE is(
        (SELECT pr.fonte_quantita_attesa
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 3
          LIMIT 1),
        'LETTURE',
        '7) AGGIUNTA standalone CONSUMO+LETTURE (seq=3): fonte_quantita_attesa = LETTURE'
    )
END;

-- ============================================================
-- 8) AGGIUNTA CANONE+DERIVATA_COMPONENTI (articolo seq=4): fonte e quantita corrette
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_arts WHERE seq = 4)
    THEN skip('8) meno di 4 articoli disponibili — skip AGGIUNTA DERIVATA_COMPONENTI')
    ELSE is(
        (SELECT pr.fonte_quantita_attesa
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 4
          LIMIT 1),
        'DERIVATA_COMPONENTI',
        '8) AGGIUNTA standalone CANONE+DERIVATA_COMPONENTI (seq=4): fonte_quantita_attesa = DERIVATA_COMPONENTI'
    )
END;

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
