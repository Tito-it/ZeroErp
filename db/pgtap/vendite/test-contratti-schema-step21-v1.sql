-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Step 2.1 — Schema vendite.contratti: listino_versione_id + cleanup modalità
--       Migrations:
--         20260515-10 (ALTER contratti: ADD listino_versione_id, DROP CHECK/trigger)
--
-- Indice test (1..9):
--   1)  Colonna listino_versione_id presente
--   2)  Colonna nullable (bigint NULL)
--   3)  FK fk_contratti_listino_versione presente
--   4)  Indice ix_contratti_listino_versione presente
--   5)  CHECK chk_contratti_modalita_pricing rimosso
--   6)  CHECK chk_contratti_variazione_globale_coerente rimosso
--   7)  Trigger trg_contratti_a10_guard_modalita_c_activation_ins_upd rimosso (contratti)
--   8)  Trigger trg_contratti_righe_a10_guard_modalita_c_ins_upd rimosso (contratti_righe)
--   9)  INSERT contratto DRAFT con listino_versione_id=NULL -> ok (nuova colonna)
--  10)  INSERT contratto DRAFT con listino_id=NULL + tipo_variazione='PERCENTUALE' -> ok
--       (era bloccato da chk_contratti_modalita_pricing)
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

SELECT plan(10);

-- ============================================================
-- Setup fixture
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza tipi_utenze,
--   legato dal z90 all'emittente di chi agisce; listino sulla stessa utility. Un
--   cliente nuovo non ha contratti: niente sovrapposizioni con quelli dei dati.
CREATE TEMP TABLE tmp_ctx_ba AS
SELECT c.billing_account_id,
       c.istanza_utility_id,
       c.utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba(
           'schema step21',
           (SELECT u.id FROM config.utilities u
             WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
             ORDER BY u.id LIMIT 1)) c;

CREATE TEMP TABLE tmp_ctx_stati AS
SELECT
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT') AS id_draft;

CREATE TEMP TABLE tmp_ctx_listino AS
SELECT listino_id FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_ctx_ba), 'schema step21');

-- ============================================================
-- 1) Colonna listino_versione_id presente
-- ============================================================
SELECT has_column(
    'vendite', 'contratti', 'listino_versione_id',
    '1) Colonna listino_versione_id presente su vendite.contratti'
);

-- ============================================================
-- 2) Colonna nullable bigint
-- ============================================================
SELECT ok(
    (SELECT is_nullable = 'YES' AND data_type = 'bigint'
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'contratti'
        AND column_name  = 'listino_versione_id'),
    '2) listino_versione_id e'' bigint nullable'
);

-- ============================================================
-- 3) FK fk_contratti_listino_versione presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname = 'vendite'
           AND t.relname  = 'contratti'
           AND c.conname  = 'fk_contratti_listino_versione'
           AND c.contype  = 'f'
    ),
    '3) FK fk_contratti_listino_versione presente'
);

-- ============================================================
-- 4) Indice ix_contratti_listino_versione presente
-- ============================================================
SELECT has_index(
    'vendite', 'contratti',
    'ix_contratti_listino_versione',
    '4) Indice ix_contratti_listino_versione presente'
);

-- ============================================================
-- 5) CHECK chk_contratti_modalita_pricing rimosso
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname = 'vendite'
           AND t.relname  = 'contratti'
           AND c.conname  = 'chk_contratti_modalita_pricing'
    ),
    '5) CHECK chk_contratti_modalita_pricing rimosso'
);

-- ============================================================
-- 6) CHECK chk_contratti_variazione_globale_coerente rimosso
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname = 'vendite'
           AND t.relname  = 'contratti'
           AND c.conname  = 'chk_contratti_variazione_globale_coerente'
    ),
    '6) CHECK chk_contratti_variazione_globale_coerente rimosso'
);

-- ============================================================
-- 7) Trigger guard modalita' C rimosso da vendite.contratti
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti'
           AND t.tgname   = 'trg_contratti_a10_guard_modalita_c_activation_ins_upd'
    ),
    '7) Trigger guard modalita_c rimosso da vendite.contratti'
);

-- ============================================================
-- 8) Trigger guard modalita' C rimosso da vendite.contratti_righe
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti_righe'
           AND t.tgname   = 'trg_contratti_righe_a10_guard_modalita_c_ins_upd'
    ),
    '8) Trigger guard modalita_c rimosso da vendite.contratti_righe'
);

-- ============================================================
-- 9) INSERT contratto DRAFT con listino_versione_id=NULL -> ok
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id,
          stato_doc_contratto_id, valido_dal, valido_al,
          listino_id, tipo_variazione_globale, valore_variazione_globale,
          listino_versione_id)
      SELECT 'PGTAP_STEP21_A',
             ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             s.id_draft, '2070-01-01', '2070-12-31',
             l.listino_id, 'PERCENTUALE', -5,
             NULL
        FROM tmp_ctx_ba ba, tmp_ctx_stati s, tmp_ctx_listino l$$,
    '9) INSERT contratto DRAFT con listino_versione_id=NULL -> ok'
);

-- ============================================================
-- 10) INSERT contratto DRAFT con listino_id=NULL + variazione -> ok
--     (era bloccato da chk_contratti_modalita_pricing)
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id,
          stato_doc_contratto_id, valido_dal, valido_al,
          listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_STEP21_B',
             ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             s.id_draft, '2071-01-01', '2071-12-31',
             NULL, 'PERCENTUALE', 5
        FROM tmp_ctx_ba ba, tmp_ctx_stati s$$,
    '10) INSERT contratto DRAFT con listino=NULL + variazione -> ok (CHECK rimosso)'
);

SELECT * FROM finish();
ROLLBACK;
