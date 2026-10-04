-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Step 2.2 — Schema vendite.contratti_righe: tipo_eccezione
--       Migrations:
--         20260515-11 (CREATE TYPE + ADD COLUMN + CHECK + UNIQUE INDEX)
--         20260515-12 (trgfn + trigger guard AGGIUNTA fuori listino)
--
-- Indice test (1..17):
--   Struttura:
--   1)  ENUM tipo_eccezione_contratto esiste con 3 valori
--   2)  Colonna tipo_eccezione presente su contratti_righe
--   3)  Colonna tipo_eccezione NOT NULL
--   4)  CHECK chk_contrighe_prezzo_per_tipo_eccezione presente
--   5)  Indice uq_contrighe_one_eccezione_per_articolo presente
--   6)  Indice uq_contrighe_one_aggiunta_per_articolo presente
--   7)  Trigger guard_aggiunta_fuori_listino presente
--
--   Comportamento CHECK e UNIQUE:
--   8)  INSERT ESCLUSIONE + prezzo NULL -> ok
--   9)  INSERT ESCLUSIONE + prezzo NOT NULL -> fallisce CHECK (23514)
--   10) INSERT OVERRIDE + prezzo NULL -> fallisce CHECK (23514)
--   11) INSERT AGGIUNTA + prezzo NOT NULL su contratto senza listino -> ok
--   12) INSERT 2° OVERRIDE stessa coppia -> fallisce UNIQUE (23505)
--   13) INSERT ESCLUSIONE su coppia con OVERRIDE gia'' presente -> fallisce UNIQUE (23505)
--
--   Trigger guard AGGIUNTA fuori listino (skip se dati insufficienti):
--   14) AGGIUNTA per art IN listino (contratto DRAFT) -> fallisce guard (P0001)
--   15) AGGIUNTA per art FUORI listino (contratto DRAFT) -> ok
--   16) AGGIUNTA per art IN versione fissata (contratto ATTIVO) -> fallisce guard (P0001)
--   17) AGGIUNTA per art FUORI versione fissata (contratto ATTIVO) -> ok
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

-- ============================================================
-- Setup fixture
-- ============================================================

-- Contesto base: billing_account, utility, stati contratto, listino
CREATE TEMP TABLE tmp_s22_ctx AS
SELECT
    ba.id                                                          AS ba_id,
    ba.istanza_utility_id,
    ba.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO' LIMIT 1) AS id_attivo,
    (SELECT id FROM vendite.listini WHERE attivo = TRUE ORDER BY id LIMIT 1)             AS listino_id
  FROM anagrafiche.billing_account ba
 ORDER BY ba.id
 LIMIT 1;

-- 5 articoli non-composite attivi (per tests comportamento 8-13)
CREATE TEMP TABLE tmp_s22_arts AS
SELECT id, row_number() OVER (ORDER BY id) AS rn
  FROM catalogo.articoli
 WHERE attivo = TRUE AND is_composito = FALSE
 ORDER BY id
 LIMIT 5;

-- Versione attiva del listino + un articolo IN versione + uno FUORI versione
-- (per tests guard 14-17; può essere vuota se dati insufficienti)
CREATE TEMP TABLE tmp_s22_lv AS
SELECT
    lv.id AS versione_id,
    (
        SELECT lr.articolo_id
          FROM vendite.listini_righe lr
         WHERE lr.listino_versione_id = lv.id
           AND lr.attivo = TRUE
           AND lr.articolo_id IN (
               SELECT id FROM catalogo.articoli WHERE attivo = TRUE AND is_composito = FALSE
           )
         LIMIT 1
    ) AS art_in_listino_id,
    (
        SELECT a.id
          FROM catalogo.articoli a
         WHERE a.attivo = TRUE
           AND a.is_composito = FALSE
           AND NOT EXISTS (
               SELECT 1 FROM vendite.listini_righe lr2
                WHERE lr2.listino_versione_id = lv.id
                  AND lr2.articolo_id = a.id
                  AND lr2.attivo = TRUE
           )
         ORDER BY a.id
         LIMIT 1
    ) AS art_fuori_listino_id
  FROM vendite.listini_versioni lv
 WHERE lv.listino_id = (SELECT listino_id FROM tmp_s22_ctx LIMIT 1)
   AND lv.validita @> CURRENT_DATE
   AND lv.attivo = TRUE
 LIMIT 1;

-- Contratto A: DRAFT, senza listino (tests 8-13)
-- Date non sovrapposte per rispettare uq_contratti_no_overlap sullo stesso BA.
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S22_A',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2070-01-01', '2070-12-31'
  FROM tmp_s22_ctx c;

-- Contratto B: DRAFT, con listino (tests 14-15) — periodo 2071 distinto da A
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al, listino_id)
SELECT 'PGTAP_S22_B',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2071-01-01', '2071-12-31', c.listino_id
  FROM tmp_s22_ctx c
 WHERE c.listino_id IS NOT NULL;

-- Contratto C: ATTIVO, con listino + versione fissata (tests 16-17) — periodo 2072.
-- INSERT diretto con stato ATTIVO: il guard transizione è solo BEFORE UPDATE OF stato.
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al,
    listino_id, listino_versione_id)
SELECT 'PGTAP_S22_C',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_attivo, '2072-01-01', '2072-12-31',
       c.listino_id, lv.versione_id
  FROM tmp_s22_ctx c, tmp_s22_lv lv
 WHERE c.listino_id IS NOT NULL AND lv.versione_id IS NOT NULL;

-- Setup test 12: pre-inserisce primo OVERRIDE su art[3], contratto A.
-- Il test 12 tenterà di inserire un secondo OVERRIDE sulla stessa coppia.
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'OVERRIDE', 100.00, 1.00, 'CANONE'
  FROM vendite.contratti ca, tmp_s22_arts a
 WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 3;

-- Setup test 13: pre-inserisce primo OVERRIDE su art[4], contratto A.
-- Il test 13 tenterà di inserire un'ESCLUSIONE sulla stessa coppia.
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'OVERRIDE', 200.00, 1.00, 'CANONE'
  FROM vendite.contratti ca, tmp_s22_arts a
 WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 4;

-- ============================================================
SELECT plan(17);
-- ============================================================

-- ============================================================
-- 1) ENUM tipo_eccezione_contratto esiste con 3 valori
-- ============================================================
SELECT ok(
    (SELECT count(*) = 3
       FROM pg_enum e
       JOIN pg_type t ON t.oid = e.enumtypid
       JOIN pg_namespace n ON n.oid = t.typnamespace
      WHERE n.nspname = 'vendite'
        AND t.typname = 'tipo_eccezione_contratto'
        AND e.enumlabel IN ('OVERRIDE', 'ESCLUSIONE', 'AGGIUNTA')),
    '1) ENUM tipo_eccezione_contratto esiste con i 3 valori attesi'
);

-- ============================================================
-- 2) Colonna tipo_eccezione presente su contratti_righe
-- ============================================================
SELECT has_column(
    'vendite', 'contratti_righe', 'tipo_eccezione',
    '2) Colonna tipo_eccezione presente su vendite.contratti_righe'
);

-- ============================================================
-- 3) Colonna tipo_eccezione NOT NULL
-- ============================================================
SELECT ok(
    (SELECT is_nullable = 'NO'
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'contratti_righe'
        AND column_name  = 'tipo_eccezione'),
    '3) Colonna tipo_eccezione e'' NOT NULL'
);

-- ============================================================
-- 4) CHECK chk_contrighe_prezzo_per_tipo_eccezione presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname = 'vendite'
           AND t.relname  = 'contratti_righe'
           AND c.conname  = 'chk_contrighe_prezzo_per_tipo_eccezione'
           AND c.contype  = 'c'
    ),
    '4) CHECK chk_contrighe_prezzo_per_tipo_eccezione presente'
);

-- ============================================================
-- 5) Indice uq_contrighe_one_eccezione_per_articolo presente
-- ============================================================
SELECT has_index(
    'vendite', 'contratti_righe',
    'uq_contrighe_one_eccezione_per_articolo',
    '5) Indice uq_contrighe_one_eccezione_per_articolo presente'
);

-- ============================================================
-- 6) Indice uq_contrighe_one_aggiunta_per_articolo presente
-- ============================================================
SELECT has_index(
    'vendite', 'contratti_righe',
    'uq_contrighe_one_aggiunta_per_articolo',
    '6) Indice uq_contrighe_one_aggiunta_per_articolo presente'
);

-- ============================================================
-- 7) Trigger guard_aggiunta_fuori_listino presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti_righe'
           AND t.tgname   = 'trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd'
    ),
    '7) Trigger trg_contratti_righe_a10_guard_aggiunta_fuori_listino presente'
);

-- ============================================================
-- 8) INSERT ESCLUSIONE + prezzo NULL -> ok
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa)
      SELECT ca.id, a.id, 'ESCLUSIONE', NULL, 1.00
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 1$$,
    '8) INSERT ESCLUSIONE + prezzo NULL -> ok (CHECK soddisfatto)'
);

-- ============================================================
-- 9) INSERT ESCLUSIONE + prezzo NOT NULL -> fallisce CHECK
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa)
      SELECT ca.id, a.id, 'ESCLUSIONE', 50.00, 1.00
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 2$$,
    '23514',
    NULL,
    '9) INSERT ESCLUSIONE + prezzo NOT NULL -> fallisce CHECK'
);

-- ============================================================
-- 10) INSERT OVERRIDE + prezzo NULL -> fallisce CHECK
-- ============================================================
SELECT throws_ok(
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
    --   senza, il guard nuovo (P0001) parlerebbe prima del CHECK prezzo (23514) che qui si prova.
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
             tipo_erogazione)
      SELECT ca.id, a.id, 'OVERRIDE', NULL, 1.00, 'CANONE'
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 2$$,
    '23514',
    NULL,
    '10) INSERT OVERRIDE + prezzo NULL -> fallisce CHECK'
);

-- ============================================================
-- 11) INSERT AGGIUNTA + prezzo NOT NULL, contratto senza listino -> ok
-- ============================================================
SELECT lives_ok(
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
             tipo_erogazione)
      SELECT ca.id, a.id, 'AGGIUNTA', 99.00, 1.00, 'CANONE'
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 5$$,
    '11) INSERT AGGIUNTA + prezzo NOT NULL su contratto senza listino -> ok (guard non scatta)'
);

-- ============================================================
-- 12) INSERT 2° OVERRIDE stessa coppia -> fallisce UNIQUE
--     (setup: primo OVERRIDE gia'' inserito in fixture per art[3])
-- ============================================================
SELECT throws_ok(
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
    --   senza, il guard nuovo (P0001) parlerebbe prima della UNIQUE (23505) che qui si prova.
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
             tipo_erogazione)
      SELECT ca.id, a.id, 'OVERRIDE', 150.00, 1.00, 'CANONE'
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 3$$,
    '23505',
    NULL,
    '12) INSERT 2° OVERRIDE stessa coppia -> fallisce UNIQUE (uq_contrighe_one_eccezione_per_articolo)'
);

-- ============================================================
-- 13) INSERT ESCLUSIONE su coppia con OVERRIDE gia'' presente -> fallisce UNIQUE
--     (OVERRIDE e ESCLUSIONE non possono coesistere sulla stessa coppia)
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa)
      SELECT ca.id, a.id, 'ESCLUSIONE', NULL, 1.00
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 4$$,
    '23505',
    NULL,
    '13) INSERT ESCLUSIONE su coppia con OVERRIDE presente -> fallisce UNIQUE'
);

-- ============================================================
-- 14) AGGIUNTA per art IN listino (contratto DRAFT) -> fallisce guard
--     SKIP se contratto B o versione/articolo non disponibili
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_S22_B')
         OR (SELECT art_in_listino_id FROM tmp_s22_lv LIMIT 1) IS NULL
    THEN skip('Nessun contratto DRAFT con listino + versione attiva + art in listino - skip guard test', 1)
    ELSE throws_ok(
        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
        --   senza, il P0001 atteso verrebbe dal guard nuovo e non da E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO.
        $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
                 tipo_erogazione)
          SELECT ca.id, lv.art_in_listino_id, 'AGGIUNTA', 99.00, 1.00, 'CANONE'
            FROM vendite.contratti ca, tmp_s22_lv lv
           WHERE ca.numero = 'PGTAP_S22_B'$$,
        'P0001',
        NULL,
        '14) AGGIUNTA art IN listino (contratto DRAFT) -> fallisce guard E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO'
    )
END;

-- ============================================================
-- 15) AGGIUNTA per art FUORI listino (contratto DRAFT) -> ok
--     SKIP se contratto B o versione/articolo non disponibili
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_S22_B')
         OR (SELECT art_fuori_listino_id FROM tmp_s22_lv LIMIT 1) IS NULL
    THEN skip('Nessun contratto DRAFT con listino + articolo fuori versione - skip guard test', 1)
    ELSE lives_ok(
        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
        $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
                 tipo_erogazione)
          SELECT ca.id, lv.art_fuori_listino_id, 'AGGIUNTA', 99.00, 1.00, 'CANONE'
            FROM vendite.contratti ca, tmp_s22_lv lv
           WHERE ca.numero = 'PGTAP_S22_B'$$,
        '15) AGGIUNTA art FUORI listino (contratto DRAFT) -> ok (guard non scatta)'
    )
END;

-- ============================================================
-- 16) AGGIUNTA per art IN versione fissata (contratto ATTIVO) -> fallisce guard
--     SKIP se contratto C o versione/articolo non disponibili
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_S22_C')
         OR (SELECT art_in_listino_id FROM tmp_s22_lv LIMIT 1) IS NULL
    THEN skip('Nessun contratto ATTIVO con versione fissata + art in listino - skip guard test', 1)
    ELSE throws_ok(
        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
        --   senza, il P0001 atteso verrebbe dal guard nuovo e non da E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO.
        $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
                 tipo_erogazione)
          SELECT ca.id, lv.art_in_listino_id, 'AGGIUNTA', 99.00, 1.00, 'CANONE'
            FROM vendite.contratti ca, tmp_s22_lv lv
           WHERE ca.numero = 'PGTAP_S22_C'$$,
        'P0001',
        NULL,
        '16) AGGIUNTA art IN versione fissata (contratto ATTIVO) -> fallisce guard E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO'
    )
END;

-- ============================================================
-- 17) AGGIUNTA per art FUORI versione fissata (contratto ATTIVO) -> ok
--     SKIP se contratto C o versione/articolo non disponibili
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_S22_C')
         OR (SELECT art_fuori_listino_id FROM tmp_s22_lv LIMIT 1) IS NULL
    THEN skip('Nessun contratto ATTIVO con versione fissata + articolo fuori versione - skip guard test', 1)
    ELSE lives_ok(
        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
        $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
                 tipo_erogazione)
          SELECT ca.id, lv.art_fuori_listino_id, 'AGGIUNTA', 99.00, 1.00, 'CANONE'
            FROM vendite.contratti ca, tmp_s22_lv lv
           WHERE ca.numero = 'PGTAP_S22_C'$$,
        '17) AGGIUNTA art FUORI versione fissata (contratto ATTIVO) -> ok (guard Branch 3 non scatta)'
    )
END;

SELECT * FROM finish();
ROLLBACK;
