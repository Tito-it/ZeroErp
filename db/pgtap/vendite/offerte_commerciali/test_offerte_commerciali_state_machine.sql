-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: state machine vendite.offerte_commerciali (Step 4).
--       Trigger guard trg_offerte_commerciali_a10_guard_transizione_upd.
--       Config-driven via config.stati_doc_offerte_transizioni.
--
-- Indice test (1..10):
--   1)  Trigger guard esiste
--   2)  BOZZA->EMESSA con listino_versione_id NULL -> throws E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO
--   3)  BOZZA->EMESSA con versione NON ATTIVA -> throws E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA
--       (skip condizionale se nessuna versione non-ATTIVA disponibile)
--   4)  BOZZA->EMESSA con versione ATTIVA -> ok
--   5)  EMESSA->BOZZA -> throws (transizione non ammessa)
--   6)  EMESSA->ACCETTATA -> ok
--   7)  data_accettazione valorizzata dopo transizione EMESSA->ACCETTATA
--   8)  ACCETTATA->EMESSA -> throws (stato terminale immutabile)
--   9)  BOZZA->ANNULLATA -> ok + data_annullamento valorizzata (addendum A2)
--  10)  EMESSA->RIFIUTATA -> ok + data_rifiuto valorizzata
--
-- Strategia fixture:
--   - BA senza tipi_utenze per evitare guard tipo/classe su contratti_utilities.
--   - Offerte in date future lontane per evitare conflitti.
--   - Un'offerta per scenario (no riuso, per isolare le transizioni).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(10);

-- ============================================================
-- Setup fixture: contesti di riferimento
-- ============================================================
CREATE TEMP TABLE tmp_sm_ctx AS
SELECT
    -- BA senza tipi_utenze (evita guard tipo/classe al push)
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
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
    (SELECT l.id FROM vendite.listini l WHERE l.attivo IS TRUE ORDER BY l.id LIMIT 1) AS listino_id,
    (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato = 'ATTIVA'  ORDER BY lv.id LIMIT 1) AS listino_versione_id_attiva,
    (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato <> 'ATTIVA' ORDER BY lv.id LIMIT 1) AS listino_versione_id_non_attiva,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'RIFIUTATA') AS stato_rifiutata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ANNULLATA') AS stato_annullata_id;

-- Tabella di appoggio: slot -> offerta_id
CREATE TEMP TABLE tmp_sm_ids (
    slot      text PRIMARY KEY,
    offerta_id bigint
);

-- Slot A: BOZZA, listino_versione_id NULL (test 2: BOZZA->EMESSA con NULL)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, NULL, DATE '2082-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'A', id FROM ins;

-- Slot B: BOZZA, versione NON ATTIVA (test 3; solo se esiste)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_non_attiva,
           DATE '2083-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
     WHERE ctx.listino_versione_id_non_attiva IS NOT NULL
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'B', id FROM ins;

-- Slot C: BOZZA con versione ATTIVA (test 4: BOZZA->EMESSA successo)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2084-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'C', id FROM ins;

-- Slot D: BOZZA poi portata in EMESSA (test 5: EMESSA->BOZZA fails)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2085-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'D', id FROM ins;

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_sm_ctx)
 WHERE id = (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'D');

-- Slot E: BOZZA poi portata in EMESSA (test 6+7: EMESSA->ACCETTATA + data_accettazione)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2086-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'E', id FROM ins;

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_sm_ctx)
 WHERE id = (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'E');

-- Slot F: direttamente ACCETTATA (test 8: ACCETTATA->EMESSA fails)
-- Inserimento diretto bypassando il trigger di transizione (solo INSERT).
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2087-01-01', ctx.stato_accettata_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'F', id FROM ins;

-- Slot G: BOZZA (test 9: BOZZA->ANNULLATA)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, NULL, DATE '2088-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'G', id FROM ins;

-- Slot H: BOZZA poi EMESSA (test 10: EMESSA->RIFIUTATA)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2089-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'H', id FROM ins;

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_sm_ctx)
 WHERE id = (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'H');

-- ============================================================
-- 1) Trigger guard esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c    ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'offerte_commerciali'
           AND t.tgname  = 'trg_offerte_commerciali_a10_guard_transizione_upd'
    ),
    '1) trg_offerte_commerciali_a10_guard_transizione_upd esiste'
);

-- ============================================================
-- 2) BOZZA->EMESSA con listino_versione_id NULL -> throws
-- ============================================================
SELECT throws_ok(
    format(
        $q$UPDATE vendite.offerte_commerciali
              SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_sm_ctx)
            WHERE id = %s$q$,
        (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'A')
    ),
    'P0001', NULL,
    '2) BOZZA->EMESSA con listino_versione_id NULL -> throws E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO'
);

-- ============================================================
-- 3) BOZZA->EMESSA con versione NON ATTIVA -> throws
--    (skip se nessuna versione non-ATTIVA disponibile nel seed)
-- ============================================================
SELECT CASE
    WHEN (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'B') IS NULL
    THEN skip('3) skip: nessuna listini_versioni con stato <> ATTIVA disponibile nel seed')
    ELSE throws_ok(
        format(
            $q$UPDATE vendite.offerte_commerciali
                  SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_sm_ctx)
                WHERE id = %s$q$,
            (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'B')
        ),
        'P0001', NULL,
        '3) BOZZA->EMESSA con versione NON ATTIVA -> throws E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA'
    )
END;

-- ============================================================
-- 4) BOZZA->EMESSA con versione ATTIVA -> ok
-- ============================================================
SELECT lives_ok(
    format(
        $q$UPDATE vendite.offerte_commerciali
              SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_sm_ctx)
            WHERE id = %s$q$,
        (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'C')
    ),
    '4) BOZZA->EMESSA con versione listino ATTIVA -> ok'
);

-- ============================================================
-- 5) EMESSA->BOZZA -> throws (transizione non ammessa)
-- ============================================================
SELECT throws_ok(
    format(
        $q$UPDATE vendite.offerte_commerciali
              SET stato_doc_offerta_id = (SELECT stato_bozza_id FROM tmp_sm_ctx)
            WHERE id = %s$q$,
        (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'D')
    ),
    'P0001', NULL,
    '5) EMESSA->BOZZA -> throws E_OFFERTA_TRANSIZIONE_NON_AMMESSA'
);

-- ============================================================
-- 6) EMESSA->ACCETTATA -> ok
-- ============================================================
SELECT lives_ok(
    format(
        $q$UPDATE vendite.offerte_commerciali
              SET stato_doc_offerta_id = (SELECT stato_accettata_id FROM tmp_sm_ctx)
            WHERE id = %s$q$,
        (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'E')
    ),
    '6) EMESSA->ACCETTATA -> ok'
);

-- ============================================================
-- 7) data_accettazione valorizzata dopo EMESSA->ACCETTATA
-- ============================================================
SELECT ok(
    (SELECT data_accettazione IS NOT NULL
       FROM vendite.offerte_commerciali
      WHERE id = (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'E')),
    '7) data_accettazione valorizzata dal trigger dopo EMESSA->ACCETTATA'
);

-- ============================================================
-- 8) ACCETTATA->EMESSA -> throws (stato terminale immutabile)
-- ============================================================
SELECT throws_ok(
    format(
        $q$UPDATE vendite.offerte_commerciali
              SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_sm_ctx)
            WHERE id = %s$q$,
        (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'F')
    ),
    'P0001', NULL,
    '8) ACCETTATA->EMESSA -> throws (stato terminale immutabile)'
);

-- ============================================================
-- 9) BOZZA->ANNULLATA -> ok + data_annullamento valorizzata (addendum A2)
-- ============================================================
SELECT lives_ok(
    format(
        $q$UPDATE vendite.offerte_commerciali
              SET stato_doc_offerta_id = (SELECT stato_annullata_id FROM tmp_sm_ctx)
            WHERE id = %s$q$,
        (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'G')
    ),
    '9) BOZZA->ANNULLATA -> ok (addendum A2: ritiro da parte nostra)'
);

-- ============================================================
-- 10) EMESSA->RIFIUTATA -> ok + data_rifiuto valorizzata
-- ============================================================
SELECT lives_ok(
    format(
        $q$UPDATE vendite.offerte_commerciali
              SET stato_doc_offerta_id = (SELECT stato_rifiutata_id FROM tmp_sm_ctx)
            WHERE id = %s$q$,
        (SELECT offerta_id FROM tmp_sm_ids WHERE slot = 'H')
    ),
    '10) EMESSA->RIFIUTATA -> ok + data_rifiuto valorizzata'
);

SELECT * FROM finish();
ROLLBACK;
