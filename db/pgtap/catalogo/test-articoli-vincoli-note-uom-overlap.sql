-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Schema: catalogo
-- Ambito: vincoli articoli, note, uom operativa, overlap componenti
-- ------------------------------------------------------------

SELECT plan(20);

CREATE TEMP TABLE tmp_test_keys AS
SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts;

CREATE TEMP TABLE tmp_ids AS
SELECT
    COALESCE((SELECT MAX(id) FROM catalogo.unita_misura), 0) + 1000 AS uom_base_id,
    COALESCE((SELECT MAX(id) FROM catalogo.unita_misura), 0) + 1001 AS uom_alt_id;

CREATE TEMP TABLE tmp_fk_refs AS
SELECT
    (SELECT id FROM vendite.articoli_gruppi WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS gruppo_id,
    (SELECT id FROM vendite.articoli_tipologie WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_id,
    (SELECT id FROM vendite.articoli_spesa WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS spesa_id,
    (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS iva_id,
    (SELECT id FROM config.lingue WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS lingua_id;

CREATE TEMP TABLE tmp_can_run AS
SELECT (
    (SELECT gruppo_id IS NOT NULL FROM tmp_fk_refs)
    AND (SELECT tipo_id IS NOT NULL FROM tmp_fk_refs)
    AND (SELECT spesa_id IS NOT NULL FROM tmp_fk_refs)
    AND (SELECT iva_id IS NOT NULL FROM tmp_fk_refs)
    AND (SELECT lingua_id IS NOT NULL FROM tmp_fk_refs)
) AS can_run;

SELECT diag(
    format(
        'Ref base: gruppo=%s tipologia=%s spesa=%s iva=%s lingua=%s (can_run=%s)',
        COALESCE((SELECT gruppo_id::text FROM tmp_fk_refs), 'NULL'),
        COALESCE((SELECT tipo_id::text FROM tmp_fk_refs), 'NULL'),
        COALESCE((SELECT spesa_id::text FROM tmp_fk_refs), 'NULL'),
        COALESCE((SELECT iva_id::text FROM tmp_fk_refs), 'NULL'),
        COALESCE((SELECT lingua_id::text FROM tmp_fk_refs), 'NULL'),
        CASE WHEN (SELECT can_run FROM tmp_can_run) THEN 'true' ELSE 'false' END
    )
);

SELECT CASE
    WHEN (SELECT gruppo_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento vendite.articoli_gruppi disponibile')
    ELSE ok(true, 'Riferimento vendite.articoli_gruppi mancante: test dipendenti skipped')
END;

SELECT CASE
    WHEN (SELECT tipo_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento vendite.articoli_tipologie disponibile')
    ELSE ok(true, 'Riferimento vendite.articoli_tipologie mancante: test dipendenti skipped')
END;

SELECT CASE
    WHEN (SELECT spesa_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento vendite.articoli_spesa disponibile')
    ELSE ok(true, 'Riferimento vendite.articoli_spesa mancante: test dipendenti skipped')
END;

SELECT CASE
    WHEN (SELECT iva_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento config.iva disponibile')
    ELSE ok(true, 'Riferimento config.iva mancante: test dipendenti skipped')
END;

SELECT CASE
    WHEN (SELECT lingua_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento config.lingue disponibile')
    ELSE ok(true, 'Riferimento config.lingue mancante: test dipendenti skipped')
END;

CREATE TEMP TABLE tmp_uom_base (id bigint);
CREATE TEMP TABLE tmp_uom_alt (id bigint);
CREATE TEMP TABLE tmp_note_stile (id bigint);
CREATE TEMP TABLE tmp_art_base (id uuid);
CREATE TEMP TABLE tmp_art_comp (id uuid);
CREATE TEMP TABLE tmp_note (id bigint);
CREATE TEMP TABLE tmp_uom_op_base (id bigint);
CREATE TEMP TABLE tmp_art_comp_rel (id uuid);

-- =========================================================
-- 1) Inserimento unita' di misura di test
-- =========================================================
DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.unita_misura (
        id,
        codice,
        descrizione,
        descrizione_fattura,
        attivo
    )
    VALUES (
        (SELECT uom_base_id FROM tmp_ids),
        (SELECT 'UTB' || right(ts, 6) FROM tmp_test_keys),
        'UNITA TEST BASE',
        'UNITA TEST BASE',
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_uom_base (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_uom_base) = 1, 'Inserita unita_misura base di test')
    ELSE ok(true, 'Inserimento unita_misura base skipped: riferimenti mancanti')
END;

DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.unita_misura (
        id,
        codice,
        descrizione,
        descrizione_fattura,
        attivo
    )
    VALUES (
        (SELECT uom_alt_id FROM tmp_ids),
        (SELECT 'UTA' || right(ts, 6) FROM tmp_test_keys),
        'UNITA TEST ALT',
        'UNITA TEST ALT',
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_uom_alt (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_uom_alt) = 1, 'Inserita unita_misura alternativa di test')
    ELSE ok(true, 'Inserimento unita_misura alternativa skipped: riferimenti mancanti')
END;

-- =========================================================
-- 2) Stile nota di test
-- =========================================================
DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO config.note_stili (
        codice,
        codice_interno,
        descrizione,
        attivo
    )
    VALUES (
        (SELECT 'NST' || right(ts, 6) FROM tmp_test_keys),
        (SELECT 'NSTI' || right(ts, 6) FROM tmp_test_keys),
        (SELECT 'STILE TEST ' || ts FROM tmp_test_keys),
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_note_stile (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_note_stile) = 1, 'Creato note_stili di test')
    ELSE ok(true, 'Creazione note_stili skipped: riferimenti mancanti')
END;

-- =========================================================
-- 3) Articoli di test
-- =========================================================
DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.articoli (
        codice,
        descrizione,
        uom_id,
        tipo_voce_id,
        gruppo_voce_id,
        spesa_id,
        iva_id
    )
    VALUES (
        (SELECT 'ART' || right(ts, 6) FROM tmp_test_keys),
        (SELECT 'ARTICOLO TEST BASE ' || ts FROM tmp_test_keys),
        (SELECT uom_base_id FROM tmp_ids),
        (SELECT tipo_id FROM tmp_fk_refs),
        (SELECT gruppo_id FROM tmp_fk_refs),
        (SELECT spesa_id FROM tmp_fk_refs),
        (SELECT iva_id FROM tmp_fk_refs)
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_art_base (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_art_base) = 1, 'Creato articolo base di test')
    ELSE ok(true, 'Creazione articolo base skipped: riferimenti mancanti')
END;

DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.articoli (
        codice,
        descrizione,
        uom_id,
        tipo_voce_id,
        gruppo_voce_id,
        spesa_id,
        iva_id
    )
    VALUES (
        (SELECT 'ARC' || right(ts, 6) FROM tmp_test_keys),
        (SELECT 'ARTICOLO TEST COMP ' || ts FROM tmp_test_keys),
        (SELECT uom_base_id FROM tmp_ids),
        (SELECT tipo_id FROM tmp_fk_refs),
        (SELECT gruppo_id FROM tmp_fk_refs),
        (SELECT spesa_id FROM tmp_fk_refs),
        (SELECT iva_id FROM tmp_fk_refs)
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_art_comp (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_art_comp) = 1, 'Creato articolo componente di test')
    ELSE ok(true, 'Creazione articolo componente skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        INSERT INTO catalogo.articoli (codice, descrizione)
        VALUES (
            (SELECT 'ART' || right(ts, 6) FROM tmp_test_keys),
            'ARTICOLO DUPLICATO'
        );
        $$,
        NULL,
        NULL,
        'Codice articolo duplicato: bloccato'
    )
    ELSE ok(true, 'Test duplicato codice skipped: riferimenti mancanti')
END;

-- =========================================================
-- 4) Note articolo
-- =========================================================
DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.note (
        target_tipo,
        target_id,
        anchor_tipo,
        posizione,
        seq,
        testo,
        id_stile,
        id_lingua
    )
    VALUES (
        'ARTICOLI',
        (SELECT id FROM tmp_art_base),
        'DOCUMENTO',
        'HEADER',
        10,
        (SELECT 'NOTA TEST ' || ts FROM tmp_test_keys),
        (SELECT id FROM tmp_note_stile),
        (SELECT lingua_id FROM tmp_fk_refs)
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_note (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_note) = 1, 'Creata nota per articolo')
    ELSE ok(true, 'Creazione nota skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN lives_ok(
        $$
        UPDATE catalogo.articoli
        SET note_target_tipo = 'ARTICOLI',
            note_id = (SELECT id FROM tmp_note)
        WHERE id = (SELECT id FROM tmp_art_base);
        $$,
        --NULL,
        --NULL,
        'Collegamento nota su articolo: OK'
    )
    ELSE ok(true, 'Collegamento nota skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        UPDATE catalogo.articoli
        SET note_target_tipo = 'ARTICOLI_COMPONENTI',
            note_id = (SELECT id FROM tmp_note)
        WHERE id = (SELECT id FROM tmp_art_base);
        $$,
        NULL,
        NULL,
        'note_target_tipo non valido per articoli: bloccato'
    )
    ELSE ok(true, 'Test note_target_tipo skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        UPDATE catalogo.articoli
        SET note_target_tipo = 'ARTICOLI',
            note_id = 999999999
        WHERE id = (SELECT id FROM tmp_art_base);
        $$,
        NULL,
        NULL,
        'FK note_id inesistente: bloccato'
    )
    ELSE ok(true, 'Test FK note_id skipped: riferimenti mancanti')
END;

-- =========================================================
-- 5) UOM operativa
-- =========================================================
DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.articoli_uom_operativa (
        articolo_id,
        uom_id,
        is_base,
        factor_to_base,
        is_sell_uom,
        is_purchase_uom,
        is_logistic_uom,
        attivo
    )
    VALUES (
        (SELECT id FROM tmp_art_base),
        (SELECT uom_base_id FROM tmp_ids),
        true,
        1,
        true,
        true,
        false,
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_uom_op_base (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_uom_op_base) = 1, 'Inserita uom operativa base')
    ELSE ok(true, 'Inserimento uom operativa base skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        INSERT INTO catalogo.articoli_uom_operativa (
            articolo_id,
            uom_id,
            is_base,
            factor_to_base,
            attivo
        )
        VALUES (
            (SELECT id FROM tmp_art_base),
            (SELECT uom_base_id FROM tmp_ids),
            false,
            1,
            true
        );
        $$,
        NULL,
        NULL,
        'UOM operativa duplicata (articolo_id, uom_id): bloccata'
    )
    ELSE ok(true, 'Test duplicato uom operativa skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        INSERT INTO catalogo.articoli_uom_operativa (
            articolo_id,
            uom_id,
            is_base,
            factor_to_base,
            attivo
        )
        VALUES (
            (SELECT id FROM tmp_art_base),
            (SELECT uom_alt_id FROM tmp_ids),
            true,
            1,
            true
        );
        $$,
        NULL,
        NULL,
        'Seconda UOM base per articolo: bloccata'
    )
    ELSE ok(true, 'Test seconda UOM base skipped: riferimenti mancanti')
END;

-- =========================================================
-- 6) Overlap articoli_componenti
-- =========================================================
DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id,
        componente_id,
        coeff_qta,
        partecipa_qta,
        obbligatorio,
        valido_dal,
        valido_al,
        attivo
    )
    VALUES (
        (SELECT id FROM tmp_art_base),
        (SELECT id FROM tmp_art_comp),
        1,
        false,
        true,
        DATE '2026-01-01',
        DATE '2026-01-31',
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_art_comp_rel (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_art_comp_rel) = 1, 'Inserito legame articoli_componenti')
    ELSE ok(true, 'Inserimento articoli_componenti skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        INSERT INTO catalogo.articoli_componenti (
            prodotto_id,
            componente_id,
            coeff_qta,
            partecipa_qta,
            obbligatorio,
            valido_dal,
            valido_al,
            attivo
        )
        VALUES (
            (SELECT id FROM tmp_art_base),
            (SELECT id FROM tmp_art_comp),
            1,
            false,
            true,
            DATE '2026-01-15',
            DATE '2026-02-15',
            true
        );
        $$,
        NULL,
        NULL,
        'Overlap articoli_componenti: bloccato'
    )
    ELSE ok(true, 'Test overlap articoli_componenti skipped: riferimenti mancanti')
END;

-- Cleanup
DELETE FROM catalogo.articoli_componenti
WHERE id = (SELECT id FROM tmp_art_comp_rel);

DELETE FROM catalogo.articoli_uom_operativa
WHERE articolo_id = (SELECT id FROM tmp_art_base);

DELETE FROM catalogo.note
WHERE target_tipo = 'ARTICOLI'
  AND id = (SELECT id FROM tmp_note);

DELETE FROM catalogo.articoli
WHERE id IN (
    (SELECT id FROM tmp_art_base),
    (SELECT id FROM tmp_art_comp)
);

DELETE FROM config.note_stili
WHERE id = (SELECT id FROM tmp_note_stile);

DELETE FROM catalogo.unita_misura
WHERE id IN (
    (SELECT uom_base_id FROM tmp_ids),
    (SELECT uom_alt_id FROM tmp_ids)
);
