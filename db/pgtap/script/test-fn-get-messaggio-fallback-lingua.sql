-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_messaggio - fallback lingua IT
-- Riferimento: migration 20260423-02-01.
--
-- Contesto: dopo il fix, se la lingua richiesta (via parametro o GUC
-- myapp.user_language) non ha riga per un codice errore, la fn ricade
-- su lingua='it' (codice ISO default progetto). Se nemmeno 'it' ha
-- riga -> placeholder legacy "[MESSAGGIO NON DEFINITO: <codice>]".
-- Implementazione single-query con IN + ORDER BY.
--
-- Indice test (1..6):
--    1. Match diretto EN -> ritorna template EN
--    2. Match diretto IT -> ritorna template IT
--    3. Codice senza EN + p_lingua='en' -> fallback IT (non placeholder)
--    4. Codice inesistente + p_lingua='en' -> placeholder
--    5. GUC myapp.user_language='en' + p_lingua=NULL su codice senza EN
--       -> fallback IT (GUC risolto correttamente)
--    6. p_valore + format() funzionante anche su fallback IT
--
-- Fixture: 3 codici TEST_FB_* inseriti nella tabella messaggi_errore.
-- Pulizia: BEGIN + ROLLBACK isolamento completo.
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

SELECT plan(6);
-- ⚠️ Dal 2026-08-07 `messaggi_errore.codice` ha una FK verso
--   `config.codici_errore`: la FRASE non puo' esistere senza il CODICE. I
--   codici di fixture vanno creati PRIMA, con la loro classe — `classe` e'
--   NOT NULL e senza default, di proposito.
--   Piano: docs/it/dev/work-done/piano-db-classe-codici-errore.md (D-7/D-8)
INSERT INTO config.codici_errore (codice, classe) VALUES
    ('TEST_FB_BOTH', 'DATO_ERRATO'),
    ('TEST_FB_ONLYIT', 'DATO_ERRATO');


-- =========================================================
-- Setup fixture
-- Uso id fissi in range seed dedicato (9xxx) per evitare collisioni
-- con la sequenza autoincrement di messaggi_errore (disallineata
-- rispetto al MAX(id) seminato). Il ROLLBACK finale ripulisce.
-- =========================================================
-- TEST_FB_BOTH: presente in IT e EN
INSERT INTO config.messaggi_errore (id, codice, lingua, messaggio, causa, soluzione)
VALUES
    (9901, 'TEST_FB_BOTH',   'it', 'Messaggio IT per %s', 'Causa IT', 'Soluzione IT'),
    (9902, 'TEST_FB_BOTH',   'en', 'Message EN for %s',   'Cause EN', 'Solution EN'),
    (9903, 'TEST_FB_ONLYIT', 'it', 'Solo IT',             NULL,       NULL);
-- Nessuna riga EN per TEST_FB_ONLYIT -> forza fallback.

-- =========================================================
-- 1) Match diretto EN -> template EN
-- =========================================================
SELECT is(
    script.fn_get_messaggio('TEST_FB_BOTH', NULL, 'en'),
    'Message EN for %s',
    '1. Codice con EN + lingua=en -> ritorna template EN'
);

-- =========================================================
-- 2) Match diretto IT -> template IT
-- =========================================================
SELECT is(
    script.fn_get_messaggio('TEST_FB_BOTH', NULL, 'it'),
    'Messaggio IT per %s',
    '2. Codice con IT + lingua=it -> ritorna template IT'
);

-- =========================================================
-- 3) Codice senza EN -> fallback IT
-- =========================================================
SELECT is(
    script.fn_get_messaggio('TEST_FB_ONLYIT', NULL, 'en'),
    'Solo IT',
    '3. Codice senza EN + lingua=en -> fallback IT (no placeholder)'
);

-- =========================================================
-- 4) Codice inesistente -> placeholder
-- =========================================================
SELECT is(
    script.fn_get_messaggio('TEST_FB_INESISTENTE', NULL, 'en'),
    '[MESSAGGIO NON DEFINITO: TEST_FB_INESISTENTE]',
    '4. Codice inesistente -> placeholder legacy (nessuna regressione)'
);

-- =========================================================
-- 5) GUC myapp.user_language='en' + p_lingua=NULL -> fallback IT
-- =========================================================
SET LOCAL myapp.user_language = 'en';

SELECT is(
    script.fn_get_messaggio('TEST_FB_ONLYIT', NULL, NULL),
    'Solo IT',
    '5. GUC user_language=en su codice senza EN -> fallback IT'
);

-- Reset GUC per test 6 (uso SET LOCAL='' per "unset").
SET LOCAL myapp.user_language = '';

-- =========================================================
-- 6) p_valore + format() su fallback IT
-- TEST_FB_ONLYIT ha solo IT con messaggio 'Solo IT' (no placeholder
-- dentro, %s non presente). Uso TEST_FB_BOTH con lingua='de' (non
-- esiste) -> ricade su IT -> format sostituisce %s con 'pippo'.
-- =========================================================
SELECT is(
    script.fn_get_messaggio('TEST_FB_BOTH', 'pippo', 'de'),
    'Messaggio IT per pippo',
    '6. format() funziona anche su fallback IT (lingua=de assente)'
);

SELECT * FROM finish();
ROLLBACK;
