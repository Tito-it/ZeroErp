-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_check_operatore_invitabile — la REGOLA UNICA dell'invito:
--       si invita chi ha una veste OPERATORE SPENTA (l'invito la accende),
--       una veste gia' attiva si rifiuta.
--
-- ⭐ Riscritto il 2026-09-25 (brief-db-blocco-login-per-credenziale §12,
--   changeSet 20260925-43; R-1 del piano BE/FE, D-8 dell'analisi accessi).
--   Fino a quel giorno il check pretendeva il contrario — veste ATTIVA,
--   is_active = true, last_login NULL — e il test lo inchiodava. Col P-2 la
--   veste nasce spenta (20260925-42): con la regola vecchia un operatore
--   appena creato non sarebbe mai stato invitabile.
--   ⭐ E il test COSTRUISCE il suo operatore (dbops.fn_pgtap_crea_operatore_umano)
--   invece di pescarne uno fra quelli che ci sono: la versione di prima
--   prendeva «la prima identita' OPERATORE attiva non super admin» del
--   database, e su un database senza operatori (la CI) non trovava niente.
--
-- Elenco test (plan 13):
--   Chiamate che non arrivano a nessuna credenziale
--    1) auth_user_id NULL -> invitabile=false
--    2) auth_user_id <= 0 -> invitabile=false
--    3) auth_user_id inesistente -> UTENTE_NON_TROVATO
--   La regola
--    4) credenziale senza veste OPERATORE -> SENZA_VESTE_OPERATORE
--    5) ⛔ veste OPERATORE gia' ATTIVA -> invitabile=false (D-8)
--    6) ⭐ veste OPERATORE SPENTA -> invitabile=true, con l'email
--    7) ... e is_active e' false (derivato dalle vesti): non conta
--    8) ... e last_login valorizzato: non conta piu' (D-8)
--    9) veste spenta fuori dalla sua finestra -> invitabile=false
--   10) veste spenta, email vuota -> invitabile=false
--   Il cablaggio
--   11) la madre fn_crea_operatore_v2 lascia un operatore INVITABILE (la veste
--       nasce spenta): e' la ragione per cui la regola si e' rovesciata
--   Piu' vesti (rev 20260925-53, R-9)
--   12) due vesti OPERATORE spente sulla stessa credenziale -> invitabile=false:
--       l'invito ne riaccende UNA e non si sa quale (il verbo del backend lo
--       rifiuta gia'; la capability deve dire lo stesso)
--   Il contratto (rev 20260927-01, brief-db-blocco-login-per-credenziale §16)
--   13) ⛔ la frase `motivo` e' ritirata: la chiave non esiste piu', ne' nel
--       rifiuto ne' nell'invitabile
--
-- ⭐ Rev 20260927-01 (§16): il motivo e' un CODICE con la sua chiave i18n, e
--   i casi pinnano la coppia `reason|reason_key` — non piu' frasi o ILIKE su
--   frasi. Un test che pinnasse il testo tornerebbe a chiedere il testo.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione (ruolo OPERATORE +
-- RLS attiva). Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli
--   (il COMMIT non arriva mai). In testa e non in coda.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture: un operatore VERO (madre + invito accettato), non super admin —
-- spegnerne la veste non tocca l'anti-lockout.
-- ============================================================
CREATE TEMP TABLE tmp_inv AS
SELECT o.auth_user_id AS user_id, o.identita_id
  FROM dbops.fn_pgtap_crea_operatore_umano('invitabile', false) o;

-- Una credenziale NUDA: nessuna identita'.
CREATE TEMP TABLE tmp_nuda AS
SELECT anagrafiche.fn_crea_auth_user(
           p_username      := '_pgtap_inv_nuda_' || substring(md5(clock_timestamp()::text) from 1 for 8),
           p_email         := '_pgtap_inv_nuda_' || substring(md5(clock_timestamp()::text) from 1 for 8) || '@example.com',
           p_password_hash := '!') AS user_id;

-- ============================================================
-- 1-3) Chiamate che non arrivano a nessuna credenziale
-- ============================================================
SELECT is((SELECT r->>'invitabile' || '|' || (r->>'reason')
             FROM (SELECT script.fn_check_operatore_invitabile(NULL) AS r) x),
          'false|UTENTE_NON_TROVATO',
          '1) auth_user_id NULL -> invitabile=false, UTENTE_NON_TROVATO');

SELECT is((SELECT r->>'invitabile' || '|' || (r->>'reason')
             FROM (SELECT script.fn_check_operatore_invitabile(-1) AS r) x),
          'false|UTENTE_NON_TROVATO',
          '2) auth_user_id <= 0 -> invitabile=false, UTENTE_NON_TROVATO');

SELECT is((SELECT (r->>'reason') || '|' || (r->>'reason_key')
             FROM (SELECT script.fn_check_operatore_invitabile(2147483000) AS r) x),
          'UTENTE_NON_TROVATO|amministrazione.operatori.invito_reason.utente_non_trovato',
          '3) auth_user_id inesistente -> UTENTE_NON_TROVATO con la sua chiave');

-- ============================================================
-- 4) Credenziale senza nessuna veste OPERATORE
-- ============================================================
SELECT is((SELECT (r->>'reason') || '|' || (r->>'reason_key')
             FROM (SELECT script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_nuda)) AS r) x),
          'SENZA_VESTE_OPERATORE|amministrazione.operatori.invito_reason.senza_veste_operatore',
          '4) credenziale senza veste OPERATORE -> SENZA_VESTE_OPERATORE');

-- ============================================================
-- 5) ⛔ Veste gia' ATTIVA (il builder la accende): rifiuto (D-8)
-- ============================================================
SELECT is(
    (SELECT r->>'invitabile' || '|' || (r->>'reason') || '|' || (r->>'reason_key')
       FROM (SELECT script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_inv)) AS r) x),
    'false|VESTE_GIA_ATTIVA|amministrazione.operatori.invito_reason.veste_gia_attiva',
    '5) veste OPERATORE gia'' attiva -> invitabile=false, VESTE_GIA_ATTIVA (D-8)');

-- ============================================================
-- 6-8) ⭐ Veste SPENTA: invitabile — e is_active, last_login non contano
-- ============================================================
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE id = (SELECT identita_id FROM tmp_inv);

UPDATE django.auth_user
   SET last_login = now()
 WHERE id = (SELECT user_id FROM tmp_inv);

SELECT is(
    (SELECT r->>'invitabile' || '|' || (r->>'email')
            || '|' || ((r->>'reason') IS NULL AND (r->>'reason_key') IS NULL)::text
       FROM (SELECT script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_inv)) AS r) x),
    'true|' || (SELECT email FROM django.auth_user WHERE id = (SELECT user_id FROM tmp_inv)) || '|true',
    '6) veste OPERATORE spenta -> invitabile=true, con l''email, reason e reason_key NULL');

SELECT is(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT user_id FROM tmp_inv)),
    false,
    '7) ...con is_active = false (la sola veste e'' spenta): non decide');

SELECT isnt(
    (SELECT last_login FROM django.auth_user WHERE id = (SELECT user_id FROM tmp_inv)),
    NULL,
    '8) ...e con last_login valorizzato: non decide piu'' (D-8)');

-- ============================================================
-- 9) Veste spenta FUORI dalla sua finestra (comincia fra dieci giorni)
-- ============================================================
UPDATE anagrafiche.identita_digitali
   SET valido_dal = script.fn_data_operativa() + 10
 WHERE id = (SELECT identita_id FROM tmp_inv);

SELECT is(
    (SELECT r->>'invitabile' || '|' || (r->>'reason') || '|' || (r->>'reason_key')
       FROM (SELECT script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_inv)) AS r) x),
    'false|VESTE_FUORI_FINESTRA|amministrazione.operatori.invito_reason.veste_fuori_finestra',
    '9) veste spenta fuori finestra -> invitabile=false, VESTE_FUORI_FINESTRA');

UPDATE anagrafiche.identita_digitali
   SET valido_dal = script.fn_data_operativa()
 WHERE id = (SELECT identita_id FROM tmp_inv);

-- ============================================================
-- 10) Veste spenta, email vuota
-- ============================================================
UPDATE django.auth_user
   SET email = ''
 WHERE id = (SELECT user_id FROM tmp_inv);

SELECT is(
    (SELECT r->>'invitabile' || '|' || (r->>'reason') || '|' || (r->>'reason_key')
       FROM (SELECT script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_inv)) AS r) x),
    'false|SENZA_EMAIL|amministrazione.operatori.invito_reason.senza_email',
    '10) veste spenta ma email vuota -> invitabile=false, SENZA_EMAIL');

-- ============================================================
-- 11) Il cablaggio: la madre lascia un operatore INVITABILE
-- ============================================================
SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE tmp_madre AS
SELECT m.auth_user_id AS user_id
  FROM anagrafiche.fn_crea_operatore_v2(
           p_cognome                      := 'Invito',
           p_nome                         := 'pgTAP',
           p_codice_fiscale               := dbops.fn_pgtap_cf_libero(),
           p_username                     := '_pgtap_inv_madre_' || substring(md5(clock_timestamp()::text) from 1 for 8),
           p_email                        := '_pgtap_inv_madre_' || substring(md5(clock_timestamp()::text) from 1 for 8) || '@example.com',
           p_password_hash                := 'pgtap-nessun-login',
           p_qualifica_id                 := (SELECT q.id FROM config.qualifiche q WHERE q.codice_interno = 'DIPENDENTE'),
           p_indirizzo_resid_dettaglio_id := dbops.fn_pgtap_crea_indirizzo_dettaglio('invitabile madre'),
           p_sesso := 'M') m;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(
    (script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_madre)))->>'invitabile',
    'true',
    '11) la madre lascia la veste spenta: l''operatore appena creato e'' invitabile');

-- ============================================================
-- 12) Due vesti OPERATORE spente sulla stessa credenziale (rev 20260925-53)
--     La seconda e' una copia spenta della prima: il modello la ammette
--     (l'unique vale solo WHERE attivo). Email ripristinata, cosi' il
--     rifiuto non puo' venire dal caso 10.
-- ============================================================
UPDATE django.auth_user
   SET email = '_pgtap_inv_due_' || substring(md5(clock_timestamp()::text) from 1 for 8) || '@example.com'
 WHERE id = (SELECT user_id FROM tmp_inv);

INSERT INTO anagrafiche.identita_digitali
       (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo, valido_dal)
SELECT idg.soggetto_ruolo_id, idg.auth_user_id, idg.ruolo_applicativo, false, idg.valido_dal
  FROM anagrafiche.identita_digitali idg
 WHERE idg.id = (SELECT identita_id FROM tmp_inv);

SELECT is(
    (SELECT r->>'invitabile' || '|' || (r->>'reason') || '|' || (r->>'reason_key')
       FROM (SELECT script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_inv)) AS r) x),
    'false|PIU_VESTI_SPENTE|amministrazione.operatori.invito_reason.piu_vesti_spente',
    '12) due vesti OPERATORE spente -> invitabile=false, PIU_VESTI_SPENTE');

-- ============================================================
-- 13) ⛔ `motivo` ritirato (rev 20260927-01): la chiave non c'e' piu' ne' nel
--     rifiuto (tmp_inv, caso 12) ne' nell'invitabile (tmp_madre, caso 11).
--     Una sede sola per il motivo: una frase rimasta accanto al codice
--     sarebbe la seconda.
-- ============================================================
SELECT is(
    (SELECT bool_or(r ? 'motivo')
       FROM (SELECT script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_inv))   AS r
             UNION ALL
             SELECT script.fn_check_operatore_invitabile((SELECT user_id FROM tmp_madre)) AS r) x),
    false,
    '13) la chiave `motivo` non esiste piu'' (rifiuto e invitabile)');

SELECT * FROM finish();
ROLLBACK;
