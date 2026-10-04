-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Step 2.3 — Trigger freeze listino_versione_id + lock post-attivazione
--       Migrations:
--         20260515-13 (freeze listino_versione_id su DRAFT→ATTIVO)
--         20260515-14 (lock post-attivazione testata + righe)
--
-- Indice test (1..13):
--   Struttura:
--   1)  Trigger freeze_listino_versione presente su contratti
--   2)  Trigger lock_post_attivazione presente su contratti
--   3)  Il BB delle righe (trg_contratti_righe_a05_doc_righe_lock_fuori_bozza) presente su contratti_righe (rev 22-09)
--
--   Freeze versione e guard negoziato puro:
--   4)  DRAFT→ATTIVO senza listino + nessuna AGGIUNTA -> errore E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE
--   5)  DRAFT→ATTIVO senza listino + AGGIUNTA con prezzo -> ok
--   6)  (COND) DRAFT→ATTIVO con listino + versione attiva -> listino_versione_id fissato
--
--   Lock post-attivazione testata (contratti ATTIVI):
--   7)  UPDATE listino_id su contratto ATTIVO -> bloccato
--   8)  UPDATE valore_variazione_globale su contratto ATTIVO -> bloccato
--   9)  UPDATE valore_variazione_globale su contratto DRAFT -> ok
--
--   Lock post-attivazione righe:
--   10) INSERT riga su contratto ATTIVO -> bloccato
--   11) UPDATE riga su contratto ATTIVO -> bloccato
--   12) DELETE riga su contratto ATTIVO -> bloccato
--   13) INSERT riga su contratto DRAFT -> ok
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

CREATE TEMP TABLE tmp_s23_ctx AS
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

-- 3 articoli per i test righe
CREATE TEMP TABLE tmp_s23_arts AS
SELECT id, row_number() OVER (ORDER BY id) AS rn
  FROM catalogo.articoli
 WHERE attivo = TRUE AND is_composito = FALSE
 ORDER BY id
 LIMIT 3;

-- Versione attiva del listino (per test 6 — condizionale)
CREATE TEMP TABLE tmp_s23_lv AS
SELECT lv.id AS versione_id
  FROM vendite.listini_versioni lv
 WHERE lv.listino_id = (SELECT listino_id FROM tmp_s23_ctx LIMIT 1)
   AND lv.validita @> CURRENT_DATE
   AND lv.attivo = TRUE
 LIMIT 1;

-- Contratto ATT: DRAFT, senza listino, con riga AGGIUNTA.
-- Verrà transitato ad ATTIVO durante il setup (dopo insert riga).
-- Usato per: test 7, 8, 10, 11, 12.
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S23_ATT',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2070-01-01', '2070-12-31'
  FROM tmp_s23_ctx c;

-- Insert riga AGGIUNTA su ATT (mentre è DRAFT: lock non scatta)
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'AGGIUNTA', 99.00, 1.00, 'CANONE'
  FROM vendite.contratti ca, tmp_s23_arts a
 WHERE ca.numero = 'PGTAP_S23_ATT' AND a.rn = 1;

-- Transizione ATT → ATTIVO (freeze trigger scatta: listino_id NULL + riga AGGIUNTA → ok)
UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_s23_ctx)
 WHERE numero = 'PGTAP_S23_ATT';

-- Contratto NEG_PURO: DRAFT, senza listino, senza righe (per test 4)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S23_NEG_PURO',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2071-01-01', '2071-12-31'
  FROM tmp_s23_ctx c;

-- Contratto NEG_OK: DRAFT, senza listino, con riga AGGIUNTA (per test 5)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S23_NEG_OK',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2072-01-01', '2072-12-31'
  FROM tmp_s23_ctx c;

-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'AGGIUNTA', 50.00, 1.00, 'CANONE'
  FROM vendite.contratti ca, tmp_s23_arts a
 WHERE ca.numero = 'PGTAP_S23_NEG_OK' AND a.rn = 2;

-- Contratto DRAFT: DRAFT, senza listino (per test 9 e 13)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S23_DRAFT',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2073-01-01', '2073-12-31'
  FROM tmp_s23_ctx c;

-- Contratto LV: DRAFT, con listino (per test 6 — condizionale)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al, listino_id)
SELECT 'PGTAP_S23_LV',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2074-01-01', '2074-12-31', c.listino_id
  FROM tmp_s23_ctx c
 WHERE c.listino_id IS NOT NULL;

-- Transizione LV → ATTIVO nel fixture (condizionale: solo se versione attiva disponibile).
-- Il freeze trigger imposta listino_versione_id dal risultato della ricerca versione.
-- Se versione non trovata il test 6 fa skip.
UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_s23_ctx)
 WHERE numero = 'PGTAP_S23_LV'
   AND EXISTS (SELECT 1 FROM tmp_s23_lv WHERE versione_id IS NOT NULL);

-- ============================================================
SELECT plan(13);
-- ============================================================

-- ============================================================
-- 1) Trigger freeze_listino_versione presente su contratti
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti'
           AND t.tgname   = 'trg_contratti_a10_freeze_listino_versione_upd'
    ),
    '1) Trigger trg_contratti_a10_freeze_listino_versione_upd presente'
);

-- ============================================================
-- 2) Trigger lock_post_attivazione presente su contratti
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti'
           AND t.tgname   = 'trg_contratti_a10_lock_post_attivazione_upd'
    ),
    '2) Trigger trg_contratti_a10_lock_post_attivazione_upd presente su contratti'
);

-- ============================================================
-- 3) Il BB delle righe e' montato su contratti_righe
--    rev 2026-09-22: trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt e la
--    sua funzione sono ritirati (20260922-06); la regola «righe solo in bozza» e'
--    il building block vendite.trgfn_doc_righe_lock_fuori_bozza, fascia _a05_.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti_righe'
           AND t.tgname   = 'trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt'
    ),
    '3) Trigger trg_contratti_righe_a05_doc_righe_lock_fuori_bozza presente su contratti_righe'
);

-- ============================================================
-- 4) DRAFT→ATTIVO senza listino, senza righe AGGIUNTA -> errore
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')
       WHERE numero = 'PGTAP_S23_NEG_PURO'$$,
    'P0001',
    NULL,
    '4) DRAFT→ATTIVO senza listino + nessuna AGGIUNTA -> errore E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE'
);

-- ============================================================
-- 5) DRAFT→ATTIVO senza listino + AGGIUNTA con prezzo -> ok
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')
       WHERE numero = 'PGTAP_S23_NEG_OK'$$,
    '5) DRAFT→ATTIVO senza listino + AGGIUNTA con prezzo -> ok (freeze non blocca)'
);

-- ============================================================
-- 6) DRAFT→ATTIVO con listino + versione attiva -> listino_versione_id fissato
--    La transizione è avvenuta nel fixture; il test verifica solo il risultato.
--    SKIP se nessun contratto LV creato o nessuna versione attiva disponibile.
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_S23_LV')
         OR (SELECT versione_id FROM tmp_s23_lv LIMIT 1) IS NULL
    THEN skip('Nessun listino con versione attiva disponibile - skip test freeze versione', 1)
    ELSE ok(
        (SELECT listino_versione_id IS NOT NULL
           FROM vendite.contratti
          WHERE numero = 'PGTAP_S23_LV'),
        '6) DRAFT→ATTIVO con listino + versione attiva -> listino_versione_id fissato dal freeze trigger'
    )
END;

-- ============================================================
-- 7) UPDATE listino_id su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET listino_id = (SELECT id FROM vendite.listini WHERE attivo = TRUE ORDER BY id LIMIT 1)
       WHERE numero = 'PGTAP_S23_ATT'$$,
    'P0001',
    NULL,
    '7) UPDATE listino_id su contratto ATTIVO -> bloccato E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE'
);

-- ============================================================
-- 8) UPDATE valore_variazione_globale su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET valore_variazione_globale = -5
       WHERE numero = 'PGTAP_S23_ATT'$$,
    'P0001',
    NULL,
    '8) UPDATE valore_variazione_globale su contratto ATTIVO -> bloccato'
);

-- ============================================================
-- 9) UPDATE valore_variazione_globale su contratto DRAFT -> ok
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET tipo_variazione_globale  = 'PERCENTUALE',
             valore_variazione_globale = -3
       WHERE numero = 'PGTAP_S23_DRAFT'$$,
    '9) UPDATE variazione globale su contratto DRAFT -> ok (lock non scatta)'
);

-- ============================================================
-- 10) INSERT riga su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
    --   senza, il P0001 atteso verrebbe dal guard nuovo e non da E_RIGA_DOC_NON_BOZZA.
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
             tipo_erogazione)
      SELECT ca.id, a.id, 'AGGIUNTA', 10.00, 1.00, 'CANONE'
        FROM vendite.contratti ca, tmp_s23_arts a
       WHERE ca.numero = 'PGTAP_S23_ATT' AND a.rn = 2$$,
    'P0001',
    NULL,
    '10) INSERT riga su contratto ATTIVO -> bloccato E_RIGA_DOC_NON_BOZZA (BB, dal 22-09)'
);

-- ============================================================
-- 11) UPDATE riga su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti_righe cr
         SET ordine = 99
        FROM vendite.contratti ca
       WHERE ca.numero = 'PGTAP_S23_ATT'
         AND cr.contratto_id = ca.id$$,
    'P0001',
    NULL,
    '11) UPDATE riga su contratto ATTIVO -> bloccato'
);

-- ============================================================
-- 12) DELETE riga su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    $$DELETE FROM vendite.contratti_righe cr
       USING vendite.contratti ca
       WHERE ca.numero = 'PGTAP_S23_ATT'
         AND cr.contratto_id = ca.id$$,
    'P0001',
    NULL,
    '12) DELETE riga su contratto ATTIVO -> bloccato'
);

-- ============================================================
-- 13) INSERT riga su contratto DRAFT -> ok
-- ============================================================
SELECT lives_ok(
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
             tipo_erogazione)
      SELECT ca.id, a.id, 'AGGIUNTA', 20.00, 1.00, 'CANONE'
        FROM vendite.contratti ca, tmp_s23_arts a
       WHERE ca.numero = 'PGTAP_S23_DRAFT' AND a.rn = 3$$,
    '13) INSERT riga su contratto DRAFT -> ok (lock non scatta)'
);

SELECT * FROM finish();
ROLLBACK;
