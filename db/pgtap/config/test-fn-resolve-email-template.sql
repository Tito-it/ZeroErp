-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.fn_resolve_email_template
--       Risoluzione template email con fallback a 5 livelli:
--       1. reparto + tipo prestazione + lingua
--       2. reparto + lingua (no tipo)
--       3. sistema + tipo prestazione + lingua
--       4. sistema + lingua
--       5. sistema + lingua 'it' (fallback finale)
--
-- Elenco test:
--  1)  codice NULL → NULL
--  2)  template sistema it → trovato (livello 4)
--  3)  template sistema it, richiesta lingua 'en' non presente → fallback it (livello 5)
--  4)  template sistema 'en' presente → trovato lingua en (livello 4)
--  5)  template sistema + tipo prestazione → trovato (livello 3)
--  6)  template reparto + lingua → trovato (livello 2)
--  7)  template reparto + tipo prestazione + lingua → trovato (livello 1)
--  8)  livello 1 ha priorita' su livello 2
--  9)  livello 2 ha priorita' su livello 3
-- 10)  template inattivo ignorato → fallback
-- 11)  codice inesistente → NULL
-- 12)  codice in minuscolo → trovato: config.email_template salva il codice
--       in maiuscolo (CODICE_MAIUSCOLO), la ricerca lo normalizza (20261104-38)
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

SELECT plan(12);

-- ============================================================
-- 0. Setup: raccolta riferimenti e creazione template di test
-- ============================================================

-- UO e tipo prestazione di test
CREATE TEMP TABLE tmp_tpl_ctx AS
SELECT
    uo.id AS uo_id,
    tp.id AS tp_id
FROM config.unita_organizzative uo
CROSS JOIN pratiche.tipi_prestazione tp
WHERE uo.attivo = true AND tp.attivo = true
ORDER BY uo.id, tp.id
LIMIT 1;

-- Codice template di test (univoco per evitare conflitti)
-- Usiamo un codice che non esiste nel seed

-- Livello 4: sistema + it (base)
INSERT INTO config.email_template
    (codice, unita_organizzativa_id, tipo_prestazione_id, lingua,
     oggetto, corpo_html, variabili_disponibili, attivo)
VALUES
    ('_PGTAP_TEST_TPL', NULL, NULL, 'it',
     'Oggetto sistema it', '<p>Corpo sistema it</p>',
     '["nome"]'::jsonb, true);

-- Livello 4 inglese: sistema + en
INSERT INTO config.email_template
    (codice, unita_organizzativa_id, tipo_prestazione_id, lingua,
     oggetto, corpo_html, variabili_disponibili, attivo)
VALUES
    ('_PGTAP_TEST_TPL', NULL, NULL, 'en',
     'Subject system en', '<p>Body system en</p>',
     '["name"]'::jsonb, true);

-- Livello 3: sistema + tipo prestazione + it
INSERT INTO config.email_template
    (codice, unita_organizzativa_id, tipo_prestazione_id, lingua,
     oggetto, corpo_html, variabili_disponibili, attivo)
VALUES
    ('_PGTAP_TEST_TPL', NULL,
     (SELECT tp_id FROM tmp_tpl_ctx), 'it',
     'Oggetto sistema+tipo it', '<p>Corpo sistema+tipo it</p>',
     '["nome"]'::jsonb, true);

-- Livello 2: reparto + it
INSERT INTO config.email_template
    (codice, unita_organizzativa_id, tipo_prestazione_id, lingua,
     oggetto, corpo_html, variabili_disponibili, attivo)
VALUES
    ('_PGTAP_TEST_TPL',
     (SELECT uo_id FROM tmp_tpl_ctx), NULL, 'it',
     'Oggetto reparto it', '<p>Corpo reparto it</p>',
     '["nome"]'::jsonb, true);

-- Livello 1: reparto + tipo prestazione + it
INSERT INTO config.email_template
    (codice, unita_organizzativa_id, tipo_prestazione_id, lingua,
     oggetto, corpo_html, variabili_disponibili, attivo)
VALUES
    ('_PGTAP_TEST_TPL',
     (SELECT uo_id FROM tmp_tpl_ctx),
     (SELECT tp_id FROM tmp_tpl_ctx), 'it',
     'Oggetto reparto+tipo it', '<p>Corpo reparto+tipo it</p>',
     '["nome"]'::jsonb, true);

-- Template inattivo per test 10
INSERT INTO config.email_template
    (codice, unita_organizzativa_id, tipo_prestazione_id, lingua,
     oggetto, corpo_html, variabili_disponibili, attivo)
VALUES
    ('_PGTAP_TEST_INATTIVO', NULL, NULL, 'it',
     'Non usare', '<p>Inattivo</p>',
     '[]'::jsonb, false);

-- ============================================================
-- 1) codice NULL → NULL
-- ============================================================
SELECT is(
    config.fn_resolve_email_template(NULL),
    NULL::jsonb,
    'codice NULL → NULL'
);

-- ============================================================
-- 2) Template sistema it → trovato (livello 4)
-- ============================================================
SELECT is(
    (config.fn_resolve_email_template('_PGTAP_TEST_TPL'))->>'oggetto',
    'Oggetto sistema it',
    'fn_resolve: senza parametri opzionali → sistema it (livello 4)'
);

-- ============================================================
-- 3) Richiesta lingua 'de' non presente → fallback it (livello 5)
-- ============================================================
SELECT is(
    (config.fn_resolve_email_template('_PGTAP_TEST_TPL', NULL, NULL, 'de'))->>'lingua',
    'it',
    'fn_resolve: lingua de non presente → fallback it (livello 5)'
);

-- ============================================================
-- 4) Lingua 'en' presente → trovato (livello 4)
-- ============================================================
SELECT is(
    (config.fn_resolve_email_template('_PGTAP_TEST_TPL', NULL, NULL, 'en'))->>'oggetto',
    'Subject system en',
    'fn_resolve: lingua en presente → sistema en (livello 4)'
);

-- ============================================================
-- 5) Sistema + tipo prestazione → livello 3
-- ============================================================
SELECT is(
    (config.fn_resolve_email_template(
        '_PGTAP_TEST_TPL', NULL,
        (SELECT tp_id FROM tmp_tpl_ctx), 'it'
    ))->>'oggetto',
    'Oggetto sistema+tipo it',
    'fn_resolve: sistema + tipo prestazione → livello 3'
);

-- ============================================================
-- 6) Reparto + lingua → livello 2
-- ============================================================
SELECT is(
    (config.fn_resolve_email_template(
        '_PGTAP_TEST_TPL',
        (SELECT uo_id FROM tmp_tpl_ctx), NULL, 'it'
    ))->>'oggetto',
    'Oggetto reparto it',
    'fn_resolve: reparto senza tipo → livello 2'
);

-- ============================================================
-- 7) Reparto + tipo prestazione + lingua → livello 1
-- ============================================================
SELECT is(
    (config.fn_resolve_email_template(
        '_PGTAP_TEST_TPL',
        (SELECT uo_id FROM tmp_tpl_ctx),
        (SELECT tp_id FROM tmp_tpl_ctx), 'it'
    ))->>'oggetto',
    'Oggetto reparto+tipo it',
    'fn_resolve: reparto + tipo → livello 1 (massima specializzazione)'
);

-- ============================================================
-- 8) Livello 1 ha priorita' su livello 2
--    (chiamo con reparto + tipo: deve trovare livello 1, non 2)
-- ============================================================
SELECT isnt(
    (config.fn_resolve_email_template(
        '_PGTAP_TEST_TPL',
        (SELECT uo_id FROM tmp_tpl_ctx),
        (SELECT tp_id FROM tmp_tpl_ctx), 'it'
    ))->>'oggetto',
    'Oggetto reparto it',
    'fn_resolve: livello 1 ha priorita'' su livello 2'
);

-- ============================================================
-- 9) Livello 2 ha priorita' su livello 3
--    Cancello livello 1 e chiamo con reparto + tipo:
--    deve trovare livello 2, non livello 3
-- ============================================================
DELETE FROM config.email_template
 WHERE codice = '_PGTAP_TEST_TPL'
   AND unita_organizzativa_id = (SELECT uo_id FROM tmp_tpl_ctx)
   AND tipo_prestazione_id = (SELECT tp_id FROM tmp_tpl_ctx);

SELECT is(
    (config.fn_resolve_email_template(
        '_PGTAP_TEST_TPL',
        (SELECT uo_id FROM tmp_tpl_ctx),
        (SELECT tp_id FROM tmp_tpl_ctx), 'it'
    ))->>'oggetto',
    'Oggetto reparto it',
    'fn_resolve: senza livello 1, fallback a livello 2 (non livello 3)'
);

-- ============================================================
-- 10) Template inattivo ignorato → NULL
-- ============================================================
SELECT is(
    config.fn_resolve_email_template('_PGTAP_TEST_INATTIVO'),
    NULL::jsonb,
    'fn_resolve: template inattivo → NULL'
);

-- ============================================================
-- 11) Codice inesistente → NULL
-- ============================================================
SELECT is(
    config.fn_resolve_email_template('CODICE_CHE_NON_ESISTE_MAI'),
    NULL::jsonb,
    'fn_resolve: codice inesistente → NULL'
);

-- ============================================================
-- 12) Codice in minuscolo → trovato (20261104-38)
-- ============================================================
SELECT is(
    (config.fn_resolve_email_template(' _pgtap_test_tpl '))->>'oggetto',
    'Oggetto sistema it',
    'fn_resolve: il codice in minuscolo e con spazi trova lo stesso template'
);

SELECT * FROM finish();
ROLLBACK;
