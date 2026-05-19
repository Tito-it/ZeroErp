-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.contratti_righe — coerenza fonte_quantita_attesa × tipo_erogazione
--       Migrations: 20260519-05 (backfill + NOT NULL + CHECK), 20260519-06 (trigger normalize)
--
-- Indice test (1..15):
--   Struttura:
--   1) fonte_quantita_attesa NOT NULL
--   2) CHECK chk_contrighe_coerenza_fonte_erogazione presente
--   3) Trigger trg_contratti_righe_a10_default_fonte_qta_ins_upd presente
--   4) Setup fixture OK (contratto DRAFT + almeno 1 articolo trovato)
--
--   Comportamento CHECK — 7 combinazioni vietate (skip se no fixture):
--   5)  CANONE     + TIMESHEET  → raises 23514
--   6)  CANONE     + LETTURE    → raises 23514
--   7)  UNA_TANTUM + TIMESHEET  → raises 23514
--   8)  UNA_TANTUM + LETTURE    → raises 23514
--   9)  ORARIO     + LETTURE    → raises 23514
--   10) CONSUMO    + FISSA      → raises 23514
--   11) CONSUMO    + TIMESHEET  → raises 23514
--
--   Comportamento normalize trigger — INSERT (skip se < 4 articoli):
--   12) INSERT CANONE  + fonte NULL → trigger imposta FISSA
--   13) INSERT CONSUMO + fonte NULL → trigger imposta LETTURE
--   14) INSERT ORARIO  + fonte NULL → trigger imposta MANUALE
--
--   Comportamento normalize trigger — UPDATE tipo (skip se < 4 articoli):
--   15) UPDATE tipo CANONE→CONSUMO, fonte=FISSA → trigger resetta fonte a LETTURE
-- ------------------------------------------------------------
--
-- Nota sui test CHECK (5-11):
--   Fonte ESPLICITA vietata (non NULL): normalize non tocca valori non-NULL su INSERT.
--   Il CHECK fires prima delle FK (AFTER trigger) → errore atteso 23514.
--
-- Nota sui test normalize (12-15):
--   I WITH-DML devono stare al top-level (non dentro CASE — vincolo PG).
--   Setup esegue gli INSERT/UPDATE nella sezione fixture; le assertions usano
--   CASE WHEN NOT EXISTS su tmp_norm_fonte (skippa se fixture indisponibile).
--   Usa 4 articoli distinti (seq 1-4) per rispettare uq_contrighe_one_aggiunta_per_articolo.
-- ------------------------------------------------------------

BEGIN;

-- ============================================================
-- Setup fixture
-- ============================================================

CREATE TEMP TABLE tmp_fonte_ctx AS
SELECT
    ba.id                   AS ba_id,
    ba.istanza_utility_id,
    ba.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT' LIMIT 1) AS id_draft,
    (SELECT a.id FROM catalogo.articoli a WHERE a.attivo = TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id
FROM anagrafiche.billing_account ba
ORDER BY ba.id
LIMIT 1;

-- Contratto DRAFT senza listino (date 2075 per non collidere con altri pgTAP)
INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_FONTE_CNT', c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2075-01-01'::date, '2075-12-31'::date
FROM tmp_fonte_ctx c
WHERE c.ba_id IS NOT NULL AND c.id_draft IS NOT NULL;

-- 4 articoli distinti per i test normalize (12-15): evita uq_contrighe_one_aggiunta_per_articolo
-- (lo stesso (contratto, articolo) non può avere due AGGIUNTA).
CREATE TEMP TABLE tmp_norm_arts AS
SELECT a.id AS articolo_id, ROW_NUMBER() OVER (ORDER BY a.id) AS seq
  FROM catalogo.articoli a
 WHERE a.attivo = TRUE AND a.is_composito = FALSE
 ORDER BY a.id
 LIMIT 4;

-- ============================================================
-- Pre-esecuzione test normalize 12-15:
-- Gli INSERT/UPDATE con WITH-DML devono stare al top level (non dentro CASE).
-- La tabella tmp_norm_fonte raccoglie (test_num, fonte_value) da RETURNING.
-- Se il contratto PGTAP_FONTE_CNT non esiste o mancano articoli, gli INSERT
-- non trovano righe nella SELECT → 0 righe inserite → tmp_norm_fonte resta
-- senza quella riga → il test skippa via CASE WHEN NOT EXISTS.
-- ============================================================

CREATE TEMP TABLE tmp_norm_fonte (test_num int, fonte_value text);

-- Test 12: CANONE + fonte NULL → aspettato FISSA (articolo seq=1)
WITH ins AS (
    INSERT INTO vendite.contratti_righe
        (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, prezzo_unitario, qta_operativa)
    SELECT c.id, na.articolo_id, 'AGGIUNTA', 'CANONE', 100, 1
      FROM vendite.contratti c, tmp_norm_arts na
     WHERE c.numero = 'PGTAP_FONTE_CNT' AND na.seq = 1
    RETURNING fonte_quantita_attesa
)
INSERT INTO tmp_norm_fonte SELECT 12, fonte_quantita_attesa FROM ins;

-- Test 13: CONSUMO + fonte NULL → aspettato LETTURE (articolo seq=2)
WITH ins AS (
    INSERT INTO vendite.contratti_righe
        (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, prezzo_unitario, qta_operativa)
    SELECT c.id, na.articolo_id, 'AGGIUNTA', 'CONSUMO', 100, 1
      FROM vendite.contratti c, tmp_norm_arts na
     WHERE c.numero = 'PGTAP_FONTE_CNT' AND na.seq = 2
    RETURNING fonte_quantita_attesa
)
INSERT INTO tmp_norm_fonte SELECT 13, fonte_quantita_attesa FROM ins;

-- Test 14: ORARIO + fonte NULL → aspettato MANUALE (articolo seq=3)
WITH ins AS (
    INSERT INTO vendite.contratti_righe
        (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, prezzo_unitario, qta_operativa)
    SELECT c.id, na.articolo_id, 'AGGIUNTA', 'ORARIO', 100, 1
      FROM vendite.contratti c, tmp_norm_arts na
     WHERE c.numero = 'PGTAP_FONTE_CNT' AND na.seq = 3
    RETURNING fonte_quantita_attesa
)
INSERT INTO tmp_norm_fonte SELECT 14, fonte_quantita_attesa FROM ins;

-- Test 15: INSERT CANONE+FISSA (articolo seq=4), poi UPDATE tipo→CONSUMO.
-- Il trigger rileva CONSUMO+FISSA (❌) e resetta fonte a LETTURE.
WITH ins AS (
    INSERT INTO vendite.contratti_righe
        (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
    SELECT c.id, na.articolo_id, 'AGGIUNTA', 'CANONE', 'FISSA', 100, 1
      FROM vendite.contratti c, tmp_norm_arts na
     WHERE c.numero = 'PGTAP_FONTE_CNT' AND na.seq = 4
    RETURNING id
),
upd AS (
    UPDATE vendite.contratti_righe
       SET tipo_erogazione = 'CONSUMO'
     WHERE id IN (SELECT id FROM ins)
    RETURNING fonte_quantita_attesa
)
INSERT INTO tmp_norm_fonte SELECT 15, fonte_quantita_attesa FROM upd;

-- ============================================================
SELECT plan(15);
-- ============================================================

-- ============================================================
-- 1) NOT NULL su fonte_quantita_attesa
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'contratti_righe'
           AND column_name  = 'fonte_quantita_attesa'
           AND is_nullable  = 'NO'
    ),
    '1) fonte_quantita_attesa NOT NULL (20260519-05)'
);

-- ============================================================
-- 2) CHECK chk_contrighe_coerenza_fonte_erogazione presente
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1 FROM information_schema.table_constraints
         WHERE constraint_schema = 'vendite'
           AND table_name        = 'contratti_righe'
           AND constraint_name   = 'chk_contrighe_coerenza_fonte_erogazione'
           AND constraint_type   = 'CHECK'
    ),
    '2) CHECK chk_contrighe_coerenza_fonte_erogazione presente (20260519-05)'
);

-- ============================================================
-- 3) Trigger normalize presente
-- ============================================================
SELECT has_trigger(
    'vendite',
    'contratti_righe',
    'trg_contratti_righe_a10_default_fonte_qta_ins_upd',
    '3) trigger trg_contratti_righe_a10_default_fonte_qta_ins_upd presente (20260519-06)'
);

-- ============================================================
-- 4) Setup fixture OK
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
    AND EXISTS(SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL),
    '4) fixture: contratto PGTAP_FONTE_CNT creato e almeno un articolo di test trovato'
);

-- ============================================================
-- 5-11) CHECK — 7 combinazioni vietate
-- ============================================================

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('5) fixture non disponibile — skip CANONE+TIMESHEET')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CANONE', 'TIMESHEET', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        '23514', NULL,
        '5) CANONE+TIMESHEET → check_violation 23514'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('6) fixture non disponibile — skip CANONE+LETTURE')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CANONE', 'LETTURE', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        '23514', NULL,
        '6) CANONE+LETTURE → check_violation 23514'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('7) fixture non disponibile — skip UNA_TANTUM+TIMESHEET')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'UNA_TANTUM', 'TIMESHEET', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        '23514', NULL,
        '7) UNA_TANTUM+TIMESHEET → check_violation 23514'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('8) fixture non disponibile — skip UNA_TANTUM+LETTURE')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'UNA_TANTUM', 'LETTURE', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        '23514', NULL,
        '8) UNA_TANTUM+LETTURE → check_violation 23514'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('9) fixture non disponibile — skip ORARIO+LETTURE')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'ORARIO', 'LETTURE', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        '23514', NULL,
        '9) ORARIO+LETTURE → check_violation 23514'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('10) fixture non disponibile — skip CONSUMO+FISSA')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CONSUMO', 'FISSA', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        '23514', NULL,
        '10) CONSUMO+FISSA → check_violation 23514'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('11) fixture non disponibile — skip CONSUMO+TIMESHEET')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CONSUMO', 'TIMESHEET', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        '23514', NULL,
        '11) CONSUMO+TIMESHEET → check_violation 23514'
    )
END;

-- ============================================================
-- 12-14) Normalize trigger — INSERT con fonte NULL
--         Gli INSERT sono stati eseguiti nel setup (CTE top-level).
--         tmp_norm_fonte contiene il risultato del RETURNING.
-- ============================================================

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_norm_fonte WHERE test_num = 12)
    THEN skip('12) meno di 1 articolo disponibile — skip normalize CANONE')
    ELSE is(
        (SELECT fonte_value FROM tmp_norm_fonte WHERE test_num = 12),
        'FISSA',
        '12) normalize INSERT: CANONE + NULL fonte → trigger imposta FISSA'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_norm_fonte WHERE test_num = 13)
    THEN skip('13) meno di 2 articoli disponibili — skip normalize CONSUMO')
    ELSE is(
        (SELECT fonte_value FROM tmp_norm_fonte WHERE test_num = 13),
        'LETTURE',
        '13) normalize INSERT: CONSUMO + NULL fonte → trigger imposta LETTURE'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_norm_fonte WHERE test_num = 14)
    THEN skip('14) meno di 3 articoli disponibili — skip normalize ORARIO')
    ELSE is(
        (SELECT fonte_value FROM tmp_norm_fonte WHERE test_num = 14),
        'MANUALE',
        '14) normalize INSERT: ORARIO + NULL fonte → trigger imposta MANUALE'
    )
END;

-- ============================================================
-- 15) Normalize trigger — UPDATE tipo_erogazione con combo vietata
--     L''INSERT CANONE+FISSA e l''UPDATE a CONSUMO sono stati eseguiti nel setup.
--     Il trigger ha resettato fonte da FISSA a LETTURE (CONSUMO+FISSA è ❌).
-- ============================================================

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_norm_fonte WHERE test_num = 15)
    THEN skip('15) meno di 4 articoli disponibili — skip normalize UPDATE tipo')
    ELSE is(
        (SELECT fonte_value FROM tmp_norm_fonte WHERE test_num = 15),
        'LETTURE',
        '15) normalize UPDATE: tipo CANONE→CONSUMO, fonte FISSA → trigger resetta LETTURE'
    )
END;

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
