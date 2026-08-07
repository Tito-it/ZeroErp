-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.fn_resolve_email_account
--       Risoluzione account SMTP con fallback reparto -> SISTEMA.
--
-- Elenco test:
--  1) Account SISTEMA esiste come fallback
--  2) Chiamata senza parametri → ritorna account SISTEMA
--  3) Chiamata con NULL → ritorna account SISTEMA
--  4) Reparto con account dedicato → ritorna account del reparto
--  5) Reparto senza account → fallback a SISTEMA
--  6) Reparto con account inattivo → fallback a SISTEMA
--  7) Account SISTEMA inattivo → ritorna NULL
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

SELECT plan(7);

-- ============================================================
-- 0. Setup: crea account di test
-- ============================================================

-- Prendo una UO esistente per i test
CREATE TEMP TABLE tmp_email_ctx AS
SELECT uo.id AS uo_id
FROM config.unita_organizzative uo
WHERE uo.attivo = true
ORDER BY uo.id
LIMIT 1;

-- Ambiente self-contained. Il seed fornisce un account SISTEMA, ma:
--   - codice_interno e' UNIQUE (20260629-05) -> non si puo' inserire un 2o SISTEMA;
--   - il SISTEMA seed ha figli attivi (email_log/email_outbox) e il guard
--     dbops.trgfn_prevent_deactivate_if_children ne impedisce la disattivazione
--     (serve al test 7).
-- Percio' rimuovo il SISTEMA seed + i suoi figli e ricreo un SISTEMA pulito
-- (senza figli, disattivabile). Tutto in transazione: ROLLBACK ripristina.
DELETE FROM config.email_log
 WHERE email_account_id IN (SELECT id FROM config.email_account WHERE codice_interno = 'SISTEMA');
DELETE FROM config.email_outbox
 WHERE email_account_id IN (SELECT id FROM config.email_account WHERE codice_interno = 'SISTEMA');
DELETE FROM config.email_account
 WHERE codice_interno IN ('SISTEMA', 'REPARTO_TEST');

-- Account SISTEMA (fallback). codice_interno = chiave immutabile risolta dalla fn.
INSERT INTO config.email_account
    (codice, codice_interno, descrizione, unita_organizzativa_id,
     smtp_host, smtp_port, smtp_use_tls, smtp_use_ssl,
     smtp_username, smtp_password_encrypted,
     email_from, attivo)
VALUES
    ('SISTEMA', 'SISTEMA', 'Account di sistema test', NULL,
     'smtp.test.local', 587, true, false,
     'test@test.local', 'encrypted_pwd_test',
     'noreply@test.local', true);

-- Account per il reparto
INSERT INTO config.email_account
    (codice, codice_interno, descrizione, unita_organizzativa_id,
     smtp_host, smtp_port, smtp_use_tls, smtp_use_ssl,
     smtp_username, smtp_password_encrypted,
     email_from, attivo)
VALUES
    ('REPARTO_TEST', 'REPARTO_TEST', 'Account reparto test',
     (SELECT uo_id FROM tmp_email_ctx),
     'smtp.reparto.local', 587, true, false,
     'reparto@test.local', 'encrypted_pwd_reparto',
     'reparto@test.local', true);

-- ============================================================
-- 1) Account SISTEMA esiste
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM config.email_account
     WHERE codice = 'SISTEMA' AND attivo = true) > 0,
    'Account SISTEMA attivo esiste'
);

-- ============================================================
-- 2) Chiamata senza parametri → account SISTEMA
-- ============================================================
SELECT is(
    (config.fn_resolve_email_account())->>'codice',
    'SISTEMA',
    'fn_resolve_email_account() senza parametri → SISTEMA'
);

-- ============================================================
-- 3) Chiamata con NULL → account SISTEMA
-- ============================================================
SELECT is(
    (config.fn_resolve_email_account(NULL))->>'codice',
    'SISTEMA',
    'fn_resolve_email_account(NULL) → SISTEMA'
);

-- ============================================================
-- 4) Reparto con account dedicato → account del reparto
-- ============================================================
SELECT is(
    (config.fn_resolve_email_account(
        (SELECT uo_id FROM tmp_email_ctx)
    ))->>'codice',
    'REPARTO_TEST',
    'fn_resolve_email_account(uo_id) → account reparto'
);

-- ============================================================
-- 5) Reparto senza account → fallback a SISTEMA
-- ============================================================
SELECT is(
    (config.fn_resolve_email_account(999999))->>'codice',
    'SISTEMA',
    'fn_resolve_email_account(uo_inesistente) → fallback SISTEMA'
);

-- ============================================================
-- 6) Account reparto inattivo → fallback a SISTEMA
-- ============================================================
UPDATE config.email_account
   SET attivo = false
 WHERE codice = 'REPARTO_TEST';

SELECT is(
    (config.fn_resolve_email_account(
        (SELECT uo_id FROM tmp_email_ctx)
    ))->>'codice',
    'SISTEMA',
    'fn_resolve_email_account(uo_id) con account inattivo → fallback SISTEMA'
);

-- ============================================================
-- 7) Account SISTEMA inattivo → NULL
-- ============================================================
UPDATE config.email_account
   SET attivo = false
 WHERE codice = 'SISTEMA';

SELECT is(
    config.fn_resolve_email_account(
        (SELECT uo_id FROM tmp_email_ctx)
    ),
    NULL::jsonb,
    'fn_resolve_email_account() con SISTEMA inattivo → NULL'
);

SELECT * FROM finish();
ROLLBACK;
