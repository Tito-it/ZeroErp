-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: generazione codice OFC-* via sistema_codici (Step 5).
--       Trigger trgfn_offerte_commerciali_gen_codice (BEFORE INSERT).
--
-- Indice test (1..4):
--   1)  Trigger gen_codice esiste su vendite.offerte_commerciali
--   2)  Sequenza vendite.offerte_commerciali_codice_seq esiste
--   3)  INSERT senza codice -> codice generato con pattern OFC-NNNNNNN
--   4)  Secondo INSERT -> codice successivo (incremento sequenza)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(4);

-- ============================================================
-- Setup fixture
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce (contesto gia' aperto); listino, con la
--   sua versione ATTIVA da oggi, sulla stessa utility.
CREATE TEMP TABLE tmp_codice_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'codice offerte',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_codice_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_codice_cli), 'codice offerte');

CREATE TEMP TABLE tmp_codice_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_codice_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_codice_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_codice_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_codice_listino) AS listino_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA') AS stato_bozza_id;

-- ============================================================
-- 1) Trigger gen_codice esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c    ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'offerte_commerciali'
           AND t.tgname  = 'trg_offerte_commerciali_a10_gen_codice_ins_upd'
    ),
    '1) trg_offerte_commerciali_a10_gen_codice_ins_upd esiste'
);

-- ============================================================
-- 2) Sequenza offerte_commerciali_codice_seq esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_sequences
         WHERE schemaname = 'vendite'
           AND sequencename = 'offerte_commerciali_codice_seq'
    ),
    '2) sequenza vendite.offerte_commerciali_codice_seq esiste'
);

-- ============================================================
-- 3) INSERT senza codice -> codice generato con pattern OFC-*
-- ============================================================
CREATE TEMP TABLE tmp_codice_ofc1 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, DATE '2091-01-01', ctx.stato_bozza_id
      FROM tmp_codice_ctx ctx
    RETURNING codice
)
SELECT codice FROM ins;

SELECT ok(
    (SELECT codice ~ '^OFC-[0-9]+$' FROM tmp_codice_ofc1),
    '3) codice generato automaticamente con pattern OFC-[0-9]+'
);

-- ============================================================
-- 4) Secondo INSERT -> codice successivo (valore numerico maggiore)
-- ============================================================
CREATE TEMP TABLE tmp_codice_ofc2 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, DATE '2092-01-01', ctx.stato_bozza_id
      FROM tmp_codice_ctx ctx
    RETURNING codice
)
SELECT codice FROM ins;

SELECT ok(
    -- Il secondo codice è numericamente successivo al primo
    (SELECT regexp_replace(c2.codice, '^OFC-0*', '')::bigint
               > regexp_replace(c1.codice, '^OFC-0*', '')::bigint
       FROM tmp_codice_ofc1 c1, tmp_codice_ofc2 c2),
    '4) secondo INSERT genera codice OFC-* con valore sequenziale maggiore del precedente'
);

SELECT * FROM finish();
ROLLBACK;
