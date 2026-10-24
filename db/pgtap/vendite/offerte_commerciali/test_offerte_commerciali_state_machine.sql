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
--   2)  BOZZA->EMESSA, versione NULL, listino SENZA versione in vigore -> throws
--       E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO. ⚠️ Rev 2026-10-07
--       (brief-db-offerta-emissione-ed-erogazione §C.1.3): con la versione NULL
--       il guard CONGELA quella in vigore, quindi il rifiuto vuole un listino che
--       non ne ha. Il listino dello slot A e' COSTRUITO (versione 2022 scaduta):
--       quello «primo per id» del DB rispondeva secondo i dati.
--       Il congelamento sta in test-offerta-emissione-congela-listino-v1.
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
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): l'offerta dello slot F
--   nasce in bozza e si porta avanti con dbops.fn_pgtap_porta_a_stato (prima
--   nasceva gia' ACCETTATA).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(10);

-- ============================================================
-- Setup fixture: contesti di riferimento
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce (contesto gia' aperto); listino, con la
--   sua versione ATTIVA da oggi, sulla stessa utility.
CREATE TEMP TABLE tmp_sm_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'state machine offerte',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_sm_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_sm_cli), 'state machine offerte');

CREATE TEMP TABLE tmp_sm_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_sm_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_sm_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_sm_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_sm_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_sm_listino) AS listino_versione_id_attiva,
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

-- Slot A: BOZZA, listino_versione_id NULL, listino senza versione in vigore
--   (test 2). Listino costruito: la sola versione e' del 2022.
CREATE TEMP TABLE tmp_sm_listino_scaduto AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_sm_ctx), 'state machine scaduto',
    DATE '2022-01-01', DATE '2022-12-31');

WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           (SELECT listino_id FROM tmp_sm_listino_scaduto), NULL, DATE '2082-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'A', id FROM ins;

-- Slot B: BOZZA, versione NON ATTIVA (test 3). 2026-10-08 (§F.2): la versione
--   CHIUSA si costruisce: e' quella del listino scaduto dello slot A, chiusa qui
--   (ATTIVA -> CHIUSA e' ammessa perche' valido_al e' passato). Prima era «la
--   prima versione non ATTIVA di un listino qualsiasi», scollegata dal listino.
--   Lo slot A non cambia esito: il listino resta senza versione in vigore.
UPDATE vendite.listini_versioni SET stato = 'CHIUSA'
 WHERE id = (SELECT listino_versione_id FROM tmp_sm_listino_scaduto);

WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           (SELECT listino_id FROM tmp_sm_listino_scaduto),
           (SELECT listino_versione_id FROM tmp_sm_listino_scaduto),
           DATE '2083-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
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

-- Slot F: ACCETTATA (test 8: ACCETTATA->EMESSA fails). Nasce in BOZZA e
-- arriva ad ACCETTATA per la matrice, sotto il guard di transizione
-- (rev 2026-10-24: prima nasceva gia' ACCETTATA).
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2087-01-01', ctx.stato_bozza_id
      FROM tmp_sm_ctx ctx
    RETURNING id
)
INSERT INTO tmp_sm_ids SELECT 'F', id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', i.offerta_id, 'ACCETTATA')
  FROM tmp_sm_ids i
 WHERE i.slot = 'F';

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
    '2) BOZZA->EMESSA, versione NULL, listino senza versione in vigore -> throws E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO'
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
