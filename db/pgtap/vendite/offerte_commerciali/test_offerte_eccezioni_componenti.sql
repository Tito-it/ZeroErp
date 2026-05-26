-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.offerte_commerciali_eccezioni_componenti
--       + fn_offerta_eccezione_componenti_init
--       + fn_offerta_eccezione_componenti_preview
--       + fn_push_offerta_a_contratto (copia componenti rev3)
-- ------------------------------------------------------------
-- Indice test (1..20):
--  1) has_table offerte_commerciali_eccezioni_componenti
--  2) has_column eccezione_offerta_id
--  3) has_column articolo_componente_id
--  4) has_column componente_id
--  5) has_column prezzo_unitario
--  6) has_column stato_approvazione_prezzo
--  7) has_pk pk_oce_comp
--  8) FK eccezione_offerta_id ON DELETE CASCADE
--  9) UNIQUE (eccezione_offerta_id, articolo_componente_id)
-- 10) trigger count >= 10 su offerte_commerciali_eccezioni_componenti
-- 11) trigger propaga_qta registrato su offerte_commerciali_eccezioni
-- 12) fn_init guard p_eccezione_id NULL → E_PARAMETRO_INVALIDO
-- 13) fn_init guard p_emittente_sr_id NULL → E_PARAMETRO_INVALIDO
-- 14) fn_init eccezione non trovata → E_PARAMETRO_INVALIDO
-- 15) fn_init articolo non composito → 0
-- 16) fn_init quantita NULL → 0 (consumo)
-- 17) fn_init idempotenza → 0 alla seconda chiamata [skip se no composito]
-- 18) fn_init happy path: componenti inseriti > 0   [skip se no composito]
-- 19) fn_init override: prezzo overriddato           [skip se no composito]
-- 20) fn_push copia componenti → contratti_righe_componenti [skip se no composito]
-- ------------------------------------------------------------

BEGIN;
SELECT plan(20);

-- ============================================================
-- Contesto dati-dipendenti (skip se assenti)
-- ============================================================
CREATE TEMP TABLE tmp_oce_ctx AS
SELECT
    -- Articolo composito con almeno un componente esposto e tutti opzionali
    -- (obbligatorio=FALSE esplicito): il fallback prezzo=0 del resolver
    -- è ammesso solo su componenti opzionali (COALESCE(obbligatorio,TRUE)).
    (SELECT a.id
       FROM catalogo.articoli a
      WHERE a.is_composito = TRUE
        AND EXISTS (
            SELECT 1 FROM catalogo.articoli_componenti ac
             WHERE ac.prodotto_id = a.id
               AND ac.esposto_in_fattura = TRUE
               AND COALESCE(ac.attivo, TRUE) = TRUE
        )
        AND NOT EXISTS (
            SELECT 1 FROM catalogo.articoli_componenti ac
             WHERE ac.prodotto_id = a.id
               AND ac.esposto_in_fattura = TRUE
               AND COALESCE(ac.attivo, TRUE) = TRUE
               AND COALESCE(ac.obbligatorio, TRUE) = TRUE
        )
      ORDER BY a.id LIMIT 1) AS articolo_composito_id,

    -- Articolo non composito (per test 15)
    (SELECT a.id
       FROM catalogo.articoli a
      WHERE COALESCE(a.is_composito, FALSE) = FALSE
      ORDER BY a.id LIMIT 1) AS articolo_semplice_id,

    -- Contesto billing/utility: BA senza tipi_utenze (evita guard tipo/classe)
    (SELECT ba.id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
      ORDER BY ba.id LIMIT 1) AS billing_account_id,

    (SELECT ba.istanza_utility_id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
      ORDER BY ba.id LIMIT 1) AS istanza_utility_id,

    (SELECT ba.utility_id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
      ORDER BY ba.id LIMIT 1) AS utility_id,

    (SELECT ef.id
       FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,

    (SELECT ef.soggetto_ruolo_id
       FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_sr_id,

    (SELECT l.id FROM vendite.listini l WHERE l.attivo IS TRUE ORDER BY l.id LIMIT 1)
        AS listino_id,

    (SELECT lv.id FROM vendite.listini_versioni lv
      WHERE lv.stato = 'ATTIVA' ORDER BY lv.id LIMIT 1)
        AS listino_versione_id,

    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA')
        AS stato_accettata_id;

-- Flag: dati composito disponibili?
CREATE TEMP TABLE tmp_oce_has_composito AS
SELECT (articolo_composito_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND emittente_sr_id IS NOT NULL) AS disponibile
  FROM tmp_oce_ctx;

-- ============================================================
-- Fixture: offerta con eccezioni semplice + composita + consumo
-- (solo se dati disponibili)
-- ============================================================
CREATE TEMP TABLE tmp_oce_ids (
    slot       text PRIMARY KEY,
    offerta_id bigint,
    eccezione_id bigint
);

DO $$
DECLARE
    v_ctx         record;
    v_off_id      bigint;
    v_off_consumo bigint;
    v_ecc_id      bigint;
BEGIN
    SELECT * INTO v_ctx FROM tmp_oce_ctx;

    IF v_ctx.billing_account_id IS NULL
       OR v_ctx.emittente_fiscale_id IS NULL
    THEN RETURN; END IF;

    -- Offerta in ACCETTATA (INSERT bypass trigger per stato terminale)
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT v_ctx.emittente_fiscale_id, v_ctx.billing_account_id,
           v_ctx.istanza_utility_id, v_ctx.utility_id,
           v_ctx.listino_id, v_ctx.listino_versione_id,
           DATE '2082-01-01', v_ctx.stato_accettata_id
    RETURNING id INTO v_off_id;

    -- Eccezione con articolo semplice (test 15)
    IF v_ctx.articolo_semplice_id IS NOT NULL THEN
        INSERT INTO vendite.offerte_commerciali_eccezioni (
            offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
            prezzo_unitario, quantita
        )
        VALUES (v_off_id, v_ctx.articolo_semplice_id, 'OVERRIDE', 'FISSA', 10.00, 1)
        RETURNING id INTO v_ecc_id;
        INSERT INTO tmp_oce_ids VALUES ('SEMPLICE', v_off_id, v_ecc_id);
    END IF;

    -- Eccezione con articolo composito (test 17-19)
    IF v_ctx.articolo_composito_id IS NOT NULL THEN
        INSERT INTO vendite.offerte_commerciali_eccezioni (
            offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
            prezzo_unitario, quantita
        )
        VALUES (v_off_id, v_ctx.articolo_composito_id, 'OVERRIDE',
                'DERIVATA_COMPONENTI', 0.00, 2)
        RETURNING id INTO v_ecc_id;
        INSERT INTO tmp_oce_ids VALUES ('COMPOSITA', v_off_id, v_ecc_id);
    END IF;

    -- Eccezione con quantita NULL (test 16) — offerta separata per evitare
    -- violazione uq_offerte_eccezioni_one_eccezione_per_articolo (OVERRIDE
    -- sullo stesso articolo composito già inserito in v_off_id).
    IF v_ctx.articolo_composito_id IS NOT NULL THEN
        INSERT INTO vendite.offerte_commerciali (
            emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
            listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
        )
        SELECT v_ctx.emittente_fiscale_id, v_ctx.billing_account_id,
               v_ctx.istanza_utility_id, v_ctx.utility_id,
               v_ctx.listino_id, v_ctx.listino_versione_id,
               DATE '2082-01-01', v_ctx.stato_accettata_id
        RETURNING id INTO v_off_consumo;

        INSERT INTO vendite.offerte_commerciali_eccezioni (
            offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
            prezzo_unitario, quantita
        )
        VALUES (v_off_consumo, v_ctx.articolo_composito_id, 'OVERRIDE',
                'LETTURE', 0.00, NULL)
        RETURNING id INTO v_ecc_id;
        INSERT INTO tmp_oce_ids VALUES ('CONSUMO', v_off_consumo, v_ecc_id);
    END IF;
END;
$$;

-- ============================================================
-- TEST 1) has_table
-- ============================================================
SELECT has_table(
    'vendite',
    'offerte_commerciali_eccezioni_componenti',
    '1) tabella vendite.offerte_commerciali_eccezioni_componenti esiste'
);

-- ============================================================
-- TEST 2-6) has_column
-- ============================================================
SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'eccezione_offerta_id', '2) colonna eccezione_offerta_id esiste');

SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'articolo_componente_id', '3) colonna articolo_componente_id esiste');

SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'componente_id', '4) colonna componente_id esiste');

SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'prezzo_unitario', '5) colonna prezzo_unitario esiste');

SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'stato_approvazione_prezzo', '6) colonna stato_approvazione_prezzo esiste');

-- ============================================================
-- TEST 7) has_pk
-- ============================================================
SELECT has_pk('vendite','offerte_commerciali_eccezioni_componenti',
    '7) PK pk_oce_comp esiste');

-- ============================================================
-- TEST 8) FK CASCADE verso offerte_commerciali_eccezioni
-- ============================================================
SELECT col_is_fk(
    'vendite', 'offerte_commerciali_eccezioni_componenti',
    'eccezione_offerta_id',
    '8) eccezione_offerta_id e'' FK verso offerte_commerciali_eccezioni'
);

-- ============================================================
-- TEST 9) UNIQUE (eccezione_offerta_id, articolo_componente_id)
-- ============================================================
SELECT has_unique(
    'vendite', 'offerte_commerciali_eccezioni_componenti',
    '9) UNIQUE uq_oce_comp_eccezione_art_comp esiste'
);

-- ============================================================
-- TEST 10) Trigger count >= 10 su offerte_commerciali_eccezioni_componenti
-- ============================================================
SELECT ok(
    (SELECT COUNT(*)
       FROM information_schema.triggers
      WHERE event_object_schema = 'vendite'
        AND event_object_table  = 'offerte_commerciali_eccezioni_componenti'
    ) >= 10,
    '10) almeno 10 trigger registrati su offerte_commerciali_eccezioni_componenti'
);

-- ============================================================
-- TEST 11) Trigger propaga_qta su offerte_commerciali_eccezioni
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM information_schema.triggers
         WHERE event_object_schema = 'vendite'
           AND event_object_table  = 'offerte_commerciali_eccezioni'
           AND trigger_name LIKE '%propaga_qta%'
    ),
    '11) trigger propaga_qta registrato su offerte_commerciali_eccezioni'
);

-- ============================================================
-- TEST 12) fn_init guard p_eccezione_id NULL → E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_like(
    $$SELECT vendite.fn_offerta_eccezione_componenti_init(NULL, 1, CURRENT_DATE)$$,
    '%Parametro non valido%',
    '12) fn_init(NULL, 1, date): guard p_eccezione_id → E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- TEST 13) fn_init guard p_emittente_sr_id NULL → E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_like(
    $$SELECT vendite.fn_offerta_eccezione_componenti_init(1, NULL, CURRENT_DATE)$$,
    '%Parametro non valido%',
    '13) fn_init(1, NULL, date): guard p_emittente_sr_id → E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- TEST 14) fn_init eccezione non trovata → E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_like(
    $$SELECT vendite.fn_offerta_eccezione_componenti_init(999999999, 1, CURRENT_DATE)$$,
    '%Parametro non valido%',
    '14) fn_init(999999999, 1, date): eccezione non trovata → E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- TEST 15) fn_init articolo non composito → 0
-- ============================================================
SELECT CASE
    WHEN (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'SEMPLICE') IS NOT NULL
    THEN is(
        vendite.fn_offerta_eccezione_componenti_init(
            (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'SEMPLICE'),
            (SELECT emittente_sr_id FROM tmp_oce_ctx),
            CURRENT_DATE
        ),
        0,
        '15) fn_init su articolo non composito → 0 (no-op CASO B)'
    )
    ELSE skip('15) skip: nessun articolo semplice disponibile')
END;

-- ============================================================
-- TEST 16) fn_init quantita NULL → 0 (consumo)
-- ============================================================
SELECT CASE
    WHEN (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'CONSUMO') IS NOT NULL
    THEN is(
        vendite.fn_offerta_eccezione_componenti_init(
            (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'CONSUMO'),
            (SELECT emittente_sr_id FROM tmp_oce_ctx),
            CURRENT_DATE
        ),
        0,
        '16) fn_init su eccezione con quantita NULL → 0 (consumo no-op)'
    )
    ELSE skip('16) skip: nessuna eccezione consumo disponibile')
END;

-- Setup: prima chiamata fn_init (popola componenti per test 17-19)
DO $$
BEGIN
    IF (SELECT disponibile FROM tmp_oce_has_composito) THEN
        PERFORM vendite.fn_offerta_eccezione_componenti_init(
            (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA'),
            (SELECT emittente_sr_id FROM tmp_oce_ctx),
            DATE '2082-01-01'
        );
    END IF;
END $$;

-- ============================================================
-- TEST 17) fn_init idempotenza → 0 alla seconda chiamata
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_oce_has_composito)
    THEN is(
        vendite.fn_offerta_eccezione_componenti_init(
            (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA'),
            (SELECT emittente_sr_id FROM tmp_oce_ctx),
            DATE '2082-01-01'
        ),
        0,
        '17) fn_init idempotenza: seconda chiamata → 0'
    )
    ELSE skip('17) skip: nessun articolo composito disponibile')
END;

-- ============================================================
-- TEST 18) fn_init happy path: componenti inseriti > 0
-- (dopo il test 17 che ha già chiamato fn_init sulla COMPOSITA)
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_oce_has_composito)
    THEN ok(
        (SELECT COUNT(*) FROM vendite.offerte_commerciali_eccezioni_componenti
          WHERE eccezione_offerta_id =
                (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA')
        ) > 0,
        '18) fn_init happy path: componenti inseriti > 0 dopo prima chiamata'
    )
    ELSE skip('18) skip: nessun articolo composito disponibile')
END;

-- Setup test 19: crea eccezione COMPOSITA-OVR e chiama fn_init con override
DO $$
DECLARE
    v_ovr_ecc_id  bigint;
    v_off_id      bigint;
    v_bom_id      uuid;
BEGIN
    IF NOT (SELECT disponibile FROM tmp_oce_has_composito) THEN RETURN; END IF;

    SELECT offerta_id INTO v_off_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA';

    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
        prezzo_unitario, quantita
    )
    VALUES (v_off_id, (SELECT articolo_composito_id FROM tmp_oce_ctx),
            'AGGIUNTA', 'DERIVATA_COMPONENTI', 0.00, 3)
    RETURNING id INTO v_ovr_ecc_id;

    INSERT INTO tmp_oce_ids VALUES ('COMPOSITA-OVR', v_off_id, v_ovr_ecc_id);

    SELECT ac.id INTO v_bom_id
      FROM catalogo.articoli_componenti ac
     WHERE ac.prodotto_id = (SELECT articolo_composito_id FROM tmp_oce_ctx)
       AND ac.esposto_in_fattura = TRUE
       AND COALESCE(ac.attivo, TRUE) = TRUE
       AND ac.validita @> DATE '2082-01-01'
     ORDER BY ac.id LIMIT 1;

    PERFORM vendite.fn_offerta_eccezione_componenti_init(
        v_ovr_ecc_id,
        (SELECT emittente_sr_id FROM tmp_oce_ctx),
        DATE '2082-01-01',
        jsonb_build_object(v_bom_id::text, 99999)
    );
END $$;

-- ============================================================
-- TEST 19) fn_init override: verifica che il prezzo override sia applicato
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_oce_has_composito)
    THEN ok(
        EXISTS (
            SELECT 1
              FROM vendite.offerte_commerciali_eccezioni_componenti
             WHERE eccezione_offerta_id =
                   (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA-OVR')
               AND prezzo_unitario = 99999
               AND origine_prezzo  = 'MANUALE'
        ),
        '19) fn_init override: prezzo 99999 applicato con origine_prezzo=MANUALE'
    )
    ELSE skip('19) skip: nessun articolo composito disponibile')
END;

-- Setup test 20: esegue push offerta → contratto
DO $$
BEGIN
    IF NOT (
        (SELECT disponibile FROM tmp_oce_has_composito)
        AND (SELECT COUNT(*) FROM vendite.offerte_commerciali_eccezioni_componenti
              WHERE eccezione_offerta_id =
                    (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA')
            ) > 0
    ) THEN RETURN; END IF;

    PERFORM vendite.fn_push_offerta_a_contratto(
        (SELECT offerta_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA'),
        NULL
    );
END $$;

-- ============================================================
-- TEST 20) fn_push copia componenti → contratti_righe_componenti
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_oce_has_composito)
       AND (SELECT COUNT(*) FROM vendite.offerte_commerciali_eccezioni_componenti
             WHERE eccezione_offerta_id =
                   (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA')
           ) > 0
    THEN ok(
        (SELECT COUNT(*)
           FROM vendite.contratti_righe_componenti crc
           JOIN vendite.contratti_righe cr ON cr.id = crc.riga_contratto_id
           JOIN vendite.contratti c ON c.id = cr.contratto_id
          WHERE c.offerta_id =
                (SELECT offerta_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA')
        ) > 0,
        '20) fn_push rev3: contratti_righe_componenti copiati dal push offerta→contratto'
    )
    ELSE skip('20) skip: componenti offerta non disponibili per test push')
END;

SELECT * FROM finish();
ROLLBACK;
