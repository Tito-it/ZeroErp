-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.trgfn_listini_righe_comp_guard_coerenza_bom
-- Riferimento: migration 20260513-19 (creazione), 20260603-03 (Guard 5
--   rimosso + cleanup JOIN a_figlio).
--
-- Contesto:
--   Guard di coerenza su vendite.listini_righe_componenti. Dopo il
--   20260603-03 i guard attivi sono 1-4 + 7 (Guard 5 IVA rimosso: ora a
--   punto unico alla sorgente; Guard 6 gia' sostituito da temporal FK).
--   Tutti sollevano E_LISTINO_COMPONENTE_COERENZA_BOM (447); il messaggio
--   447 ("Riga listino componenti incoerente: %s.") incorpora la stringa
--   specifica del guard, quindi throws_like distingue chi scatta.
--
--   Colma il buco di copertura segnalato il 2026-06-03: prima nessun pgTAP
--   asseriva i guard del listino. Il caso (2) blinda l'happy-path dopo la
--   rimozione del JOIN a_figlio.
--
-- Indice test (1..7):
--   1. Precondizione: fixture creato (composito + BoM attiva + versione BOZZA)
--   2. Riga bundle valida -> OK (regressione cleanup JOIN a_figlio)
--   3. Guard 1: articolo_componente_id inesistente -> raise (non trovato)
--   4. Guard 2: articolo_padre_id != ac.prodotto_id -> raise
--   5. Guard 3: articolo_figlio_id != ac.componente_id -> raise
--   6. Guard 7: validita riga fuori dalla versione listino -> raise
--   7. Guard 4 irraggiungibile per costruzione: il catalogo blocca
--      is_composito=FALSE su padre di BoM attiva (canarino)
--
-- Fixture self-contained: crea padre composito + figlio (stessa IVA) + BoM
-- attiva aperta, e una versione BOZZA su un listino esistente. Skippa solo
-- se mancano i seed di base (uom/tipo/gruppo/spesa/iva) o nessun listino.
-- BEGIN + ROLLBACK isolamento completo.
--
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione si
--   inserisce senza stato (nasce BOZZA dal trigger; la colonna stato non c'e' piu').
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- Setup: riferimenti seed + un listino esistente
-- =========================================================
CREATE TEMP TABLE tmp_seed AS
SELECT
    (SELECT id FROM catalogo.unita_misura     WHERE attivo IS TRUE ORDER BY id LIMIT 1)  AS uom_id,
    (SELECT id FROM vendite.articoli_tipologie WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_id,
    (SELECT id FROM vendite.articoli_gruppi    WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS gruppo_id,
    (SELECT id FROM vendite.articoli_spesa     WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS spesa_id,
    (SELECT id FROM config.iva                 WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS iva_id,
    (SELECT id FROM vendite.listini            WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS listino_id;

-- tmp_ctx popolato solo se i prerequisiti sono presenti: padre/figlio/BoM
-- creati da zero + versione BOZZA su listino esistente.
CREATE TEMP TABLE tmp_ctx (
    padre_id               uuid,
    figlio_id              uuid,
    articolo_componente_id uuid,
    iva_id                 smallint,
    versione_id            bigint
);

DO $$
DECLARE
    s            tmp_seed%ROWTYPE;
    v_p          uuid;
    v_f          uuid;
    v_l          uuid;
    v_versione   bigint;
    v_ts         text := to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS');
BEGIN
    SELECT * INTO s FROM tmp_seed LIMIT 1;
    IF s.uom_id IS NULL OR s.tipo_id IS NULL OR s.gruppo_id IS NULL
       OR s.spesa_id IS NULL OR s.iva_id IS NULL OR s.listino_id IS NULL THEN
        RETURN;  -- prerequisiti mancanti -> tmp_ctx resta vuoto -> skip
    END IF;

    -- Padre composito + figlio con stessa IVA (coerente per guard_iva).
    INSERT INTO catalogo.articoli (
        codice, descrizione, uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id, is_composito)
    VALUES ('ART_LRCGUARD_PAD_' || v_ts, 'Padre composito test guard listino',
            s.uom_id, s.tipo_id, s.gruppo_id, s.spesa_id, s.iva_id, TRUE)
    RETURNING id INTO v_p;

    INSERT INTO catalogo.articoli (
        codice, descrizione, uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id)
    VALUES ('ART_LRCGUARD_FIG_' || v_ts, 'Figlio test guard listino',
            s.uom_id, s.tipo_id, s.gruppo_id, s.spesa_id, s.iva_id)
    RETURNING id INTO v_f;

    -- BoM attiva aperta (valido_al NULL): copre script.fn_data_operativa() e qualsiasi data
    -- futura, cosi' la temporal FK non interferisce col test Guard 7.
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, obbligatorio,
        valido_dal, valido_al, attivo)
    VALUES (v_p, v_f, 1, TRUE, (script.fn_data_operativa() - 1), NULL, TRUE)
    RETURNING id INTO v_l;

    -- Versione BOZZA (obbligatoria per INSERT su listini_righe_componenti),
    -- finestra script.fn_data_operativa()..script.fn_data_operativa()+400:
    -- nasce BOZZA dal trigger.
    INSERT INTO vendite.listini_versioni(
        listino_id, codice_versione, valido_dal, valido_al, attivo)
    VALUES (s.listino_id, 'PGTAP_LRCGUARD_' || v_ts, script.fn_data_operativa(), script.fn_data_operativa() + 400, TRUE)
    RETURNING id INTO v_versione;

    INSERT INTO tmp_ctx VALUES (v_p, v_f, v_l, s.iva_id, v_versione);
END
$$;

-- =========================================================
-- 1) Precondizione
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_ctx) = 0
        THEN skip('1) Prerequisiti seed mancanti (uom/tipo/gruppo/spesa/iva/listino) — test 2..7 salteranno')
    ELSE ok(TRUE, '1) Precondizione: padre composito + figlio + BoM attiva + versione BOZZA creati')
END;

-- =========================================================
-- 2) Riga bundle VALIDA -> OK
-- Happy-path: blinda la rimozione del JOIN a_figlio (20260603-03).
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_ctx) = 0
        THEN skip('2) Dati non disponibili')
    ELSE (
        SELECT lives_ok(
            format(
                $sql$ INSERT INTO vendite.listini_righe_componenti(
                          listino_versione_id, articolo_componente_id,
                          articolo_padre_id, articolo_figlio_id,
                          prezzo, iva_id, valido_dal, valido_al, attivo)
                      VALUES (%s, %L::uuid, %L::uuid, %L::uuid,
                              50.00, %s, script.fn_data_operativa(), script.fn_data_operativa(), TRUE) $sql$,
                ctx.versione_id,
                ctx.articolo_componente_id, ctx.padre_id, ctx.figlio_id,
                ctx.iva_id
            ),
            '2) Riga bundle valida -> OK (regressione cleanup JOIN a_figlio)'
        )
        FROM tmp_ctx ctx
    )
END;

-- =========================================================
-- 3) Guard 1: articolo_componente_id inesistente -> raise (non trovato)
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_ctx) = 0
        THEN skip('3) Dati non disponibili')
    ELSE (
        SELECT throws_like(
            format(
                $sql$ INSERT INTO vendite.listini_righe_componenti(
                          listino_versione_id, articolo_componente_id,
                          articolo_padre_id, articolo_figlio_id,
                          prezzo, iva_id, valido_dal, valido_al, attivo)
                      VALUES (%s, '00000000-0000-0000-0000-0000000000aa'::uuid,
                              %L::uuid, %L::uuid,
                              50.00, %s, script.fn_data_operativa(), script.fn_data_operativa(), TRUE) $sql$,
                ctx.versione_id, ctx.padre_id, ctx.figlio_id, ctx.iva_id
            ),
            '%non trovato o non attivo%',
            '3) Guard 1: articolo_componente_id inesistente -> E_LISTINO_COMPONENTE_COERENZA_BOM'
        )
        FROM tmp_ctx ctx
    )
END;

-- =========================================================
-- 4) Guard 2: articolo_padre_id != ac.prodotto_id -> raise
-- Passo il figlio_id (articolo reale) come padre errato.
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_ctx) = 0
        THEN skip('4) Dati non disponibili')
    ELSE (
        SELECT throws_like(
            format(
                $sql$ INSERT INTO vendite.listini_righe_componenti(
                          listino_versione_id, articolo_componente_id,
                          articolo_padre_id, articolo_figlio_id,
                          prezzo, iva_id, valido_dal, valido_al, attivo)
                      VALUES (%s, %L::uuid, %L::uuid, %L::uuid,
                              50.00, %s, script.fn_data_operativa(), script.fn_data_operativa(), TRUE) $sql$,
                ctx.versione_id, ctx.articolo_componente_id, ctx.figlio_id, ctx.figlio_id,
                ctx.iva_id
            ),
            '%padre_id=%atteso=%',
            '4) Guard 2: articolo_padre_id incoerente -> E_LISTINO_COMPONENTE_COERENZA_BOM'
        )
        FROM tmp_ctx ctx
    )
END;

-- =========================================================
-- 5) Guard 3: articolo_figlio_id != ac.componente_id -> raise
-- Padre corretto, figlio = padre_id (articolo reale) errato.
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_ctx) = 0
        THEN skip('5) Dati non disponibili')
    ELSE (
        SELECT throws_like(
            format(
                $sql$ INSERT INTO vendite.listini_righe_componenti(
                          listino_versione_id, articolo_componente_id,
                          articolo_padre_id, articolo_figlio_id,
                          prezzo, iva_id, valido_dal, valido_al, attivo)
                      VALUES (%s, %L::uuid, %L::uuid, %L::uuid,
                              50.00, %s, script.fn_data_operativa(), script.fn_data_operativa(), TRUE) $sql$,
                ctx.versione_id, ctx.articolo_componente_id, ctx.padre_id, ctx.padre_id,
                ctx.iva_id
            ),
            '%figlio_id=%atteso=%',
            '5) Guard 3: articolo_figlio_id incoerente -> E_LISTINO_COMPONENTE_COERENZA_BOM'
        )
        FROM tmp_ctx ctx
    )
END;

-- =========================================================
-- 6) Guard 7: validita riga fuori dalla versione listino -> raise
-- versione = [script.fn_data_operativa(), script.fn_data_operativa()+400]; riga [+500, +600].
-- BoM aperta -> temporal FK ok; il trigger BEFORE (Guard 7) scatta prima.
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_ctx) = 0
        THEN skip('6) Dati non disponibili')
    ELSE (
        SELECT throws_like(
            format(
                $sql$ INSERT INTO vendite.listini_righe_componenti(
                          listino_versione_id, articolo_componente_id,
                          articolo_padre_id, articolo_figlio_id,
                          prezzo, iva_id, valido_dal, valido_al, attivo)
                      VALUES (%s, %L::uuid, %L::uuid, %L::uuid,
                              50.00, %s,
                              (script.fn_data_operativa() + 500)::date, (script.fn_data_operativa() + 600)::date, TRUE) $sql$,
                ctx.versione_id, ctx.articolo_componente_id, ctx.padre_id, ctx.figlio_id,
                ctx.iva_id
            ),
            '%non contenuta in versione%',
            '6) Guard 7: validita riga fuori dalla versione -> E_LISTINO_COMPONENTE_COERENZA_BOM'
        )
        FROM tmp_ctx ctx
    )
END;

-- =========================================================
-- 7) Guard 4 (listino) irraggiungibile per costruzione.
-- Guard 4 verifica padre.is_composito=TRUE, ma una riga listino esige una
-- BoM attiva (Guard 1) e il catalogo impedisce di rendere non-composito
-- un padre con BoM attiva (trgfn_articoli_guard_flags_struttura_bom_attiva
-- -> E_BOM_MODIFICA_VIETATA). Canarino: se il blocco sparisse, Guard 4
-- diventerebbe raggiungibile e questo test virerebbe rosso.
-- =========================================================
SELECT CASE
    WHEN (SELECT COUNT(*) FROM tmp_ctx) = 0
        THEN skip('7) Dati non disponibili')
    ELSE (
        SELECT throws_ok(
            format(
                $sql$ UPDATE catalogo.articoli SET is_composito = FALSE WHERE id = %L::uuid $sql$,
                ctx.padre_id
            ),
            NULL, NULL,
            '7) Guard 4 irraggiungibile: catalogo blocca is_composito=FALSE su padre di BoM attiva'
        )
        FROM tmp_ctx ctx
    )
END;

SELECT * FROM finish();
ROLLBACK;
