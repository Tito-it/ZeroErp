-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vincoli e comportamenti base su vendite.attivita_fatturabili
--
-- Elenco test:
-- 1) Riferimento catalogo.articoli presente
-- 2) Riferimento anagrafiche.istanze_utilities presente
-- 3) Riferimento config.sorgenti presente
-- 4) Riferimento catalogo.unita_misura presente
-- 5) Sorgente configurata con target valido (per guard polimorfo)
-- 6) Inserimento con quantita negativa consentito
-- 7) Quantita negativa mantenuta
-- 8) Default approvato = false
-- 9) Default fatturato = false
-- 10) Default sospesa = false
-- 11) Default lock_in_fatturazione = false
-- 12) Default storicizza = true
-- 13) Default factor_to_base = 1
-- 14) Default sorgente_riga = 0
-- 15) Normalizzazione competenza_mese al primo del mese
-- 16) Check competenza_data >= data_attivita
-- 17) NOT NULL quantita
-- 18) FK su articolo_id
-- 19) Inserimento riga con sorgente_tipo_id e sorgente_uid/sorgente_riga validi
-- 20) Unicita parziale su (sorgente_tipo_id, sorgente_uid)
-- 21) Riferimento config.note_stili presente
-- 22) Inserimento nota su vendite.note (target ATTIVITAFT)
-- 23) Nota presente in partizione vendite.note_attivita_fatturabili
-- ------------------------------------------------------------

SELECT plan(23);

-- ============================================================
-- 0) Costanti e riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_af AS
SELECT
    'pgtap_attivita_fatturabili'::text AS test_scope,
    uuidv7() AS sorgente_uid_unica;

CREATE TEMP TABLE tmp_refs_af AS
SELECT
    (SELECT id
       FROM catalogo.articoli
      WHERE attivo IS TRUE
      ORDER BY data_insert DESC NULLS LAST
      LIMIT 1) AS articolo_id,
    (SELECT id
       FROM anagrafiche.istanze_utilities
      ORDER BY data_insert DESC NULLS LAST
      LIMIT 1) AS istanza_utility_id,
    (SELECT id
       FROM config.sorgenti
      WHERE attivo IS TRUE
      ORDER BY id
      LIMIT 1) AS sorgente_tipo_id,
    (SELECT id
       FROM catalogo.unita_misura
      WHERE attivo IS TRUE
      ORDER BY id
      LIMIT 1) AS uom_id;

CREATE TEMP TABLE tmp_note_stile AS
SELECT id AS id_stile
FROM config.note_stili
WHERE attivo IS TRUE
ORDER BY id
LIMIT 1;

CREATE TEMP TABLE tmp_sorgente_cfg (
    sorgente_tipo_id bigint,
    key_selector text,
    sorgente_riga bigint,
    sorgente_uid uuid
);

DO $$
DECLARE
    r record;
    v_id bigint;
    v_uid uuid;
BEGIN
    SELECT id, target_table, key_selector
      INTO r
      FROM config.sorgenti
     WHERE id = 1
       AND attivo IS TRUE
       AND target_table IS NOT NULL
       AND key_selector IN ('id', 'uid');

    IF r.id IS NULL THEN
        RETURN;
    END IF;

    v_id := NULL;
    v_uid := NULL;

    IF r.key_selector = 'id' THEN
        EXECUTE format('SELECT id FROM %s ORDER BY 1 LIMIT 1', r.target_table::text)
          INTO v_id;
        IF v_id IS NOT NULL THEN
            INSERT INTO tmp_sorgente_cfg
            VALUES (r.id, r.key_selector, v_id, NULL);
        END IF;
    ELSE
        EXECUTE format('SELECT uid FROM %s ORDER BY 1 LIMIT 1', r.target_table::text)
          INTO v_uid;
        IF v_uid IS NOT NULL THEN
            INSERT INTO tmp_sorgente_cfg
            VALUES (r.id, r.key_selector, NULL, v_uid);
        END IF;
    END IF;
END $$;

SELECT ok(
    (SELECT articolo_id FROM tmp_refs_af) IS NOT NULL,
    'Riferimento catalogo.articoli presente'
);

SELECT ok(
    (SELECT istanza_utility_id FROM tmp_refs_af) IS NOT NULL,
    'Riferimento anagrafiche.istanze_utilities presente'
);

SELECT ok(
    (SELECT sorgente_tipo_id FROM tmp_refs_af) IS NOT NULL,
    'Riferimento config.sorgenti presente'
);

SELECT ok(
    (SELECT uom_id FROM tmp_refs_af) IS NOT NULL,
    'Riferimento catalogo.unita_misura presente'
);

SELECT ok(
    (SELECT id_stile FROM tmp_note_stile) IS NOT NULL,
    'Riferimento config.note_stili presente'
);

SELECT ok(
    (SELECT count(*) FROM tmp_sorgente_cfg) = 1,
    'Sorgente id=1 configurata con target valido'
);

-- ============================================================
-- 1) Inserimento base con quantita negativa (ammessa)
-- ============================================================
CREATE TEMP TABLE tmp_attivita_base AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        data_attivita,
        quantita,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        current_date,
        -5,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_refs_af r,
         tmp_costanti_af k
    RETURNING
        id,
        quantita,
        approvato,
        fatturato,
        sospesa,
        lock_in_fatturazione,
        storicizza,
        factor_to_base,
        sorgente_riga
)
SELECT * FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_attivita_base),
    1,
    'Inserita attivita con quantita negativa'
);

SELECT is(
    (SELECT quantita::numeric FROM tmp_attivita_base),
    -5::numeric,
    'Quantita negativa mantenuta'
);

SELECT is(
    (SELECT approvato FROM tmp_attivita_base),
    false,
    'Default approvato = false'
);

SELECT is(
    (SELECT fatturato FROM tmp_attivita_base),
    false,
    'Default fatturato = false'
);

SELECT is(
    (SELECT sospesa FROM tmp_attivita_base),
    false,
    'Default sospesa = false'
);

SELECT is(
    (SELECT lock_in_fatturazione FROM tmp_attivita_base),
    false,
    'Default lock_in_fatturazione = false'
);

SELECT is(
    (SELECT storicizza FROM tmp_attivita_base),
    true,
    'Default storicizza = true'
);

SELECT is(
    (SELECT factor_to_base::numeric FROM tmp_attivita_base),
    1::numeric,
    'Default factor_to_base = 1'
);

SELECT is(
    (SELECT sorgente_riga::bigint FROM tmp_attivita_base),
    0::bigint,
    'Default sorgente_riga = 0'
);

-- ============================================================
-- 1b) Note su vendite.note e partizione note_attivita_fatturabili
-- ============================================================
CREATE TEMP TABLE tmp_note_attivita AS
WITH ins AS (
    INSERT INTO vendite.note (
        target_tipo,
        target_id,
        target_riga_id,
        anchor_tipo,
        posizione,
        seq,
        testo,
        visibile,
        solo_stampa,
        meta,
        id_stile,
        id_lingua
    )
    SELECT
        'ATTIVITAFT',
        a.id,
        a.id,
        'RIGA',
        'BEFORE',
        10,
        'Nota test attivita fatturabili',
        true,
        false,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'note_attivita'),
        s.id_stile,
        NULL
    FROM tmp_attivita_base a,
         tmp_costanti_af k,
         tmp_note_stile s
    RETURNING id, target_tipo
)
SELECT * FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_note_attivita),
    1,
    'Inserita nota su vendite.note (ATTIVITAFT)'
);

SELECT is(
    (SELECT count(*)::int
       FROM vendite.note_attivita_fatturabili n
      WHERE n.id = (SELECT id FROM tmp_note_attivita)
        AND n.target_tipo = 'ATTIVITAFT'),
    1,
    'Nota presente in partizione note_attivita_fatturabili'
);

-- ============================================================
-- 2) Normalizzazione competenza_mese
-- ============================================================
CREATE TEMP TABLE tmp_attivita_competenza AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        data_attivita,
        quantita,
        competenza_mese,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        date '2025-01-15',
        10,
        date '2025-01-20',
        jsonb_build_object('test_scope', k.test_scope, 'case', 'competenza_norm')
    FROM tmp_refs_af r,
         tmp_costanti_af k
    RETURNING id, competenza_mese
)
SELECT * FROM ins;

SELECT is(
    (SELECT competenza_mese FROM tmp_attivita_competenza),
    date '2025-01-01',
    'Competenza_mese normalizzata al primo del mese'
);

-- ============================================================
-- 3) Check competenza_data >= data_attivita
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        data_attivita,
        quantita,
        competenza_data
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        date '2025-02-01',
        1,
        date '2025-01-31'
    FROM tmp_refs_af r;
    $$,
    '23514',
    NULL,
    'Check competenza_data >= data_attivita'
);

-- ============================================================
-- 4) NOT NULL quantita
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        data_attivita,
        quantita
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        current_date,
        NULL
    FROM tmp_refs_af r;
    $$,
    '23502',
    NULL,
    'Quantita NOT NULL'
);

-- ============================================================
-- 5) FK articolo_id inesistente
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        data_attivita,
        quantita
    )
    SELECT
        uuidv7(),
        r.istanza_utility_id,
        current_date,
        1
    FROM tmp_refs_af r;
    $$,
    '23503',
    NULL,
    'FK violation su articolo_id'
);

-- ============================================================
-- 6) Unicita parziale sorgente_tipo_id + sorgente_uid
-- ============================================================
CREATE TEMP TABLE tmp_attivita_sorgente AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        data_attivita,
        quantita,
        sorgente_tipo_id,
        sorgente_riga,
        sorgente_uid,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        current_date,
        1,
        s.sorgente_tipo_id,
        CASE WHEN s.key_selector = 'id' THEN s.sorgente_riga ELSE NULL END,
        CASE WHEN s.key_selector = 'uid' THEN s.sorgente_uid ELSE k.sorgente_uid_unica END,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'unique_sorgente')
    FROM tmp_refs_af r,
         tmp_sorgente_cfg s,
         tmp_costanti_af k
    RETURNING id
)
SELECT * FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_attivita_sorgente),
    1,
    'Inserita riga con sorgente_tipo_id e sorgente_uid'
);

SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        data_attivita,
        quantita,
        sorgente_tipo_id,
        sorgente_riga,
        sorgente_uid
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        current_date,
        2,
        s.sorgente_tipo_id,
        CASE WHEN s.key_selector = 'id' THEN s.sorgente_riga ELSE NULL END,
        CASE WHEN s.key_selector = 'uid' THEN s.sorgente_uid ELSE k.sorgente_uid_unica END
    FROM tmp_refs_af r,
         tmp_sorgente_cfg s,
         tmp_costanti_af k;
    $$,
    '23505',
    NULL,
    'Unicita sorgente_tipo_id + sorgente_uid'
);

-- Cleanup
DELETE FROM vendite.note
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

DELETE FROM vendite.attivita_fatturabili
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);
