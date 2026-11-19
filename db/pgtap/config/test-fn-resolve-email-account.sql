-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--  7) Account SISTEMA inattivo → ritorna NULL (SISTEMA si spegne anche se ha
--     spedito: lo storico delle mail non tiene acceso l'account, §16.14)
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

-- Contesto applicativo: il file gira come l'applicazione (runner di default) e
-- scrive come scrive l'amministratore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- ============================================================
-- 0. Setup
-- ============================================================

-- Una UO attiva SENZA account: il livello 1 del risolutore e' l'account
-- REPARTO_TEST che il file crea, non un account che c'era gia'.
CREATE TEMP TABLE tmp_email_ctx AS
SELECT uo.id AS uo_id
FROM config.unita_organizzative uo
WHERE uo.attivo = true
  AND NOT EXISTS (SELECT 1 FROM config.email_account ea
                   WHERE ea.unita_organizzativa_id = uo.id)
ORDER BY uo.id
LIMIT 1;

-- L'account SISTEMA e' quello del seed, acceso e col suo codice. Si aggiorna,
-- non si ricrea.
-- ⛔ 2026-11-19 — FINO A QUI il file cancellava SISTEMA e lo ricreava da OWNER,
--   dopo averne staccato i figli (email_log, email_outbox): il SISTEMA del seed
--   aveva spedito, e dbops.trgfn_prevent_deactivate_if_children ne impediva la
--   disattivazione che serve al test 7. Dal giro 1 del seed di primo impianto
--   quella strada era chiusa due volte (la DELETE di una riga di seed e'
--   E_SEED_RIGA_NON_CANCELLABILE, e l'UPDATE del migratore su una tabella in
--   solo inserimento si scarta), e dal 20261117-28 account e template non si
--   cancellano piu' (dbops.automation_delete_block). Lo stesso giro toglie il
--   blocco della disattivazione verso lo storico delle mail
--   (dbops.automazione_attivo_eccezioni): un account che ha spedito si spegne.
--   ⇒ Il test 7 lo prova sull'account vero, coi suoi figli, come app.
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive §16.14.
UPDATE config.email_account
   SET codice = 'SISTEMA', attivo = true
 WHERE codice_interno = 'SISTEMA';

-- Un database senza il seed: SISTEMA lo crea l'installazione.
INSERT INTO config.email_account
    (codice, codice_interno, descrizione, unita_organizzativa_id,
     smtp_host, smtp_port, smtp_use_tls, smtp_use_ssl,
     smtp_username, smtp_password_encrypted,
     email_from, attivo)
SELECT 'SISTEMA', 'SISTEMA', 'Account di sistema test', NULL,
       'smtp.test.local', 587, true, false,
       'test@test.local', 'encrypted_pwd_test',
       'noreply@test.local', true
 WHERE NOT EXISTS (SELECT 1 FROM config.email_account WHERE codice_interno = 'SISTEMA');

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
