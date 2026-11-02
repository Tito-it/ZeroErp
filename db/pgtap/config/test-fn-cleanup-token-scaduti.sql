-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.fn_cleanup_token_scaduti
--       Pulizia periodica token monouso scaduti/utilizzati.
--
-- Elenco test:
--  1) Token valido e non utilizzato → NON eliminato
--  2) Token scaduto da 31 giorni → eliminato (retention default 30)
--  3) Token scaduto da 10 giorni, retention 30 → NON eliminato
--  4) Token utilizzato da 31 giorni → eliminato
--  5) Token utilizzato da 10 giorni, retention 30 → NON eliminato
--  6) Ritorna conteggio corretto dei record eliminati
--  7) Retention NULL → usa default 30
--  8) Retention negativo → usa default 30
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

SELECT plan(8);

-- ============================================================
-- 0. Setup: recupero un auth_user_id valido e creo token di test
-- ============================================================

-- 🔴 PULIZIA D'INGRESSO, aggiunta il 2026-08-18.
--   `fn_cleanup_token_scaduti` cancella su TUTTA la tabella e ritorna il totale
--   cancellato: e' una funzione di manutenzione, non sa cosa sia una fixture.
--   Il test 6 asseriva `= 2` contando sul fatto che in tabella ci fossero solo
--   i suoi due token — e da quando in sviluppo ce ne sono altri 13 scaduti
--   usciva `have: 15, want: 2`.
--
--   ⚠️ Non si aggiusta il numero: sarebbe una fotografia dei dati di sviluppo,
--   e domani ne basta uno in piu'. Si rende deterministico l'universo su cui la
--   funzione lavora.
--
--   ⭐ Sicuro perche' questo file e' TRANSAZIONALE: si chiude in ROLLBACK e i
--   token veri tornano tutti. La stessa riga in un test non transazionale
--   sarebbe un disastro.
DELETE FROM config.token_monouso;

-- Dalla madre identita_digitali (12-09-2026: la vista risorse_umane_auth_user
-- e' stata ritirata; il filtro OPERATORE e' quello che la vista applicava).
CREATE TEMP TABLE tmp_token_ctx AS
SELECT i.auth_user_id AS user_id
FROM anagrafiche.identita_digitali i
WHERE i.ruolo_applicativo = 'OPERATORE'
ORDER BY i.id
LIMIT 1;

-- Token 1: valido, non scaduto, non utilizzato (NON deve essere eliminato)
INSERT INTO config.token_monouso
    (token_hash, tipo, auth_user_id, scadenza, utilizzato)
VALUES
    ('hash_valido_test_001', 'TEST_PGTAP',
     (SELECT user_id FROM tmp_token_ctx),
     now() + interval '24 hours', false);

-- Token 2: scaduto da 31 giorni (DEVE essere eliminato con retention 30)
INSERT INTO config.token_monouso
    (token_hash, tipo, auth_user_id, scadenza, utilizzato, data_insert)
VALUES
    ('hash_scaduto_31g_test_002', 'TEST_PGTAP',
     (SELECT user_id FROM tmp_token_ctx),
     now() - interval '31 days', false,
     now() - interval '32 days');

-- Token 3: scaduto da 10 giorni (NON deve essere eliminato con retention 30)
INSERT INTO config.token_monouso
    (token_hash, tipo, auth_user_id, scadenza, utilizzato, data_insert)
VALUES
    ('hash_scaduto_10g_test_003', 'TEST_PGTAP',
     (SELECT user_id FROM tmp_token_ctx),
     now() - interval '10 days', false,
     now() - interval '11 days');

-- Token 4: utilizzato da 31 giorni (DEVE essere eliminato)
INSERT INTO config.token_monouso
    (token_hash, tipo, auth_user_id, scadenza, utilizzato, utilizzato_at, data_insert)
VALUES
    ('hash_usato_31g_test_004', 'TEST_PGTAP',
     (SELECT user_id FROM tmp_token_ctx),
     now() - interval '32 days', true,
     now() - interval '31 days',
     now() - interval '33 days');

-- Token 5: utilizzato da 10 giorni (NON deve essere eliminato con retention 30)
INSERT INTO config.token_monouso
    (token_hash, tipo, auth_user_id, scadenza, utilizzato, utilizzato_at, data_insert)
VALUES
    ('hash_usato_10g_test_005', 'TEST_PGTAP',
     (SELECT user_id FROM tmp_token_ctx),
     now() - interval '11 days', true,
     now() - interval '10 days',
     now() - interval '12 days');

-- ============================================================
-- 1) Token valido → NON eliminato
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM config.token_monouso WHERE token_hash = 'hash_valido_test_001'),
    'Setup: token valido presente prima del cleanup'
);

-- ============================================================
-- 6) Esecuzione cleanup con retention 30 → ritorna 2 (token 2 e 4)
-- ============================================================
SELECT is(
    config.fn_cleanup_token_scaduti(30),
    2,
    'fn_cleanup_token_scaduti(30) → elimina 2 token (scaduto 31g + usato 31g)'
);

-- ============================================================
-- 2) Token scaduto da 31 giorni → eliminato
-- ============================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM config.token_monouso WHERE token_hash = 'hash_scaduto_31g_test_002'),
    'Token scaduto da 31 giorni eliminato'
);

-- ============================================================
-- 3) Token scaduto da 10 giorni → NON eliminato
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM config.token_monouso WHERE token_hash = 'hash_scaduto_10g_test_003'),
    'Token scaduto da 10 giorni NON eliminato (retention 30)'
);

-- ============================================================
-- 4) Token utilizzato da 31 giorni → eliminato
-- ============================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM config.token_monouso WHERE token_hash = 'hash_usato_31g_test_004'),
    'Token utilizzato da 31 giorni eliminato'
);

-- ============================================================
-- 5) Token utilizzato da 10 giorni → NON eliminato
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM config.token_monouso WHERE token_hash = 'hash_usato_10g_test_005'),
    'Token utilizzato da 10 giorni NON eliminato (retention 30)'
);

-- ============================================================
-- 7) Retention NULL → usa default 30 (non deve crashare)
-- ============================================================
SELECT is(
    config.fn_cleanup_token_scaduti(NULL),
    0,
    'fn_cleanup_token_scaduti(NULL) → 0 (nessun altro da eliminare, usa default 30)'
);

-- ============================================================
-- 8) Retention negativo → usa default 30
-- ============================================================
SELECT is(
    config.fn_cleanup_token_scaduti(-5),
    0,
    'fn_cleanup_token_scaduti(-5) → 0 (usa default 30, nessun altro da eliminare)'
);

SELECT * FROM finish();
ROLLBACK;
