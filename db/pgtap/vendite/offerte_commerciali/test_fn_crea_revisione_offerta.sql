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
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): l'offerta del test 7
--   nasce in bozza e si porta avanti con dbops.fn_pgtap_porta_a_stato (prima
--   nasceva gia' ACCETTATA).
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato
--   dell'offerta dal verbo — rev.1 si emette con dbops.fn_pgtap_porta_a_stato
--   invece dell'UPDATE di stato, che la porta ora rifiuta.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
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
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe di
--   offerta stanno nel PERIMETRO dell'articolo, e la tipologia dell'articolo dev'essere fra
--   quelle della utility del cliente. Gli articoli si COSTRUISCONO (dbops.fn_pgtap_crea_articolo:
--   MERCE senza tipologia, ammette UNA_TANTUM): prima erano i primi per id del database,
--   che su dbdev sono PRODOTTI, e la utility del cliente preso dai dati (TEL) non li prevede.
CREATE TEMP TABLE tmp_rev_fn_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-REVF-1') AS a1,
       dbops.fn_pgtap_crea_articolo('PGT-REVF-2') AS a2,
       dbops.fn_pgtap_crea_articolo('PGT-REVF-3') AS a3;

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce (contesto gia' aperto); listino, con la
--   sua versione ATTIVA da oggi, sulla stessa utility.
CREATE TEMP TABLE tmp_rev_fn_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'crea revisione offerta',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_rev_fn_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_rev_fn_cli), 'crea revisione offerta');

-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5): le
--   due OVERRIDE (a1, a3) modificano una riga del listino, quindi i loro articoli
--   ci stanno. Prima si scrivevano fuori listino e non comparivano nel drawer.
SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT listino_versione_id FROM tmp_rev_fn_listino),
    ARRAY[(SELECT a1 FROM tmp_rev_fn_art), (SELECT a3 FROM tmp_rev_fn_art)]);

CREATE TEMP TABLE tmp_rev_fn_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_rev_fn_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_rev_fn_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_rev_fn_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_rev_fn_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_rev_fn_listino) AS listino_versione_id_attiva,
    (SELECT a1 FROM tmp_rev_fn_art) AS articolo_id_1,
    -- rev 2026-10-04: l'articolo dell'AGGIUNTA sta FUORI dalla versione di listino
    --   dell'offerta (guard script.trgfn_righe_guard_aggiunta_fuori_listino, ora
    --   anche sull'offerta), e diverso dal primo. Rev 2026-10-07: costruito, quindi
    --   fuori da ogni listino per costruzione.
    (SELECT a2 FROM tmp_rev_fn_art) AS articolo_id_2,
    (SELECT a3 FROM tmp_rev_fn_art) AS articolo_id_3,
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

-- Eccezioni rev.1: 2 attive + 1 inattiva
-- tipo_erogazione UNA_TANTUM + fonte FISSA: combinazione ammessa da tutti i CHECK.
-- ⭐ CORRETTO IL 2026-08-24 — con `fonte_quantita_attesa = 'FISSA'` la quantita'
--    va messa in **qta_operativa**, non lasciata a NULL: e' la colonna operativa,
--    ed e' quella che il guard pretende (E_QTA_MISSING, «Quantita' nulla o
--    mancante», che nomina la colonna). Senza, il fixture non entrava proprio e
--    il file falliva prima di qualunque asserzione.
--    ⚠️ E' una trappola nota di questa famiglia di tabelle: la quantita'
--    "parlante" e' quella operativa, non `quantita`.
INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione,
    tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo, qta_operativa
)
-- ⛔ rev 2026-10-13 (Lotto 3b): l'articolo sta nel listino e ne prende la
--   tipologia, che dipende dalla utility: erogazione e fonte le eredita il DB
--   (NULL), la quantita' c'e' solo se la fonte ereditata e' FISSA.
SELECT r1.id, ctx.articolo_id_1, 'OVERRIDE'::"vendite"."tipo_eccezione_contratto",
       NULL, NULL, 100.00, TRUE,
       (SELECT 1.00 FROM vendite.fn_articolo_erogazioni(ctx.articolo_id_1) e
         WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1)
  FROM tmp_rev_fn_rev1 r1, tmp_rev_fn_ctx ctx
 WHERE ctx.articolo_id_1 IS NOT NULL;

INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione,
    tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo, qta_operativa
)
SELECT r1.id, ctx.articolo_id_2, 'AGGIUNTA'::"vendite"."tipo_eccezione_contratto",
       'UNA_TANTUM', 'FISSA', 50.00, TRUE, 1.00
  FROM tmp_rev_fn_rev1 r1, tmp_rev_fn_ctx ctx
 WHERE ctx.articolo_id_2 IS NOT NULL;

-- Eccezione inattiva: NON deve essere copiata nella revisione
INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione,
    tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo, qta_operativa
)
-- ⛔ rev 2026-10-13 (Lotto 3b): l'articolo sta nel listino e ne prende la
--   tipologia, che dipende dalla utility: erogazione e fonte le eredita il DB
--   (NULL), la quantita' c'e' solo se la fonte ereditata e' FISSA.
SELECT r1.id, ctx.articolo_id_3, 'OVERRIDE'::"vendite"."tipo_eccezione_contratto",
       NULL, NULL, 75.00, FALSE,
       (SELECT 1.00 FROM vendite.fn_articolo_erogazioni(ctx.articolo_id_3) e
         WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1)
  FROM tmp_rev_fn_rev1 r1, tmp_rev_fn_ctx ctx
 WHERE ctx.articolo_id_3 IS NOT NULL
   AND ctx.articolo_id_3 <> ctx.articolo_id_1
   AND ctx.articolo_id_3 <> ctx.articolo_id_2;

-- ⚠️ rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R5a): le righe
--   dell'offerta si scrivono solo in BOZZA. L'emissione viene quindi DOPO le
--   eccezioni, come in un'offerta vera; prima le si aggiungeva a rev.1 gia' EMESSA.
-- ⚠️ rev 2026-10-11 (brief-db-testata-dopo-emissione §11, R-DB-3): anche la
--   fornitura si scrive solo in BOZZA (trg_offerte_commerciali_utilities_a05_
--   doc_bozza_ins_upd_dlt). Nasce quindi prima dell'emissione, come le eccezioni.
-- Utility rev.1 (1:1)
INSERT INTO vendite.offerte_commerciali_utilities (
    offerta_id, istanza_utility_id, utility_id
)
SELECT r1.id, ctx.istanza_utility_id, ctx.utility_id
  FROM tmp_rev_fn_rev1 r1, tmp_rev_fn_ctx ctx;

-- rev 2026-10-26 (giro 9): l'emissione dal verbo, non con un UPDATE di stato.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', r1.id, 'EMESSA')
  FROM tmp_rev_fn_rev1 r1;

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
-- L'offerta nasce in BOZZA e arriva ad ACCETTATA per la matrice
-- (BOZZA -> EMESSA -> ACCETTATA), sotto i guard veri (rev 2026-10-24).
CREATE TEMP TABLE tmp_rev_fn_accettata AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva, DATE '2097-01-01',
           ctx.stato_bozza_id
      FROM tmp_rev_fn_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', a.id, 'ACCETTATA')
  FROM tmp_rev_fn_accettata a;

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
