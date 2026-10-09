-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.offerte_commerciali_eccezioni_componenti
--       + fn_offerta_eccezione_componenti_init
--       + fn_offerta_eccezione_componenti_preview
--       + fn_push_offerta_a_contratto (copia componenti rev3)
-- ------------------------------------------------------------
-- Indice test (1..26):
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
-- 14) fn_init eccezione non trovata → E_OFFERTA_ECCEZIONE_NON_TROVATA
-- 15) fn_init articolo non composito → 0
-- 16) fn_init quantita NULL → 0 (consumo)
-- 17) fn_init idempotenza → 0 alla seconda chiamata [skip se no composito]
-- 18) fn_init happy path: componenti inseriti > 0   [skip se no composito]
-- 19) fn_init override: prezzo overriddato           [skip se no composito]
-- 20) fn_push copia componenti → contratti_righe_componenti [skip se no composito]
-- 21) fn_preview esiste (has_function)
-- 22) fn_preview articolo semplice → 0 righe        [skip se no ctx]
-- 23) fn_preview articolo composito → righe > 0,
--     colonne obbligatorio+esposizione_in_fattura accessibili [skip se no composito valido]
-- 24) fn_preview COUNT = COUNT componenti attivi validi
--     (nessun filtro esposto_in_fattura)              [skip se no composito valido]
-- 25) fn_preview quantita_componente = coeff_qta * quantita_padre [skip se no composito valido]
-- 26) fn_preview include componenti esposto=FALSE     [skip se nessun componente non-esposto]
-- 27) fn_init guard ESCLUSIONE composito → 0, nessun componente,
--     padre conserva prezzo_unitario NULL                [skip se no composito]
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(27);

-- ============================================================
-- Contesto dati-dipendenti (skip se assenti)
-- ============================================================
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe
--   stanno nel PERIMETRO dell'articolo, e la tipologia dell'articolo dev'essere fra quelle
--   della utility del cliente. I due articoli si scelgono PRIMA, e il billing account e' il
--   primo la cui utility ne ammette le tipologie (su dbdev il composito e' SERVIZI, che la
--   utility del primo cliente non prevede). Le erogazioni sono quelle che il perimetro
--   ammette: UNA_TANTUM sul semplice, CANONE/DERIVATA_COMPONENTI e CONSUMO/MANUALE sul
--   composito (CONSUMO/LETTURE non lo ammette una tipologia non a contatore).
CREATE TEMP TABLE tmp_oce_comp AS
    -- Articolo composito con almeno un componente attivo valido al DATE '2082-01-01'
    -- (fixture) e tutti opzionali (obbligatorio=FALSE): il fallback prezzo=0 del
    -- resolver e' ammesso solo su componenti opzionali. Nessun filtro esposto_in_fattura
    -- (modello unificato rev 2026-05-27).
SELECT (SELECT a.id
       FROM catalogo.articoli a
      WHERE a.is_composito = TRUE
        AND EXISTS (
            SELECT 1 FROM catalogo.articoli_componenti ac
             WHERE ac.prodotto_id = a.id
               AND COALESCE(ac.attivo, TRUE) = TRUE
               AND ac.validita @> DATE '2082-01-01'
        )
        AND NOT EXISTS (
            SELECT 1 FROM catalogo.articoli_componenti ac
             WHERE ac.prodotto_id = a.id
               AND COALESCE(ac.attivo, TRUE) = TRUE
               AND COALESCE(ac.obbligatorio, TRUE) = TRUE
        )
        -- rev 2026-10-07 (giro B3): le combinazioni che il test scrive sono nel perimetro
        AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                     WHERE e.tipo_erogazione = 'CANONE' AND e.fonte_quantita_attesa = 'DERIVATA_COMPONENTI')
        AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                     WHERE e.tipo_erogazione = 'CONSUMO' AND e.fonte_quantita_attesa = 'MANUALE')
      ORDER BY a.id LIMIT 1) AS articolo_composito_id;

CREATE TEMP TABLE tmp_oce_sempl AS
    -- Articolo non composito (per test 15)
SELECT (SELECT a.id
       FROM catalogo.articoli a
      WHERE COALESCE(a.is_composito, FALSE) = FALSE
        -- rev 2026-10-07 (giro B3): UNA_TANTUM/FISSA nel perimetro
        AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                     WHERE e.tipo_erogazione = 'UNA_TANTUM' AND e.fonte_quantita_attesa = 'FISSA')
      ORDER BY a.id LIMIT 1) AS articolo_semplice_id;

CREATE TEMP TABLE tmp_oce_ctx AS
SELECT
    (SELECT articolo_composito_id FROM tmp_oce_comp) AS articolo_composito_id,

    (SELECT articolo_semplice_id FROM tmp_oce_sempl) AS articolo_semplice_id,

    -- Contesto billing/utility: BA senza tipi_utenze (evita guard tipo/classe)
    (SELECT ba.id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
        -- rev 2026-10-07 (giro B3): la utility ammette le tipologie dei due articoli
        AND NOT EXISTS (
            SELECT 1 FROM catalogo.articoli a
             WHERE a.id IN ((SELECT articolo_composito_id FROM tmp_oce_comp),
                            (SELECT articolo_semplice_id FROM tmp_oce_sempl))
               AND a.listino_tipologia_id IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                                WHERE ltu.utility_id = ba.utility_id
                                  AND ltu.tipologia_id = a.listino_tipologia_id
                                  AND ltu.attivo))
      ORDER BY ba.id LIMIT 1) AS billing_account_id,

    (SELECT ba.istanza_utility_id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
        -- rev 2026-10-07 (giro B3): la utility ammette le tipologie dei due articoli
        AND NOT EXISTS (
            SELECT 1 FROM catalogo.articoli a
             WHERE a.id IN ((SELECT articolo_composito_id FROM tmp_oce_comp),
                            (SELECT articolo_semplice_id FROM tmp_oce_sempl))
               AND a.listino_tipologia_id IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                                WHERE ltu.utility_id = ba.utility_id
                                  AND ltu.tipologia_id = a.listino_tipologia_id
                                  AND ltu.attivo))
      ORDER BY ba.id LIMIT 1) AS istanza_utility_id,

    (SELECT ba.utility_id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
        -- rev 2026-10-07 (giro B3): la utility ammette le tipologie dei due articoli
        AND NOT EXISTS (
            SELECT 1 FROM catalogo.articoli a
             WHERE a.id IN ((SELECT articolo_composito_id FROM tmp_oce_comp),
                            (SELECT articolo_semplice_id FROM tmp_oce_sempl))
               AND a.listino_tipologia_id IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                                WHERE ltu.utility_id = ba.utility_id
                                  AND ltu.tipologia_id = a.listino_tipologia_id
                                  AND ltu.attivo))
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
        AS stato_accettata_id,
    -- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R5a): le righe
    --   dell'offerta si scrivono solo in BOZZA. Le offerte nascono in BOZZA, e la
    --   COMPOSITA va in EMESSA e poi ACCETTATA solo prima del push (test 20).
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')
        AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')
        AS stato_emessa_id;

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo). Qui gli
--   articoli (composito, semplice) e i loro prezzi vengono dai dati, quindi il
--   fixture non si ricostruisce: si FILTRA. L'emittente si deriva dal BA (il
--   guard emittente/cliente lo pretendeva gia'), il listino e' il primo attivo
--   della utility e dell'emittente del BA, la versione la prima ATTIVA di QUEL
--   listino (prima era la prima ATTIVA di un listino qualsiasi). Senza un
--   listino cosi' il fixture salta, come senza BA.
UPDATE tmp_oce_ctx c
   SET emittente_fiscale_id = anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id),
       emittente_sr_id = (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
                           WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id))
 -- Senza BA il fixture salta: fn_get_emittente_fiscale_pk rifiuta un id NULL.
 WHERE c.billing_account_id IS NOT NULL;
UPDATE tmp_oce_ctx c
   SET listino_id = (SELECT l.id FROM vendite.listini l
                      WHERE l.attivo IS TRUE
                        AND l.utility_id = c.utility_id
                        AND l.emittente_soggetto_ruolo_id = c.emittente_sr_id
                      ORDER BY l.id LIMIT 1);
UPDATE tmp_oce_ctx c
   SET listino_versione_id = (SELECT lv.id FROM vendite.listini_versioni lv
                               WHERE lv.listino_id = c.listino_id AND lv.stato = 'ATTIVA'
                               ORDER BY lv.id LIMIT 1);

-- Flag: dati composito disponibili?
CREATE TEMP TABLE tmp_oce_has_composito AS
SELECT (articolo_composito_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND listino_id IS NOT NULL
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
       OR v_ctx.listino_id IS NULL
    THEN RETURN; END IF;

    -- Offerta in BOZZA: le righe si scrivono solo li' (rev 2026-10-04, R5a).
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT v_ctx.emittente_fiscale_id, v_ctx.billing_account_id,
           v_ctx.istanza_utility_id, v_ctx.utility_id,
           v_ctx.listino_id, v_ctx.listino_versione_id,
           DATE '2082-01-01', v_ctx.stato_bozza_id
    RETURNING id INTO v_off_id;

    -- Eccezione con articolo semplice (test 15).
    -- fonte=FISSA richiede qta_operativa NOT NULL (trigger a10 qta_from_operativa,
    -- bind 20260531-11): si valorizza qta_operativa e il trigger deriva quantita.
    IF v_ctx.articolo_semplice_id IS NOT NULL THEN
        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
        INSERT INTO vendite.offerte_commerciali_eccezioni (
            offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
            prezzo_unitario, qta_operativa, tipo_erogazione
        )
        VALUES (v_off_id, v_ctx.articolo_semplice_id, 'OVERRIDE', 'FISSA', 10.00, 1, 'UNA_TANTUM')
        RETURNING id INTO v_ecc_id;
        INSERT INTO tmp_oce_ids VALUES ('SEMPLICE', v_off_id, v_ecc_id);
    END IF;

    -- Eccezione con articolo composito (test 17-19)
    IF v_ctx.articolo_composito_id IS NOT NULL THEN
        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
        INSERT INTO vendite.offerte_commerciali_eccezioni (
            offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
            prezzo_unitario, quantita, tipo_erogazione
        )
        VALUES (v_off_id, v_ctx.articolo_composito_id, 'OVERRIDE',
                'DERIVATA_COMPONENTI', 0.00, 2, 'CANONE')
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
               DATE '2082-01-01', v_ctx.stato_bozza_id
        RETURNING id INTO v_off_consumo;

        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
        INSERT INTO vendite.offerte_commerciali_eccezioni (
            offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
            prezzo_unitario, quantita, tipo_erogazione
        )
        VALUES (v_off_consumo, v_ctx.articolo_composito_id, 'OVERRIDE',
                'MANUALE', 0.00, NULL, 'CONSUMO')
        RETURNING id INTO v_ecc_id;
        INSERT INTO tmp_oce_ids VALUES ('CONSUMO', v_off_consumo, v_ecc_id);
    END IF;

    -- Eccezione ESCLUSIONE su articolo composito (test 27).
    -- ⚠️ rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R1): l'esclusione
    --   nasce VUOTA — niente fonte, niente quantita'. Prima portava quantita' 2 per
    --   provare che l'init la salta pur avendo una quantita'; oggi un'esclusione con
    --   quantita' non si scrive (E_RIGA_ESCLUSIONE_CON_DATI), e il test prova l'esito
    --   (0 componenti, prezzo padre NULL) sull'esclusione come il modello la ammette.
    -- Offerta separata: l'unique parziale uq_offerte_eccezioni_one_eccezione_per_articolo
    -- ammette al piu' 1 riga OVERRIDE/ESCLUSIONE per (offerta, articolo) e la COMPOSITA
    -- ha gia' un OVERRIDE sullo stesso articolo. prezzo_unitario NULL (CHECK ESCLUSIONE).
    IF v_ctx.articolo_composito_id IS NOT NULL THEN
        INSERT INTO vendite.offerte_commerciali (
            emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
            listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
        )
        SELECT v_ctx.emittente_fiscale_id, v_ctx.billing_account_id,
               v_ctx.istanza_utility_id, v_ctx.utility_id,
               v_ctx.listino_id, v_ctx.listino_versione_id,
               DATE '2082-01-01', v_ctx.stato_bozza_id
        RETURNING id INTO v_off_consumo;

        INSERT INTO vendite.offerte_commerciali_eccezioni (
            offerta_id, articolo_id, tipo_eccezione
        )
        VALUES (v_off_consumo, v_ctx.articolo_composito_id, 'ESCLUSIONE')
        RETURNING id INTO v_ecc_id;
        INSERT INTO tmp_oce_ids VALUES ('ESCLUSIONE', v_off_consumo, v_ecc_id);
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
    $$SELECT vendite.fn_offerta_eccezione_componenti_init(NULL, 1, script.fn_data_operativa())$$,
    '%Parametro non valido%',
    '12) fn_init(NULL, 1, date): guard p_eccezione_id → E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- TEST 13) fn_init guard p_emittente_sr_id NULL → E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_like(
    $$SELECT vendite.fn_offerta_eccezione_componenti_init(1, NULL, script.fn_data_operativa())$$,
    '%Parametro non valido%',
    '13) fn_init(1, NULL, date): guard p_emittente_sr_id → E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- TEST 14) fn_init eccezione non trovata → E_OFFERTA_ECCEZIONE_NON_TROVATA
--
-- ⭐ AGGIORNATO IL 2026-08-24, e in meglio: il test pretendeva
--    `E_PARAMETRO_INVALIDO`, ma quel ramo ha ricevuto un codice PROPRIO —
--    `E_OFFERTA_ECCEZIONE_NON_TROVATA`, classe `NON_TROVATO` — che e' la
--    direzione in cui il progetto sta andando (il generico si sta scomponendo,
--    codice per codice). Il test blindava il codice VECCHIO, cioe' avrebbe
--    protestato contro un miglioramento.
--
-- ⚠️ E qui si asserisce il CODICE, non piu' un frammento di frase: il punto e'
--    QUALE errore, e la frase e' la cosa che cambia piu' spesso. Con
--    `throws_like('%Parametro non valido%')` un domani basterebbe riscrivere il
--    messaggio per far diventare verde un ramo sbagliato.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.oce_codice_init(p_ecc bigint)
RETURNS text AS $fn$
-- ⚠️ `text` esplicito: e' il canale CONSTRAINT dell'eccezione, non una colonna.
DECLARE v_cod text;
BEGIN
    PERFORM vendite.fn_offerta_eccezione_componenti_init(p_ecc, 1, script.fn_data_operativa());
    RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
    RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $fn$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_oce_cod_14 AS
SELECT pg_temp.oce_codice_init(999999999::bigint) AS codice;

SELECT is(
    (SELECT codice FROM tmp_oce_cod_14),
    'E_OFFERTA_ECCEZIONE_NON_TROVATA',
    '14) fn_init(999999999, 1, date): eccezione non trovata → E_OFFERTA_ECCEZIONE_NON_TROVATA'
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
            script.fn_data_operativa()
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
            script.fn_data_operativa()
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

-- Setup test 19: crea eccezione COMPOSITA-OVR e chiama fn_init con override.
-- Chiave override: componente_id::text (uuid articolo figlio) — modello unificato
-- rev 2026-05-27; nessun filtro esposto_in_fattura nella ricerca del componente.
DO $$
DECLARE
    v_ovr_ecc_id  bigint;
    v_off_id      bigint;
    v_comp_id     uuid;
BEGIN
    IF NOT (SELECT disponibile FROM tmp_oce_has_composito) THEN RETURN; END IF;

    -- ⚠️ rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R5b): prima
    --   era un'AGGIUNTA dello stesso articolo composito, sulla stessa offerta che ne
    --   forzava gia' il prezzo (OVERRIDE): cioe' un articolo del listino aggiunto
    --   come fuori listino, che il guard dell'aggiunta ora rifiuta anche
    --   sull'offerta. Il test prova l'override del prezzo di un componente, non il
    --   tipo di riga: diventa un OVERRIDE su un'offerta sua, in BOZZA.
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT c.emittente_fiscale_id, c.billing_account_id, c.istanza_utility_id, c.utility_id,
           c.listino_id, c.listino_versione_id, DATE '2082-01-01', c.stato_bozza_id
      FROM tmp_oce_ctx c
    RETURNING id INTO v_off_id;

    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
        prezzo_unitario, quantita, tipo_erogazione
    )
    VALUES (v_off_id, (SELECT articolo_composito_id FROM tmp_oce_ctx),
            'OVERRIDE', 'DERIVATA_COMPONENTI', 0.00, 3, 'CANONE')
    RETURNING id INTO v_ovr_ecc_id;

    INSERT INTO tmp_oce_ids VALUES ('COMPOSITA-OVR', v_off_id, v_ovr_ecc_id);

    -- Prende il componente_id (uuid articolo figlio) del primo componente valido.
    SELECT ac.componente_id INTO v_comp_id
      FROM catalogo.articoli_componenti ac
     WHERE ac.prodotto_id = (SELECT articolo_composito_id FROM tmp_oce_ctx)
       AND COALESCE(ac.attivo, TRUE) = TRUE
       AND ac.validita @> DATE '2082-01-01'
     ORDER BY ac.id LIMIT 1;

    PERFORM vendite.fn_offerta_eccezione_componenti_init(
        v_ovr_ecc_id,
        (SELECT emittente_sr_id FROM tmp_oce_ctx),
        DATE '2082-01-01',
        jsonb_build_object(v_comp_id::text, 99999)
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

    -- rev 2026-10-04 (R5a): righe e componenti si scrivono in BOZZA; il push vuole
    -- un'offerta ACCETTATA, e ci arriva per la sua strada: BOZZA -> EMESSA -> ACCETTATA.
    UPDATE vendite.offerte_commerciali
       SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_oce_ctx)
     WHERE id = (SELECT offerta_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA');
    UPDATE vendite.offerte_commerciali
       SET stato_doc_offerta_id = (SELECT stato_accettata_id FROM tmp_oce_ctx)
     WHERE id = (SELECT offerta_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA');

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

-- ============================================================
-- Setup test 21-26: fn_offerta_eccezione_componenti_preview
-- Context separato: richiede componenti validi per script.fn_data_operativa().
-- ============================================================
CREATE TEMP TABLE tmp_preview_ctx AS
SELECT
    ctx.articolo_composito_id,
    ctx.articolo_semplice_id,
    ctx.billing_account_id,
    ctx.utility_id,
    ctx.emittente_sr_id,
    a.uom_id   AS composito_uom_id,
    as_.uom_id AS semplice_uom_id,
    -- disponibile = true solo se tutti i dati presenti E almeno
    -- un componente attivo valido per script.fn_data_operativa()
    (ctx.articolo_composito_id IS NOT NULL
     AND ctx.billing_account_id IS NOT NULL
     AND ctx.emittente_sr_id IS NOT NULL
     AND EXISTS (
         SELECT 1 FROM catalogo.articoli_componenti ac
          WHERE ac.prodotto_id = ctx.articolo_composito_id
            AND COALESCE(ac.attivo, TRUE) = TRUE
            AND ac.validita @> script.fn_data_operativa()
     )) AS disponibile
  FROM tmp_oce_ctx ctx
  LEFT JOIN catalogo.articoli a   ON a.id   = ctx.articolo_composito_id
  LEFT JOIN catalogo.articoli as_ ON as_.id = ctx.articolo_semplice_id;

-- ============================================================
-- TEST 21) fn_preview esiste (has_function)
-- ============================================================
SELECT has_function(
    'vendite',
    'fn_offerta_eccezione_componenti_preview',
    '21) vendite.fn_offerta_eccezione_componenti_preview esiste'
);

-- ============================================================
-- TEST 22) fn_preview articolo semplice → 0 righe
-- ============================================================
SELECT CASE
    WHEN (SELECT billing_account_id IS NOT NULL
               AND articolo_semplice_id IS NOT NULL
            FROM tmp_preview_ctx)
    THEN is(
        (SELECT COUNT(*) FROM vendite.fn_offerta_eccezione_componenti_preview(
            (SELECT articolo_semplice_id FROM tmp_preview_ctx),
            (SELECT semplice_uom_id      FROM tmp_preview_ctx),
            1,
            script.fn_data_operativa(),
            (SELECT billing_account_id   FROM tmp_preview_ctx),
            (SELECT utility_id           FROM tmp_preview_ctx),
            (SELECT emittente_sr_id      FROM tmp_preview_ctx),
            NULL
        )),
        0::bigint,
        '22) fn_preview articolo semplice → 0 righe (nessun componente BoM)'
    )
    ELSE skip('22) skip: articolo semplice o billing context non disponibile')
END;

-- ============================================================
-- TEST 23) fn_preview articolo composito → righe > 0
--          (obbligatorio + esposizione_in_fattura accessibili nella proiezione)
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_preview_ctx)
    THEN ok(
        (SELECT COUNT(*) FROM vendite.fn_offerta_eccezione_componenti_preview(
            (SELECT articolo_composito_id FROM tmp_preview_ctx),
            (SELECT composito_uom_id      FROM tmp_preview_ctx),
            2,
            script.fn_data_operativa(),
            (SELECT billing_account_id    FROM tmp_preview_ctx),
            (SELECT utility_id            FROM tmp_preview_ctx),
            (SELECT emittente_sr_id       FROM tmp_preview_ctx),
            NULL
        ) p
        -- IS NOT DISTINCT FROM sé stesso è tautologia: se le colonne non
        -- esistessero nella RETURNS TABLE, la query fallirebbe qui
        WHERE p.obbligatorio IS NOT DISTINCT FROM p.obbligatorio
          AND p.esposizione_in_fattura IS NOT DISTINCT FROM p.esposizione_in_fattura
        ) > 0,
        '23) fn_preview articolo composito: righe > 0, colonne obbligatorio+esposizione_in_fattura accessibili'
    )
    ELSE skip('23) skip: articolo composito con componenti validi per script.fn_data_operativa() non disponibile')
END;

-- ============================================================
-- TEST 24) COUNT preview = COUNT componenti attivi validi
--          (nessun filtro esposto_in_fattura → modello unificato)
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_preview_ctx)
    THEN is(
        (SELECT COUNT(*) FROM vendite.fn_offerta_eccezione_componenti_preview(
            (SELECT articolo_composito_id FROM tmp_preview_ctx),
            (SELECT composito_uom_id      FROM tmp_preview_ctx),
            2,
            script.fn_data_operativa(),
            (SELECT billing_account_id    FROM tmp_preview_ctx),
            (SELECT utility_id            FROM tmp_preview_ctx),
            (SELECT emittente_sr_id       FROM tmp_preview_ctx),
            NULL
        )),
        (SELECT COUNT(*)
           FROM catalogo.articoli_componenti ac
          WHERE ac.prodotto_id = (SELECT articolo_composito_id FROM tmp_preview_ctx)
            AND COALESCE(ac.attivo, TRUE) = TRUE
            AND ac.validita @> script.fn_data_operativa()),
        '24) fn_preview COUNT = COUNT componenti attivi validi (nessun filtro esposto_in_fattura)'
    )
    ELSE skip('24) skip: articolo composito con componenti validi per script.fn_data_operativa() non disponibile')
END;

-- ============================================================
-- TEST 25) quantita_componente = coeff_qta_snapshot * p_quantita_padre
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_preview_ctx)
    THEN ok(
        NOT EXISTS (
            SELECT 1
              FROM vendite.fn_offerta_eccezione_componenti_preview(
                  (SELECT articolo_composito_id FROM tmp_preview_ctx),
                  (SELECT composito_uom_id      FROM tmp_preview_ctx),
                  2,
                  script.fn_data_operativa(),
                  (SELECT billing_account_id    FROM tmp_preview_ctx),
                  (SELECT utility_id            FROM tmp_preview_ctx),
                  (SELECT emittente_sr_id       FROM tmp_preview_ctx),
                  NULL
              ) p
             WHERE p.quantita_componente IS DISTINCT FROM (p.coeff_qta_snapshot * 2)
        ),
        '25) fn_preview quantita_componente = coeff_qta_snapshot * 2 (p_quantita_padre) per ogni riga'
    )
    ELSE skip('25) skip: articolo composito con componenti validi per script.fn_data_operativa() non disponibile')
END;

-- ============================================================
-- TEST 26) fn_preview include componenti NASCOSTI
--          (verifica rimozione del vecchio filtro AND esposto_in_fattura=TRUE;
--          dal 2026-10-01 il booleano false e' esposizione_in_fattura = NASCOSTO)
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_preview_ctx)
       AND EXISTS (
           SELECT 1 FROM catalogo.articoli_componenti ac
            WHERE ac.prodotto_id = (SELECT articolo_composito_id FROM tmp_preview_ctx)
              AND ac.esposizione_in_fattura = 'NASCOSTO'
              AND COALESCE(ac.attivo, TRUE) = TRUE
              AND ac.validita @> script.fn_data_operativa()
       )
    THEN ok(
        EXISTS (
            SELECT 1
              FROM vendite.fn_offerta_eccezione_componenti_preview(
                  (SELECT articolo_composito_id FROM tmp_preview_ctx),
                  (SELECT composito_uom_id      FROM tmp_preview_ctx),
                  2,
                  script.fn_data_operativa(),
                  (SELECT billing_account_id    FROM tmp_preview_ctx),
                  (SELECT utility_id            FROM tmp_preview_ctx),
                  (SELECT emittente_sr_id       FROM tmp_preview_ctx),
                  NULL
              ) p
             WHERE p.esposizione_in_fattura = 'NASCOSTO'
        ),
        '26) fn_preview include componenti NASCOSTI (filtro AND esposto=TRUE rimosso)'
    )
    ELSE skip('26) skip: nessun componente NASCOSTO valido per script.fn_data_operativa()')
END;

-- ============================================================
-- TEST 27) fn_init guard difensivo: ESCLUSIONE su articolo composito
--          → ritorna 0, NESSUN componente inserito, e la riga padre
--          conserva prezzo_unitario IS NULL (nessuna violazione del
--          CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione).
-- ============================================================
SELECT CASE
    WHEN (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'ESCLUSIONE') IS NOT NULL
    THEN is(
        (
            -- la fn deve ritornare 0 (no-op) senza sollevare il CHECK
            SELECT vendite.fn_offerta_eccezione_componenti_init(
                (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'ESCLUSIONE'),
                (SELECT emittente_sr_id FROM tmp_oce_ctx),
                DATE '2082-01-01'
            )
        )
        -- 0 componenti inseriti
        + (SELECT COUNT(*)::integer FROM vendite.offerte_commerciali_eccezioni_componenti
            WHERE eccezione_offerta_id =
                  (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'ESCLUSIONE'))
        -- prezzo padre ancora NULL → +0; se non NULL questo termine sarebbe 1000
        + (SELECT CASE WHEN prezzo_unitario IS NULL THEN 0 ELSE 1000 END
             FROM vendite.offerte_commerciali_eccezioni
            WHERE id = (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'ESCLUSIONE')),
        0,
        '27) fn_init ESCLUSIONE composito → 0, nessun componente, prezzo padre NULL'
    )
    ELSE skip('27) skip: nessuna eccezione ESCLUSIONE composita disponibile')
END;

SELECT * FROM finish();
ROLLBACK;
