-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-07 (brief-db-sorgente-documento-e-riga, giro T.5, 20261106-97): contratti.offerta_id e'
--   ritirata; il contratto nato dall'offerta si riconosce dalla provenienza (sorgente_uid = l'uid
--   dell'offerta, col tipo OFFERTA_COMMERCIALE). Attese invariate.
-- pgTAP test per Zero ERP
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato dell'offerta si
--   cambia solo dal verbo vendite.fn_cambia_stato_offerta; i flussi A, B, C lo chiamano al
--   posto degli UPDATE di stato (EMESSA -> RIFIUTATA con la motivazione, che la matrice
--   chiede). All'utente del contesto si concede l'azione emetti_offerta: il test prova i
--   flussi, non il permesso.
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

-- Il test prova i flussi, non il permesso: l'azione di processo di BOZZA -> EMESSA.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');

-- ============================================================
-- Setup fixture comune
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce (contesto gia' aperto); listino, con la
--   sua versione ATTIVA da oggi, sulla stessa utility.
CREATE TEMP TABLE tmp_e2e_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'offerte end to end',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_e2e_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_e2e_cli), 'offerte end to end');

CREATE TEMP TABLE tmp_e2e_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_e2e_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_e2e_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_e2e_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_e2e_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_e2e_listino) AS listino_versione_id_attiva,
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
    '1) Riferimenti minimi disponibili (BA e listino ATTIVA costruiti, emittente, stati)'
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

-- BOZZA -> EMESSA, dal verbo
SELECT * FROM vendite.fn_cambia_stato_offerta((SELECT id FROM tmp_e2e_ofc_a), 'EMESSA', NULL);

-- EMESSA -> ACCETTATA, dal verbo
SELECT * FROM vendite.fn_cambia_stato_offerta((SELECT id FROM tmp_e2e_ofc_a), 'ACCETTATA', NULL);

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
-- 3) Flusso A: la provenienza corretta sul contratto (l'uid dell'offerta)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_e2e_contratto_a ca ON c.id = ca.contratto_id
          JOIN tmp_e2e_ofc_a oa ON TRUE
         WHERE c.sorgente_uid = oa.uid
           AND c.sorgente_id IS NULL
    ),
    '3) Flusso A: la provenienza del contratto e'' l''uid dell''offerta'
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

SELECT * FROM vendite.fn_cambia_stato_offerta((SELECT id FROM tmp_e2e_ofc_b), 'EMESSA', NULL);

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

SELECT * FROM vendite.fn_cambia_stato_offerta((SELECT id FROM tmp_e2e_ofc_c), 'EMESSA', NULL);

-- EMESSA -> RIFIUTATA: la matrice chiede la motivazione
SELECT * FROM vendite.fn_cambia_stato_offerta((SELECT id FROM tmp_e2e_ofc_c), 'RIFIUTATA', 'pgTAP e2e: rifiuto del cliente');

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
