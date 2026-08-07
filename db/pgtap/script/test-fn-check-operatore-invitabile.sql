-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_check_operatore_invitabile
--       Verifica le 7 condizioni di invitabilita' di un operatore.
--
-- Migrazione Fase 7 Chunk A (2026-04-29):
--   Pre-migrazione il test scriveva su anagrafiche.risorse_umane_auth_user
--   come tabella ponte legacy (con ruolo_sistema enum + attivo boolean).
--   Post-cutover §13.3 (19-04-2026) RAU e' diventata vista non-updatable
--   calcolata da identita_digitali + binding SUPER_ADMIN. Le UPDATE su
--   rau fallivano in CI dal cutover. Questa migrazione le sostituisce
--   con scritture dirette su identita_digitali (sorgente di verita'):
--     - rau.attivo=false  -> identita_digitali.attivo=false
--     - rau.ruolo_sistema='DISABILITATO'  -> id.ruolo_applicativo='DISABILITATO'
--     - rau.ruolo_sistema='OPERATIVO'     -> id.ruolo_applicativo='OPERATORE' + id.attivo=true
--
-- Filtro vergine "non-SA": il setup pesca un'identita OPERATORE attiva
-- SENZA binding SUPER_ADMIN, per evitare di scatenare il guard
-- anti-lockout ultimo SA (trgfn_identita_digitali_guard_ultimo_super_admin)
-- durante i test di disattivazione/disabilitazione (case 4, 5, 6).
--
-- Elenco test:
--  1) auth_user_id NULL → invitabile=false
--  2) auth_user_id <= 0 → invitabile=false
--  3) auth_user_id inesistente → invitabile=false, motivo 'Utente non trovato'
--  4) auth_user is_active=false → invitabile=false
--  5) identita.attivo=false → invitabile=false
--  6) auth_user senza email → invitabile=false
--  7) auth_user con last_login NOT NULL → invitabile=false
--  8) Operatore valido (tutte condizioni OK) → invitabile=true con email
--
-- Nota: il ramo `IF v_ruolo_applicativo = 'DISABILITATO'` nel body
-- della fn e' dead code post-cutover §13.3 — il LEFT JOIN su
-- identita_digitali filtra `ruolo_applicativo = 'OPERATORE'`, quindi
-- nessuna riga estratta puo' avere ruolo DISABILITATO. I percorsi
-- "operatore disabilitato" reali sono coperti dai casi 4 (is_active),
-- 5 (id.attivo) e dal caso "Nessuna identita OPERATORE" (riga
-- assente o ruolo_applicativo diverso da OPERATORE). Il vecchio
-- caso 6 che forzava ruolo_applicativo=DISABILITATO e' stato rimosso
-- in Fase 7 (la stringa attesa "%DISABILITATO%" non corrisponde piu'
-- al motivo restituito dalla fn).
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
-- 0. Setup: pesco una identita OPERATORE attiva "vergine" (senza
--    binding SUPER_ADMIN) per non scatenare guard ultimo-SA.
-- ============================================================

CREATE TEMP TABLE tmp_invito_ctx AS
SELECT
    id.auth_user_id           AS user_id,
    id.id                     AS identita_id,
    au.email                  AS original_email,
    au.is_active              AS original_active,
    au.last_login             AS original_last_login,
    id.ruolo_applicativo::text AS original_ruolo_app,
    id.attivo                 AS original_id_attivo
FROM anagrafiche.identita_digitali id
JOIN django.auth_user au ON au.id = id.auth_user_id
WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
  AND id.attivo = true
  AND NOT EXISTS (
      SELECT 1
        FROM config.profili_accesso_bindings pab
        JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
  )
ORDER BY id.id
LIMIT 1;

-- Preparo l'operatore come invitabile:
-- email presente, is_active=true, last_login=NULL,
-- identita OPERATORE attiva, ruolo_applicativo='OPERATORE'.
UPDATE django.auth_user
   SET email = 'test.invito@pgtap.local',
       is_active = true,
       last_login = NULL
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

UPDATE anagrafiche.identita_digitali
   SET ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo,
       attivo = true
 WHERE id = (SELECT identita_id FROM tmp_invito_ctx);

-- ============================================================
-- 1) auth_user_id NULL → invitabile=false
-- ============================================================
SELECT is(
    (script.fn_check_operatore_invitabile(NULL))->>'invitabile',
    'false',
    'fn_check_operatore_invitabile(NULL) → invitabile=false'
);

-- ============================================================
-- 2) auth_user_id <= 0 → invitabile=false
-- ============================================================
SELECT is(
    (script.fn_check_operatore_invitabile(-1))->>'invitabile',
    'false',
    'fn_check_operatore_invitabile(-1) → invitabile=false'
);

-- ============================================================
-- 3) auth_user_id inesistente → invitabile=false
-- ============================================================
SELECT is(
    (script.fn_check_operatore_invitabile(99999999))->>'motivo',
    'Utente non trovato',
    'fn_check_operatore_invitabile(99999999) → Utente non trovato'
);

-- ============================================================
-- 4) is_active=false → invitabile=false
--    Nota: il trigger sync_auth_user_active si comporta in modo
--    inverso (auth_user.is_active deriva da identita.attivo). Per
--    forzare auth_user.is_active=false senza ribaltarlo dal sync
--    e' sufficiente fare l'UPDATE diretto: il trigger sync e' su
--    identita_digitali, non su auth_user.
-- ============================================================
UPDATE django.auth_user
   SET is_active = false
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%is_active%',
    '4) is_active=false → invitabile=false con motivo is_active'
);

UPDATE django.auth_user
   SET is_active = true
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 5) identita.attivo=false → invitabile=false
--    Pre-Fase 7: UPDATE rau.attivo. Post-Fase 7: UPDATE
--    identita_digitali.attivo direttamente.
-- ============================================================
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE id = (SELECT identita_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%non attiva%',
    '5) identita.attivo=false → invitabile=false con motivo "non attiva"'
);

UPDATE anagrafiche.identita_digitali
   SET attivo = true
 WHERE id = (SELECT identita_id FROM tmp_invito_ctx);

-- ============================================================
-- 6) Senza email → invitabile=false
-- ============================================================
UPDATE django.auth_user
   SET email = ''
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%email%',
    '6) email vuota → invitabile=false'
);

UPDATE django.auth_user
   SET email = 'test.invito@pgtap.local'
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 7) last_login NOT NULL → invitabile=false
-- ============================================================
UPDATE django.auth_user
   SET last_login = now()
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%login%',
    '7) last_login NOT NULL → invitabile=false (gia'' loggato)'
);

UPDATE django.auth_user
   SET last_login = NULL
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 8) Tutte le condizioni OK → invitabile=true con email
-- ============================================================
SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'invitabile' = 'true'
    AND
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'email' = 'test.invito@pgtap.local',
    '8) Tutte condizioni OK → invitabile=true, email corretta'
);

SELECT * FROM finish();
ROLLBACK;
