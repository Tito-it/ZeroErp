-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture CANCELLA le righe seedate di
--   config.email_outbox / email_log per rendere l'account SISTEMA privo di
--   figli (serve al test 7). Dal 2026-09-05 `config.email_outbox` ha la RLS
--   attiva (changeSet 20260905-37) e le sue righe sono di ambito SISTEMA, che
--   la policy riserva al super admin: come applicazione quel DELETE non tocca
--   piu' niente. ⭐ Ed e' giusto cosi' — l'applicazione quelle righe non le
--   cancella. E' una scrittura da owner, e si dichiara invece di indebolire la
--   policy. Verificato leggendo la policy, non dedotto.
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

-- Contesto applicativo: la riga resta perche' il preambolo e' presidiato e
-- perche' la funzione sotto test legge come legge l'applicazione.
-- ⚠️ Ma dal 2026-09-05 il file gira come OWNER (marcatore in testa): la RLS su
-- config.email_outbox e' attiva e la fixture deve cancellare righe che
-- l'applicazione non cancella. ⛔ Quindi questo file NON esercita piu' la RLS,
-- e va detto: chi cerca il collaudo della policy sulle email lo trova in
-- db/pgtap/rls/test-rls-email-outbox-ambito.sql.
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
--
-- ⛔ 2026-09-05 — E QUI IL FILE E' MORTO PER UN GIORNO, in un modo che vale
--   ricordare. Acceso il changeSet `20260905-37` (RLS su config.email_outbox),
--   il DELETE qui sotto ha smesso di cancellare: le righe sono di ambito
--   SISTEMA, e la policy le riserva al super admin.
--   ⚠️ **Un DELETE che non cancella niente non solleva niente.** Il file non e'
--   caduto dove stava il problema: e' caduto due istruzioni piu' in la', sulla
--   FK di `email_account`, nominando una tabella che non c'entrava.
--   ⇒ Il rimedio non e' indebolire la policy ne' saltare la riga: e' dichiarare
--   che questa fixture e' una scrittura da OWNER (marcatore in testa).
--
-- ⛔ 2026-09-25 — I FIGLI SI STACCANO, NON SI CANCELLANO. Dal changeSet
--   `20260925-74` una mail spedita non si elimina (la regola «solo in bozza»,
--   E_DELETE_DOC_NON_BOZZA), e il DELETE qui sotto moriva su ogni database con
--   una mail di sistema gia' partita. Al test serve un account SENZA figli, non
--   figli cancellati: `email_account_id` e' nullable su entrambe le tabelle, e
--   staccarli non tocca la storia di nessuna mail.
UPDATE config.email_log
   SET email_account_id = NULL
 WHERE email_account_id IN (SELECT id FROM config.email_account WHERE codice_interno = 'SISTEMA');
UPDATE config.email_outbox
   SET email_account_id = NULL
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
