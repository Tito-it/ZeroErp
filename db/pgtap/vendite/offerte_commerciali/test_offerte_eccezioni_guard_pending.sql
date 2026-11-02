-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Simmetria L3 guard_pending su vendite.offerte_commerciali_eccezioni
--       Migrations: 20260601-01 (colonne), 20260601-02 (guard generico),
--                   20260601-03 (repoint trigger al generico).
--
-- Il guard riga-level e' il building-block generico
--   script.trgfn_righe_guard_pending('offerta_id'), condiviso con
--   preventivi_righe e contratti_righe (allowlist via to_jsonb).
--
-- Indice test (1..8):
--   Struttura:
--   1)  Colonne stato_approvazione_prezzo e pratica_approvazione_prezzo_id
--       presenti su offerte_commerciali_eccezioni
--   2)  Trigger trg_offerte_eccezioni_a10_guard_pending_upd usa il generico
--       script.trgfn_righe_guard_pending
--   3)  Trigger trg_offerte_eccezioni_a10_guard_pending_upd presente
--
--   Comportamento guard (COND: skip se fixture non creata):
--   4)  Eccezione stato=NULL → UPDATE prezzo_unitario OK (guard non attivo)
--   5)  Eccezione PENDING → UPDATE prezzo_unitario → raise E_RIGA_PREZZO_PENDENTE
--   6)  Eccezione PENDING → UPDATE stato PENDING→APPROVED → OK (allowlist)
--   7)  Eccezione PENDING → UPDATE pratica_approvazione_prezzo_id → OK (allowlist)
--   8)  Eccezione PENDING → UPDATE meta → OK (allowlist)
--
-- Nota: i test 4-8 saltano automaticamente se la fixture (offerta + eccezione)
--       non viene creata per mancanza di dati prerequisito.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
-- ============================================================
-- Setup fixture (dati-dipendente; skip se assenti)
-- ============================================================
-- BA senza tipi_utenze + emittente risolto dalla stessa funzione usata dai
-- guard di coerenza emittente↔BA: emittente coerente per costruzione.
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe di
--   offerta stanno nel PERIMETRO dell'articolo, e la tipologia dell'articolo dev'essere fra
--   quelle della utility del cliente. Gli articoli si COSTRUISCONO (dbops.fn_pgtap_crea_articolo:
--   MERCE senza tipologia, ammette UNA_TANTUM): prima erano i primi per id del database,
--   che su dbdev sono PRODOTTI, e la utility del cliente preso dai dati (TEL) non li prevede.
CREATE TEMP TABLE tmp_ofc_pnd_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OFCPND-1') AS a1;

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze, legato dal z90 all'emittente di chi agisce; listino sulla stessa
--   utility. L'emittente resta derivato dal BA, come prima.
CREATE TEMP TABLE tmp_ofc_pnd_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'guard pending offerte',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_ofc_pnd_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_ofc_pnd_cli), 'guard pending offerte');

CREATE TEMP TABLE tmp_ofc_pnd_ctx AS
SELECT
    anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id) AS emittente_fiscale_id,
    c.billing_account_id AS ba_id,
    c.istanza_utility_id,
    c.utility_id,
    (SELECT listino_id FROM tmp_ofc_pnd_listino)              AS listino_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA') AS id_bozza,
    (SELECT a1 FROM tmp_ofc_pnd_art)                          AS articolo_id
  FROM tmp_ofc_pnd_cli c;

-- Fixture: offerta BOZZA + eccezione AGGIUNTA non composita (prezzo valorizzato).
CREATE TEMP TABLE tmp_ofc_pnd_ids (
    offerta_id   bigint,
    eccezione_id bigint
);

DO $$
DECLARE
    v_ctx  record;
    v_off  bigint;
    v_ecc  bigint;
BEGIN
    SELECT * INTO v_ctx FROM tmp_ofc_pnd_ctx;

    IF v_ctx.ba_id IS NULL
       OR v_ctx.emittente_fiscale_id IS NULL
       OR v_ctx.listino_id IS NULL
       OR v_ctx.articolo_id IS NULL
       OR v_ctx.id_bozza IS NULL
    THEN RETURN; END IF;

    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, stato_doc_offerta_id
    )
    VALUES (
        v_ctx.emittente_fiscale_id, v_ctx.ba_id, v_ctx.istanza_utility_id,
        v_ctx.utility_id, v_ctx.listino_id, DATE '2074-01-01', v_ctx.id_bozza
    )
    RETURNING id INTO v_off;

    -- AGGIUNTA: fuori listino, prezzo esplicito (nessun guard listino su offerte).
    -- qta_operativa e' la SORGENTE (quantita la deriva trgfn_qta_from_operativa);
    -- fonte_quantita_attesa la imposta il default trigger. Pattern identico alla
    -- fixture gemella test-contratti-righe-guard-pending.
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
        tipo_erogazione
    )
    VALUES (v_off, v_ctx.articolo_id, 'AGGIUNTA', 100.00, 1.00, 'UNA_TANTUM')
    RETURNING id INTO v_ecc;

    INSERT INTO tmp_ofc_pnd_ids VALUES (v_off, v_ecc);
END $$;

-- ============================================================
SELECT plan(8);
-- ============================================================

-- ============================================================
-- 1) Colonne stato_approvazione_prezzo e pratica_approvazione_prezzo_id presenti
-- ============================================================
SELECT ok(
    (SELECT COUNT(*) = 2
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'offerte_commerciali_eccezioni'
        AND column_name  IN ('stato_approvazione_prezzo', 'pratica_approvazione_prezzo_id')),
    '1) Colonne stato_approvazione_prezzo e pratica_approvazione_prezzo_id presenti'
);

-- ============================================================
-- 2) Trigger guard_pending usa il generico script.trgfn_righe_guard_pending
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class  c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_proc   p ON p.oid = t.tgfoid
          JOIN pg_namespace pn ON pn.oid = p.pronamespace
         WHERE n.nspname  = 'vendite'
           AND c.relname  = 'offerte_commerciali_eccezioni'
           AND t.tgname   = 'trg_offerte_eccezioni_a10_guard_pending_upd'
           AND pn.nspname = 'script'
           AND p.proname  = 'trgfn_righe_guard_pending'
    ),
    '2) Trigger guard_pending usa il generico script.trgfn_righe_guard_pending'
);

-- ============================================================
-- 3) Trigger trg_offerte_eccezioni_a10_guard_pending_upd presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'offerte_commerciali_eccezioni'
           AND t.tgname  = 'trg_offerte_eccezioni_a10_guard_pending_upd'
           AND NOT t.tgisinternal
    ),
    '3) Trigger trg_offerte_eccezioni_a10_guard_pending_upd presente'
);

-- ============================================================
-- 4) Eccezione stato=NULL → UPDATE prezzo_unitario OK
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_ofc_pnd_ids)
    THEN skip('Fixture offerta/eccezione non creata - skip', 1)
    ELSE lives_ok(
        $$UPDATE vendite.offerte_commerciali_eccezioni
             SET prezzo_unitario = 200.00
           WHERE id = (SELECT eccezione_id FROM tmp_ofc_pnd_ids)
             AND stato_approvazione_prezzo IS NULL$$,
        '4) Eccezione stato=NULL → UPDATE prezzo_unitario OK (guard non attivo)'
    )
END;

-- ============================================================
-- 5) Eccezione PENDING → UPDATE prezzo_unitario → raise P0001
--    Setup: porta l'eccezione in PENDING via DO block.
-- ============================================================
DO $$
BEGIN
    UPDATE vendite.offerte_commerciali_eccezioni
       SET stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
     WHERE id = (SELECT eccezione_id FROM tmp_ofc_pnd_ids);
END;
$$;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_ofc_pnd_ids)
    THEN skip('Fixture offerta/eccezione non creata - skip', 1)
    ELSE throws_ok(
        $$UPDATE vendite.offerte_commerciali_eccezioni
             SET prezzo_unitario = 999.00
           WHERE id = (SELECT eccezione_id FROM tmp_ofc_pnd_ids)
             AND stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo$$,
        'P0001',
        NULL,
        '5) Eccezione PENDING → UPDATE prezzo_unitario → raise E_RIGA_PREZZO_PENDENTE'
    )
END;

-- ============================================================
-- 6) Eccezione PENDING → UPDATE stato PENDING→APPROVED → OK (allowlist)
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_ofc_pnd_ids)
    THEN skip('Fixture offerta/eccezione non creata - skip', 1)
    ELSE lives_ok(
        $$UPDATE vendite.offerte_commerciali_eccezioni
             SET stato_approvazione_prezzo = 'APPROVED'::config.stato_approvazione_prezzo
           WHERE id = (SELECT eccezione_id FROM tmp_ofc_pnd_ids)
             AND stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo$$,
        '6) Eccezione PENDING → UPDATE stato→APPROVED OK (transizione workflow)'
    )
END;

-- ============================================================
-- 7) Eccezione PENDING → UPDATE pratica_approvazione_prezzo_id → OK (allowlist)
--    Dopo test 6 e' APPROVED: riporta in PENDING via DO block.
-- ============================================================
DO $$
BEGIN
    UPDATE vendite.offerte_commerciali_eccezioni
       SET stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
     WHERE id = (SELECT eccezione_id FROM tmp_ofc_pnd_ids);
END;
$$;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_ofc_pnd_ids)
    THEN skip('Fixture offerta/eccezione non creata - skip', 1)
    ELSE lives_ok(
        $$UPDATE vendite.offerte_commerciali_eccezioni
             SET pratica_approvazione_prezzo_id = NULL
           WHERE id = (SELECT eccezione_id FROM tmp_ofc_pnd_ids)
             AND stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo$$,
        '7) Eccezione PENDING → UPDATE pratica_id OK (allowlist)'
    )
END;

-- ============================================================
-- 8) Eccezione PENDING → UPDATE meta → OK (allowlist)
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_ofc_pnd_ids)
    THEN skip('Fixture offerta/eccezione non creata - skip', 1)
    ELSE lives_ok(
        $$UPDATE vendite.offerte_commerciali_eccezioni
             SET meta = '{"note": "test pgtap"}'::jsonb
           WHERE id = (SELECT eccezione_id FROM tmp_ofc_pnd_ids)
             AND stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo$$,
        '8) Eccezione PENDING → UPDATE meta OK (allowlist)'
    )
END;

SELECT * FROM finish();
ROLLBACK;
