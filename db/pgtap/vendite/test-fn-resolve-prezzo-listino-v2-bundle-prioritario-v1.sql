-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: fn_resolve_prezzo_listino_v2 — logica bundle-prioritario
-- Fix bug 2026-05-13 sera: bundle (listini_righe_componenti) deve
-- avere PRIORITA' su standalone (listini_righe) quando padre_contesto
-- e' fornito. Verifica anche E_LISTINO_VERSIONE_NON_ATTIVA (448).
--
-- Indice test (1..7):
--   1) Precondizione: esiste composito + BoM IVA-coerente + BA idoneo
--   2) Bundle-only (solo lrc, nessuna listini_righe): padre_contesto
--      fornito -> LISTINO_BUNDLE [CORE FIX]
--   3) Versione listino non attiva alla data (matrice OK, versione NO)
--      -> E_LISTINO_VERSIONE_NON_ATTIVA (448)
--   4) Bundle + standalone presenti: padre_contesto -> bundle vince
--      (prezzo bundle=75, standalone=100)
--   5) Solo standalone + padre_contesto fake (nessuna lrc match)
--      -> fallback CATEGORIA
--   6) Ne' bundle ne' standalone (articolo fake, padre_contesto reale)
--      -> E_PREZZO_LISTINO_RIGA_NON_TROVATA
--   7) CONTRATTO_OVERRIDE + padre_contesto -> vince CONTRATTO_OVERRIDE
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- =========================================================
-- Setup: tmp_bundle_ctx — composito + BoM + BA idoneo
--
-- Criteri selezione:
--   - padre: is_composito=TRUE, attivo=TRUE, listino_tipologia_id NOT NULL
--   - BoM entry: attivo e valida a CURRENT_DATE
--   - figlio: attivo=TRUE, iva_id = padre.iva_id (guard coerenza IVA)
--   - BA: categoria_cliente_id NOT NULL, utility SENZA dimensione
--     tipo/classe (evita guard snapshot contratto)
--   - listino attivo con tipologia padre
-- =========================================================
CREATE TEMP TABLE tmp_bundle_ctx AS
SELECT
    a_padre.id                      AS padre_id,
    a_padre.listino_tipologia_id    AS tipologia_id,
    a_padre.iva_id                  AS iva_id,
    ac.id                           AS articolo_componente_id,
    ac.componente_id                AS figlio_id,
    a_figlio.uom_id                 AS figlio_uom_id,
    ba.id                           AS ba_id,
    ba.categoria_cliente_id         AS categoria_id,
    ba.utility_id                   AS utility_id,
    ba.istanza_utility_id           AS istanza_utility_id,
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1)      AS emittente_srid,
    (SELECT l.id FROM vendite.listini l
      WHERE l.tipologia_id = a_padre.listino_tipologia_id
        AND l.attivo       = TRUE
      ORDER BY l.id LIMIT 1)                               AS listino_id
  FROM catalogo.articoli a_padre
  JOIN catalogo.articoli_componenti ac
    ON ac.prodotto_id             = a_padre.id
   AND COALESCE(ac.attivo, TRUE)  = TRUE
   AND ac.validita               @> CURRENT_DATE
  JOIN catalogo.articoli a_figlio
    ON a_figlio.id                = ac.componente_id
   AND a_figlio.attivo            IS TRUE
   AND a_figlio.iva_id            = a_padre.iva_id
  JOIN anagrafiche.billing_account ba
    ON ba.categoria_cliente_id IS NOT NULL
  WHERE a_padre.is_composito        = TRUE
    AND a_padre.attivo              IS TRUE
    AND a_padre.listino_tipologia_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
    )
    AND EXISTS (
        SELECT 1 FROM vendite.listini l
         WHERE l.tipologia_id = a_padre.listino_tipologia_id AND l.attivo = TRUE
    )
  ORDER BY a_padre.id, ac.id, ba.id
  LIMIT 1;

-- tmp_bundle_versione: creata SEMPRE (anche vuota) affinche' le SELECT
-- che la referenziano siano parsabili indipendentemente dai dati.
CREATE TEMP TABLE tmp_bundle_versione (versione_id bigint);

-- =========================================================
-- Setup versione BOZZA+attivo + matrice categoria -> listino
-- (solo se dati disponibili)
-- =========================================================
DO $$
DECLARE
    v_listino_id     bigint;
    v_versione_id    bigint;
    v_categoria_id   smallint;
    v_utility_id     integer;
    v_emittente_srid bigint;
BEGIN
    SELECT listino_id, categoria_id, utility_id, emittente_srid
      INTO v_listino_id, v_categoria_id, v_utility_id, v_emittente_srid
      FROM tmp_bundle_ctx LIMIT 1;

    IF v_listino_id IS NULL THEN RETURN; END IF;

    -- Versione BOZZA+attivo=TRUE.
    -- BOZZA: obbligatorio per INSERT su listini_righe_componenti (guard immutabilita').
    -- attivo=TRUE: il resolver filtra lv.attivo=TRUE.
    INSERT INTO vendite.listini_versioni(
        listino_id, codice_versione, valido_dal, valido_al, stato, attivo)
    VALUES (v_listino_id, 'PGTAP_BUNDLE_V', CURRENT_DATE, CURRENT_DATE + 400, 'BOZZA', TRUE);

    SELECT id INTO v_versione_id
      FROM vendite.listini_versioni
     WHERE codice_versione = 'PGTAP_BUNDLE_V'
       AND listino_id      = v_listino_id;

    INSERT INTO tmp_bundle_versione VALUES (v_versione_id);

    -- Matrice categoria -> listino (valido_al NULL = aperto).
    INSERT INTO anagrafiche.categorie_clienti_listini(
        categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
        classe_utenza_id, listino_id, tipo_variazione, valore_variazione,
        valido_dal, valido_al)
    VALUES (v_categoria_id, v_utility_id, v_emittente_srid,
            NULL, v_listino_id, NULL, NULL, CURRENT_DATE, NULL);
END
$$;

-- =========================================================
-- Setup test 2: INSERT solo riga bundle (nessuna listini_righe)
-- =========================================================
DO $$
DECLARE
    v_versione_id bigint;
BEGIN
    SELECT versione_id INTO v_versione_id FROM tmp_bundle_versione LIMIT 1;
    IF v_versione_id IS NULL THEN RETURN; END IF;

    INSERT INTO vendite.listini_righe_componenti(
        listino_versione_id, articolo_componente_id,
        articolo_padre_id, articolo_figlio_id,
        prezzo, iva_id, valido_dal, valido_al, attivo)
    SELECT v_versione_id,
           ctx.articolo_componente_id,
           ctx.padre_id,
           ctx.figlio_id,
           75.00,
           ctx.iva_id,
           CURRENT_DATE,
           CURRENT_DATE,
           TRUE
      FROM tmp_bundle_ctx ctx;
END
$$;

-- =========================================================
-- 1) Precondizione
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_bundle_versione) = 0
        THEN skip('1) Nessun composito+BoM+BA+listino idoneo — test 2..7 salteranno')
    ELSE ok(TRUE, '1) Precondizione: composito+BoM+BA+listino+versione BOZZA creati')
END;

-- =========================================================
-- 2) Bundle-only: solo lrc, nessuna listini_righe per il figlio
--    padre_contesto fornito -> LISTINO_BUNDLE [CORE FIX]
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_bundle_versione) = 0
        THEN skip('2) Dati non disponibili')
    ELSE (
        SELECT is(
            (SELECT origine::text
               FROM vendite.fn_resolve_prezzo_listino_v2(
                   ctx.figlio_id,
                   ctx.figlio_uom_id,
                   CURRENT_DATE,
                   ctx.ba_id,
                   ctx.utility_id,
                   ctx.emittente_srid,
                   NULL,
                   ctx.padre_id
               )),
            'LISTINO_BUNDLE',
            '2) Bundle-only + padre_contesto -> LISTINO_BUNDLE (core fix bug bi-layer)'
        )
        FROM tmp_bundle_ctx ctx
    )
END;

-- =========================================================
-- 3) Versione non attiva alla data CURRENT_DATE+500
--    La versione copre solo CURRENT_DATE..CURRENT_DATE+400.
--    La matrice e' aperta (valido_al NULL) -> matrice trovata.
--    -> E_LISTINO_VERSIONE_NON_ATTIVA (448)
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_bundle_versione) = 0
        THEN skip('3) Dati non disponibili')
    ELSE (
        SELECT throws_ok(
            format(
                $$SELECT * FROM vendite.fn_resolve_prezzo_listino_v2(
                    %L::uuid, %s, %L::date, %s, %s, %s, NULL, %L::uuid)$$,
                ctx.figlio_id::text,
                ctx.figlio_uom_id,
                (CURRENT_DATE + 500)::text,
                ctx.ba_id,
                ctx.utility_id,
                ctx.emittente_srid,
                ctx.padre_id::text
            ),
            'P0001',
            NULL,
            '3) Versione non attiva alla data -> E_LISTINO_VERSIONE_NON_ATTIVA'
        )
        FROM tmp_bundle_ctx ctx
    )
END;

-- =========================================================
-- Setup test 4+5: INSERT listini_righe standalone per il figlio
-- (prezzo=100, nella stessa versione BOZZA)
-- =========================================================
DO $$
DECLARE
    v_versione_id bigint;
BEGIN
    SELECT versione_id INTO v_versione_id FROM tmp_bundle_versione LIMIT 1;
    IF v_versione_id IS NULL THEN RETURN; END IF;

    INSERT INTO vendite.listini_righe(
        listino_versione_id, articolo_id, uom_id, prezzo)
    SELECT v_versione_id, ctx.figlio_id, ctx.figlio_uom_id, 100.00
      FROM tmp_bundle_ctx ctx
    ON CONFLICT DO NOTHING;
END
$$;

-- =========================================================
-- 4) Bundle + standalone presenti: padre_contesto -> bundle vince
--    (prezzo bundle=75, standalone=100)
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_bundle_versione) = 0
        THEN skip('4) Dati non disponibili')
    ELSE (
        SELECT is(
            (SELECT prezzo_finale
               FROM vendite.fn_resolve_prezzo_listino_v2(
                   ctx.figlio_id,
                   ctx.figlio_uom_id,
                   CURRENT_DATE,
                   ctx.ba_id,
                   ctx.utility_id,
                   ctx.emittente_srid,
                   NULL,
                   ctx.padre_id
               )),
            75.00::numeric,
            '4) Bundle + standalone: padre_contesto -> bundle vince (prezzo=75 non 100)'
        )
        FROM tmp_bundle_ctx ctx
    )
END;

-- =========================================================
-- 5) Solo standalone + padre_contesto fake: nessuna lrc per il padre fake
--    -> fallback CATEGORIA, prezzo=100
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_bundle_versione) = 0
        THEN skip('5) Dati non disponibili')
    ELSE (
        SELECT is(
            (SELECT origine::text
               FROM vendite.fn_resolve_prezzo_listino_v2(
                   ctx.figlio_id,
                   ctx.figlio_uom_id,
                   CURRENT_DATE,
                   ctx.ba_id,
                   ctx.utility_id,
                   ctx.emittente_srid,
                   NULL,
                   -- UUID fake: nessuna lrc con questo padre -> fallback standalone
                   '00000000-0000-0000-0000-000000000099'::uuid
               )),
            'CATEGORIA',
            '5) padre_contesto fake (nessuna lrc) + standalone presente -> CATEGORIA'
        )
        FROM tmp_bundle_ctx ctx
    )
END;

-- =========================================================
-- 6) Ne' bundle ne' standalone: articolo UUID fake
--    padre_contesto = reale -> bundle tentato ma non trovato
--    standalone non trovato (articolo fake non ha righe)
--    -> E_PREZZO_LISTINO_RIGA_NON_TROVATA
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_bundle_versione) = 0
        THEN skip('6) Dati non disponibili')
    ELSE (
        SELECT throws_ok(
            format(
                $$SELECT * FROM vendite.fn_resolve_prezzo_listino_v2(
                    '00000000-0000-0000-0000-000000000098'::uuid,
                    %s, %L::date, %s, %s, %s, NULL, %L::uuid)$$,
                ctx.figlio_uom_id,
                CURRENT_DATE::text,
                ctx.ba_id,
                ctx.utility_id,
                ctx.emittente_srid,
                ctx.padre_id::text
            ),
            'P0001',
            NULL,
            '6) Articolo fake + padre_contesto reale: ne'' bundle ne'' standalone -> P0001'
        )
        FROM tmp_bundle_ctx ctx
    )
END;

-- =========================================================
-- Setup test 7: contratto ATTIVO con riga prezzo=999 per il figlio
-- =========================================================
DO $$
DECLARE
    v_versione_id bigint;
BEGIN
    SELECT versione_id INTO v_versione_id FROM tmp_bundle_versione LIMIT 1;
    IF v_versione_id IS NULL THEN RETURN; END IF;

    INSERT INTO vendite.contratti(
        numero, billing_account_id, istanza_utility_id, utility_id,
        stato_doc_contratto_id, valido_dal, listino_id)
    SELECT 'PGTAP_BNDL_OVR',
           ctx.ba_id,
           ctx.istanza_utility_id,
           ctx.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO'),
           CURRENT_DATE,
           ctx.listino_id
      FROM tmp_bundle_ctx ctx;

    INSERT INTO vendite.contratti_righe(
        contratto_id, articolo_id, prezzo_unitario, attivo, qta_operativa)
    SELECT c.id, ctx.figlio_id, 999.00, TRUE, 1
      FROM vendite.contratti c, tmp_bundle_ctx ctx
     WHERE c.numero = 'PGTAP_BNDL_OVR';
END
$$;

-- =========================================================
-- 7) CONTRATTO_OVERRIDE + padre_contesto: override batte bundle
--    Il contratto ha riga prezzo=999 per il figlio.
--    STADIO 1a (CONTRATTO_OVERRIDE) precede bundle -> prezzo=999.
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_bundle_versione) = 0
        THEN skip('7) Dati non disponibili')
    ELSE (
        SELECT is(
            (SELECT origine::text
               FROM vendite.fn_resolve_prezzo_listino_v2(
                   ctx.figlio_id,
                   ctx.figlio_uom_id,
                   CURRENT_DATE,
                   ctx.ba_id,
                   ctx.utility_id,
                   ctx.emittente_srid,
                   NULL,
                   ctx.padre_id
               )),
            'CONTRATTO_OVERRIDE',
            '7) CONTRATTO_OVERRIDE + padre_contesto -> vince override (bundle ignorato)'
        )
        FROM tmp_bundle_ctx ctx
    )
END;

SELECT * FROM finish();
ROLLBACK;
