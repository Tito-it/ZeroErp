-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--   7)  Trigger del guard di articolo presente (dal Lotto 3b: AGGIUNTA gia' in listino
--       e' un motivo di script.fn_check_articolo_riga; il guard dedicato e' ritirato)
--
--   Comportamento CHECK e UNIQUE:
--   8)  INSERT ESCLUSIONE + prezzo NULL -> ok
--   9)  INSERT ESCLUSIONE + prezzo NOT NULL -> rifiutata (dal 2026-10-04 parla il guard
--       E_RIGA_ESCLUSIONE_CON_DATI, P0001, prima del CHECK 23514, che resta la rete)
--   10) INSERT OVERRIDE + prezzo NULL -> fallisce CHECK (23514)
--   11) INSERT AGGIUNTA + prezzo NOT NULL su contratto senza listino -> ok
--   12) INSERT 2° OVERRIDE stessa coppia -> fallisce UNIQUE (23505)
--   13) INSERT ESCLUSIONE su coppia con OVERRIDE gia'' presente -> fallisce UNIQUE (23505)
--
--   Trigger guard AGGIUNTA fuori listino (skip se dati insufficienti):
--   14) AGGIUNTA per art IN listino (contratto DRAFT) -> fallisce guard (P0001)
--   15) AGGIUNTA per art FUORI listino (contratto DRAFT) -> ok
--   16) AGGIUNTA per art IN versione fissata (contratto DRAFT) -> fallisce guard (P0001)
--   17) AGGIUNTA per art FUORI versione fissata (contratto DRAFT) -> ok
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
-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5):
--   FIXTURE RISCRITTA, TUTTA COSTRUITA. Prima cliente, listino e articoli si
--   pescavano dal database, e il contratto A (senza listino) riceveva OVERRIDE
--   ed ESCLUSIONE: righe che modificano un listino che non c'e', e che dal
--   Lotto 3b sono rifiutate (E_RIGA_ECCEZIONE_SENZA_LISTINO). Ora: un cliente,
--   un listino con la versione di oggi, sei articoli — 1..4 nel listino, 5 e 6
--   fuori. Erogazione e fonte le eredita il DB dall'articolo (la tipologia del
--   listino dipende dalla utility), la quantita' c'e' solo se la fonte
--   ereditata e' FISSA (pg_temp.qta).
--   I contratti: A (DRAFT, col listino, test 8-13), B (DRAFT, col listino,
--   test 14-15), C (DRAFT, col listino e la VERSIONE FISSATA, test 16-17).
--   ⚠️ C era ATTIVO: su un contratto attivo le righe non si scrivono affatto
--   (lock fuori bozza, Step 2.3), e i test 16-17 su dbdev passavano solo perche'
--   la pesca non trovava il listino e li saltava. Il loro soggetto e' la
--   versione fissata, che un DRAFT puo' portare.
CREATE TEMP TABLE tmp_s22_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('schema step22');

CREATE TEMP TABLE tmp_s22_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_s22_mondo), 'schema step22');

CREATE TEMP TABLE tmp_s22_ctx AS
SELECT
    m.billing_account_id                                                            AS ba_id,
    m.istanza_utility_id,
    m.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO' LIMIT 1) AS id_attivo,
    (SELECT listino_id FROM tmp_s22_listino)                                        AS listino_id
  FROM tmp_s22_mondo m;

CREATE TEMP TABLE tmp_s22_arts AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-S22-' || g, false) AS id, g AS rn
  FROM generate_series(1, 6) AS g;

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT listino_versione_id FROM tmp_s22_listino),
    ARRAY(SELECT id FROM tmp_s22_arts WHERE rn <= 4 ORDER BY rn));

CREATE TEMP TABLE tmp_s22_lv AS
SELECT (SELECT listino_versione_id FROM tmp_s22_listino) AS versione_id,
       (SELECT id FROM tmp_s22_arts WHERE rn = 1)        AS art_in_listino_id,
       (SELECT id FROM tmp_s22_arts WHERE rn = 6)        AS art_fuori_listino_id;

-- Scopo: la quantita' di una riga che eredita dall'articolo: 1 se la fonte di
--   default e' FISSA, altrimenti vuota (la fonte la porta a valle).
CREATE OR REPLACE FUNCTION pg_temp.qta(p_articolo uuid)
RETURNS numeric LANGUAGE sql STABLE AS $fx$
  SELECT 1.00 FROM vendite.fn_articolo_erogazioni(p_articolo) e
   WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1;
$fx$;

-- I tre contratti, su periodi che non si sovrappongono (ex_contratti_no_overlap).
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al, listino_id, listino_versione_id)
SELECT v.numero, c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, v.dal, v.al, c.listino_id,
       CASE WHEN v.fissata THEN (SELECT versione_id FROM tmp_s22_lv) END
  FROM tmp_s22_ctx c,
       (VALUES ('PGTAP_S22_A', DATE '2070-01-01', DATE '2070-12-31', false),
               ('PGTAP_S22_B', DATE '2071-01-01', DATE '2071-12-31', false),
               ('PGTAP_S22_C', DATE '2072-01-01', DATE '2072-12-31', true)) AS v(numero, dal, al, fissata);

-- Setup test 12: pre-inserisce primo OVERRIDE su art[3], contratto A.
-- Il test 12 tenterà di inserire un secondo OVERRIDE sulla stessa coppia.
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'OVERRIDE', 100.00, pg_temp.qta(a.id), NULL
  FROM vendite.contratti ca, tmp_s22_arts a
 WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 3;

-- Setup test 13: pre-inserisce primo OVERRIDE su art[4], contratto A.
-- Il test 13 tenterà di inserire un'ESCLUSIONE sulla stessa coppia.
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'OVERRIDE', 200.00, pg_temp.qta(a.id), NULL
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
-- 7) Trigger del guard di articolo presente (rev 2026-10-13, Lotto 3b)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti_righe'
           AND t.tgname   = 'trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd'
    ),
    '7) Trigger trg_contratti_righe_a10_guard_articolo_ammesso presente'
);

-- ============================================================
-- 8) INSERT ESCLUSIONE + prezzo NULL -> ok
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario)
      SELECT ca.id, a.id, 'ESCLUSIONE', NULL
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 1$$,
    '8) INSERT ESCLUSIONE + prezzo NULL -> ok (CHECK soddisfatto)'
);

-- ============================================================
-- 9) INSERT ESCLUSIONE + prezzo NOT NULL -> fallisce CHECK
-- ============================================================
-- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): un'esclusione
--   non porta dati di vendita, e a dirlo e' il guard col campo (P0001), prima
--   del CHECK sul prezzo. Il CHECK resta la rete per le strade senza trigger.
SELECT throws_like(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario)
      SELECT ca.id, a.id, 'ESCLUSIONE', 50.00
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 2$$,
    '%non porta prezzo, quantità né erogazione%',
    '9) INSERT ESCLUSIONE + prezzo NOT NULL -> rifiutata dal guard dell''esclusione'
);

-- ============================================================
-- 10) INSERT OVERRIDE + prezzo NULL -> fallisce CHECK
-- ============================================================
SELECT throws_ok(
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
    --   senza, il guard nuovo (P0001) parlerebbe prima del CHECK prezzo (23514) che qui si prova.
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
             tipo_erogazione)
      SELECT ca.id, a.id, 'OVERRIDE', NULL, pg_temp.qta(a.id), NULL
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
      SELECT ca.id, a.id, 'AGGIUNTA', 99.00, pg_temp.qta(a.id), NULL
        FROM vendite.contratti ca, tmp_s22_arts a
       WHERE ca.numero = 'PGTAP_S22_A' AND a.rn = 5$$,
    '11) INSERT AGGIUNTA + prezzo NOT NULL di un articolo fuori listino -> ok (guard non scatta)'
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
      SELECT ca.id, a.id, 'OVERRIDE', 150.00, pg_temp.qta(a.id), NULL
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
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario)
      SELECT ca.id, a.id, 'ESCLUSIONE', NULL
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
          SELECT ca.id, lv.art_in_listino_id, 'AGGIUNTA', 99.00, pg_temp.qta(lv.art_in_listino_id), NULL
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
          SELECT ca.id, lv.art_fuori_listino_id, 'AGGIUNTA', 99.00, pg_temp.qta(lv.art_fuori_listino_id), NULL
            FROM vendite.contratti ca, tmp_s22_lv lv
           WHERE ca.numero = 'PGTAP_S22_B'$$,
        '15) AGGIUNTA art FUORI listino (contratto DRAFT) -> ok (guard non scatta)'
    )
END;

-- ============================================================
-- 16) AGGIUNTA per art IN versione fissata (contratto DRAFT) -> fallisce guard
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
          SELECT ca.id, lv.art_in_listino_id, 'AGGIUNTA', 99.00, pg_temp.qta(lv.art_in_listino_id), NULL
            FROM vendite.contratti ca, tmp_s22_lv lv
           WHERE ca.numero = 'PGTAP_S22_C'$$,
        'P0001',
        NULL,
        '16) AGGIUNTA art IN versione fissata (contratto DRAFT) -> fallisce guard E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO'
    )
END;

-- ============================================================
-- 17) AGGIUNTA per art FUORI versione fissata (contratto DRAFT) -> ok
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
          SELECT ca.id, lv.art_fuori_listino_id, 'AGGIUNTA', 99.00, pg_temp.qta(lv.art_fuori_listino_id), NULL
            FROM vendite.contratti ca, tmp_s22_lv lv
           WHERE ca.numero = 'PGTAP_S22_C'$$,
        '17) AGGIUNTA art FUORI versione fissata (contratto DRAFT) -> ok (guard non scatta)'
    )
END;

SELECT * FROM finish();
ROLLBACK;
