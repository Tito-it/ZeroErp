-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato dell'offerta si
--   cambia solo dal verbo; rev.1 arriva in EMESSA con dbops.fn_pgtap_porta_a_stato invece
--   dell'UPDATE di stato. Il trigger ora proietta lo stato con
--   vendite.fn_offerta_proietta_stato_revisione: l'effetto visibile provato e' lo stesso.
--
-- Test: trigger revisione trg_offerte_commerciali_z90_revisione_ins (Step 6).
--       AFTER INSERT: quando viene inserita rev.N+1 con revisione_padre_id != NULL,
--       il trigger marca automaticamente rev.N come SUPERATA.
--
-- Indice test (1..3):
--   1)  Trigger z90_revisione_ins esiste
--   2)  INSERT rev.2 con revisione_padre_id = rev.1.id -> rev.1 diventa SUPERATA
--   3)  INSERT rev.1 con revisione_padre_id = NULL -> nessun altro stato cambia
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(3);

-- ============================================================
-- Setup fixture
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce (contesto gia' aperto); listino, con la
--   sua versione ATTIVA da oggi, sulla stessa utility.
CREATE TEMP TABLE tmp_rev_trg_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'revisione trigger',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_rev_trg_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_rev_trg_cli), 'revisione trigger');

CREATE TEMP TABLE tmp_rev_trg_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_rev_trg_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_rev_trg_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_rev_trg_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_rev_trg_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_rev_trg_listino) AS listino_versione_id_attiva,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')    AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')   AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'SUPERATA') AS stato_superata_id;

-- Rev.1: inserita in BOZZA e portata in EMESSA dal verbo
CREATE TEMP TABLE tmp_rev_trg_rev1 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva, DATE '2093-01-01',
           ctx.stato_bozza_id, 1, NULL
      FROM tmp_rev_trg_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

-- Porta rev.1 in EMESSA (perché la transizione EMESSA->SUPERATA è quella che il trigger esegue)
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', r.id, 'EMESSA')
  FROM tmp_rev_trg_rev1 r;

-- ============================================================
-- 1) Trigger z90_revisione_ins esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c    ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'offerte_commerciali'
           AND t.tgname  = 'trg_offerte_commerciali_z90_revisione_ins'
    ),
    '1) trg_offerte_commerciali_z90_revisione_ins esiste'
);

-- ============================================================
-- 2) INSERT rev.2 con revisione_padre_id = rev.1 -> rev.1 diventa SUPERATA
-- ============================================================
INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
    revisione_numero, revisione_padre_id
)
SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
       ctx.listino_id, ctx.listino_versione_id_attiva, DATE '2094-01-01',
       ctx.stato_bozza_id, 2, r1.id
  FROM tmp_rev_trg_ctx ctx, tmp_rev_trg_rev1 r1;

SELECT ok(
    (SELECT oc.stato_doc_offerta_id = ctx.stato_superata_id
       FROM vendite.offerte_commerciali oc, tmp_rev_trg_rev1 r1, tmp_rev_trg_ctx ctx
      WHERE oc.id = r1.id),
    '2) rev.1 marcata SUPERATA automaticamente dopo INSERT rev.2 con revisione_padre_id'
);

-- ============================================================
-- 3) INSERT rev senza padre (rev.1 standalone) -> nessun altro cambia stato
-- ============================================================
-- Conta le offerte in SUPERATA prima dell'INSERT
CREATE TEMP TABLE tmp_rev_superata_ante AS
SELECT COUNT(*) AS cnt FROM vendite.offerte_commerciali
 WHERE stato_doc_offerta_id = (SELECT stato_superata_id FROM tmp_rev_trg_ctx);

INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
    revisione_numero, revisione_padre_id
)
SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
       ctx.listino_id, ctx.listino_versione_id_attiva, DATE '2095-01-01',
       ctx.stato_bozza_id, 1, NULL
  FROM tmp_rev_trg_ctx ctx;

SELECT ok(
    -- Il numero di offerte SUPERATA non deve essere aumentato ulteriormente
    (SELECT COUNT(*) FROM vendite.offerte_commerciali
      WHERE stato_doc_offerta_id = (SELECT stato_superata_id FROM tmp_rev_trg_ctx))
    = (SELECT cnt FROM tmp_rev_superata_ante),
    '3) INSERT offerta con revisione_padre_id NULL: nessuna altra offerta marcata SUPERATA'
);

SELECT * FROM finish();
ROLLBACK;
