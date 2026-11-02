-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo pratiche.azioni_ui + aggancio
--       pratiche.template_flussi.azione_ui_id (FK).
-- Specchio FE del registry handler_flussi/handler_id, data-driven.
--
-- Indice test (1..9):
--    1. tabella pratiche.azioni_ui esiste
--    2. colonna template_flussi.azione_ui_id esiste
--    3. UNIQUE su azioni_ui.azione_ui_key
--    4. seed APRI_PREVENTIVO (id 9001) presente e attivo
--    5. FK template_flussi.azione_ui_id -> azioni_ui.id presente
--    6. azione_ui_id inesistente viola la FK (23503)
--    7. template PREVENTIVAZIONE 9002 -> azione_ui_id 9001
--    8. template PREVENTIVAZIONE 9006 -> azione_ui_id 9001
--    9. template non-PREVENTIVAZIONE (9001 RICHIESTA_CLIENTE) -> NULL
--
-- BEGIN; + ROLLBACK finale: nessuna manipolazione persiste.
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

SELECT plan(9);

-- ============================================================
-- 1) tabella catalogo esiste
-- ============================================================
SELECT has_table(
    'pratiche', 'azioni_ui',
    '1. tabella pratiche.azioni_ui esiste'
);

-- ============================================================
-- 2) colonna FK su template_flussi esiste
-- ============================================================
SELECT has_column(
    'pratiche', 'template_flussi', 'azione_ui_id',
    '2. colonna template_flussi.azione_ui_id esiste'
);

-- ============================================================
-- 3) UNIQUE su azione_ui_key
-- ============================================================
SELECT col_is_unique(
    'pratiche', 'azioni_ui', 'azione_ui_key',
    '3. UNIQUE su azioni_ui.azione_ui_key'
);

-- ============================================================
-- 4) seed APRI_PREVENTIVO presente e attivo
-- ============================================================
SELECT is(
    (SELECT attivo
       FROM pratiche.azioni_ui
      WHERE azione_ui_key = 'APRI_PREVENTIVO'),
    true,
    '4. seed APRI_PREVENTIVO (id 9001) presente e attivo'
);

-- ============================================================
-- 5) FK relationship presente
-- ============================================================
SELECT fk_ok(
    'pratiche', 'template_flussi', 'azione_ui_id',
    'pratiche', 'azioni_ui', 'id',
    '5. FK template_flussi.azione_ui_id -> azioni_ui.id'
);

-- ============================================================
-- 6) azione_ui_id inesistente viola la FK (foreign_key_violation)
-- ============================================================
SELECT throws_ok(
    $$ UPDATE pratiche.template_flussi
          SET azione_ui_id = 999999
        WHERE id = 9001 $$,
    '23503',
    NULL,
    '6. azione_ui_id inesistente viola la FK (23503)'
);

-- ============================================================
-- 7) template PREVENTIVAZIONE 9002 -> azione_ui_id 9001
-- ============================================================
SELECT is(
    (SELECT azione_ui_id FROM pratiche.template_flussi WHERE id = 9002),
    9001,
    '7. template 9002 (PREVENTIVAZIONE immediata) -> azione_ui_id 9001'
);

-- ============================================================
-- 8) template PREVENTIVAZIONE 9006 -> azione_ui_id 9001
-- ============================================================
SELECT is(
    (SELECT azione_ui_id FROM pratiche.template_flussi WHERE id = 9006),
    9001,
    '8. template 9006 (PREVENTIVAZIONE differita) -> azione_ui_id 9001'
);

-- ============================================================
-- 9) template non-PREVENTIVAZIONE -> azione_ui_id NULL
-- ============================================================
SELECT is(
    (SELECT azione_ui_id FROM pratiche.template_flussi WHERE id = 9001),
    NULL::integer,
    '9. template 9001 (RICHIESTA_CLIENTE) -> azione_ui_id NULL'
);

SELECT * FROM finish();
ROLLBACK;
