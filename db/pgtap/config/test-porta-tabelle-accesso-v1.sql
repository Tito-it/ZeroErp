-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: le tabelle che danno l'accesso si scrivono solo dai verbi del SUPER_ADMIN.
-- Riferimento: brief-db-porte-aperte-dalla-sola-guc §14 (giro 10-bis; D-AC a,
--   D-AD b, D-AE a, D-AF a di Tid, 2026-11-26); changeSet 20_code/config/20261126-01
--   … -07 (legami e profili), 20_code/anagrafiche/20261126-08 … -12 (operatore,
--   primo amministratore, provisioning), 20_code/script/20261126-13, -14 (utente
--   tecnico), 20_code/dbops/20261126-15 … -23 (fixture e builder), 90_end/20261126-24
--   (le tabelle in sola lettura), -25 (le primitive riservate); 90_end/20261127-06
--   ritira l'involucro anagrafiche.fn_crea_operatore_v2, che era la settima.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - lo scope, i legami e il contenuto dei profili sono in sola lettura per
--     l'app: un INSERT diretto di un legame verso il profilo SUPER_ADMIN, che
--     farebbe un SUPER_ADMIN, si ferma sul privilegio (42501);
--   - i verbi che le scrivono sono SECURITY DEFINER col search_path fissato e
--     chiedono il SUPER_ADMIN in prima riga: un operatore, o nessun utente, riceve
--     E_PERMESSO_NEGATO, e niente si scrive;
--   - le primitive (e i passi interni della creazione dell'operatore) non le
--     esegue ne' l'app ne' PUBLIC: il permesso dei verbi non si aggira;
--   - le fixture dei pgTAP sono le sole DEFINER senza permesso aperte all'app, e
--     partono solo dove sono ammessi i dati di sviluppo;
--   - da un SUPER_ADMIN (i builder, che chiamano i verbi veri) il profilo e il
--     legame nascono, e il contesto di prima torna.
--
-- ⚠️ Il caso «PRODUZIONE» della fixture non si costruisce: l'ambiente sta in
--   dbops.installazione, in sola lettura per l'app. Si prova la regola pura
--   (dbops.fn_dati_di_sviluppo_ammessi_su_valori) e che le fixture la chiedano
--   prima della primitiva.
-- ⚠️ Nessun caso «due emittenti»: le tabelle non hanno RLS, e chi passa il guard
--   e' il SUPER_ADMIN, che vede tutte le aziende.
-- Gira come l'applicazione (runner di default). Da proprietario i privilegi non si
--   vedono: 5, 6 e 7 sono rossi per costruzione, e il 12 anche, perche' la sessione
--   del proprietario e' quella del migratore, che il verbo dell'utente tecnico
--   lascia passare.
--
-- Elenco test (plan 18):
--   forma
--    1) i sette verbi: SECURITY DEFINER, search_path fissato
--    2) le fixture: SECURITY DEFINER, eseguibili dall'app
--    3) l'app non esegue le sei funzioni riservate, e PUBLIC nemmeno
--   la sola lettura
--    4) sulle cinque tabelle l'app ha SELECT e nessuna scrittura
--    5) un INSERT diretto di un legame verso il profilo SUPER_ADMIN: 42501
--    6) un UPDATE diretto del contenuto di un profilo: 42501
--    7) un DELETE diretto della riga di scope: 42501
--   il permesso dei verbi
--    8) un operatore lega un profilo: E_PERMESSO_NEGATO
--    9) … e il legame non c'e'
--   10) un operatore scrive un profilo: E_PERMESSO_NEGATO
--   11) un operatore crea un operatore: E_PERMESSO_NEGATO
--   12) un operatore crea un utente tecnico: E_PERMESSO_NEGATO
--   13) un operatore lega un reparto: E_PERMESSO_NEGATO
--   14) senza utente in sessione il legame rifiuta (fail-closed)
--   le fixture
--   15) la regola del cancello: PRODUZIONE no, SVILUPPO si'
--   16) le due fixture chiedono il cancello prima della primitiva
--   dal SUPER_ADMIN
--   17) dal builder il profilo nasce e si lega all'identita'
--   18) dopo il builder il contesto e' di nuovo l'operatore
-- ------------------------------------------------------------

BEGIN;

-- Un'azienda col suo operatore (non SUPER_ADMIN) e una persona da legare.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

CREATE TEMP TABLE _p ON COMMIT DROP AS
SELECT o.identita_id, o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('porta-tabelle-accesso', false) o;

-- Una seconda persona, solo per il controesempio 5: da proprietario l'INSERT riesce,
-- e non deve sporcare i casi che leggono i legami della prima.
CREATE TEMP TABLE _p5 ON COMMIT DROP AS
SELECT o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('porta-tabelle-accesso-5', false) o;

-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- 1-3 La forma
-- ============================================================
SELECT is(
  (SELECT COALESCE(array_agg(p.oid::regproc::text ORDER BY 1), ARRAY[]::text[])
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('config.fn_lega_profilo_identita'::regproc, 'config.fn_slega_profilo_identita'::regproc,
                    'config.fn_lega_profilo_reparto'::regproc, 'config.fn_slega_profilo_reparto'::regproc,
                    'config.fn_scrivi_profilo_accesso'::regproc, 'anagrafiche.fn_crea_operatore'::regproc,
                    'script.fn_crea_utente_tecnico'::regproc)
      AND NOT (p.prosecdef
               AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search\_path=%'))),
  ARRAY[]::text[],
  '1) i sette verbi: SECURITY DEFINER, search_path fissato');

SELECT is(
  (SELECT bool_and(p.prosecdef AND has_function_privilege('zeroerp_app', p.oid, 'EXECUTE'))
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('dbops.fn_pgtap_fixture_crea_operatore'::regproc,
                    'dbops.fn_pgtap_fixture_crea_utente_tecnico'::regproc)),
  true,
  '2) le due fixture: SECURITY DEFINER, eseguibili dall''app');

SELECT is(
  (SELECT COALESCE(array_agg(p.oid::regproc::text ORDER BY 1), ARRAY[]::text[])
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('config.fn_applica_lega_profilo_identita'::regproc,
                    'config.fn_applica_scrivi_profilo_accesso'::regproc,
                    'anagrafiche.fn_applica_crea_operatore'::regproc,
                    'script.fn_applica_crea_utente_tecnico'::regproc,
                    'anagrafiche.fn_crea_risorsa_umana'::regproc,
                    'anagrafiche.fn_crea_auth_user'::regproc)
      AND (has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')
           OR has_function_privilege('public', p.oid, 'EXECUTE'))),
  ARRAY[]::text[],
  '3) l''app non esegue le sei funzioni riservate, e PUBLIC nemmeno');

-- ============================================================
-- 4-7 La sola lettura
-- ============================================================
SELECT is(
  (SELECT COALESCE(array_agg(t ORDER BY t), ARRAY[]::text[])
     FROM unnest(ARRAY['config.user_emittenti_fiscali', 'config.profili_accesso_bindings',
                       'config.profili_accesso', 'config.profili_accesso_aree',
                       'config.profili_accesso_azioni']) AS t
    WHERE NOT has_table_privilege('zeroerp_app', t, 'SELECT')
       OR has_table_privilege('zeroerp_app', t, 'INSERT')
       OR has_table_privilege('zeroerp_app', t, 'UPDATE')
       OR has_table_privilege('zeroerp_app', t, 'DELETE')),
  ARRAY[]::text[],
  '4) sulle cinque tabelle l''app ha SELECT e nessuna scrittura');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, identita_digitale_id)
       VALUES (config.fn_profilo_super_admin_id(), %s)$q$, (SELECT identita_id FROM _p5))),
  '42501',
  '5) ⭐ un INSERT diretto di un legame verso il profilo SUPER_ADMIN: 42501, nessun SUPER_ADMIN nasce');

SELECT is(
  dbops.fn_pgtap_codice_errore($q$UPDATE config.profili_accesso_aree SET livello = livello WHERE false$q$),
  '42501',
  '6) un UPDATE diretto del contenuto di un profilo: 42501');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = %s$q$, (SELECT auth_user_id FROM _e))),
  '42501',
  '7) un DELETE diretto della riga di scope: 42501');

-- ============================================================
-- 8-14 Il permesso dei verbi
-- ============================================================
-- Il profilo da legare nasce dal builder, cioe' dal verbo chiamato da un SUPER_ADMIN.
CREATE TEMP TABLE _prof ON COMMIT DROP AS
SELECT dbops.fn_pgtap_scrivi_profilo_accesso(
           'AD_HOC', '_PGTAP_PORTA_ACC_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
           'pgTAP: la porta delle tabelle dell''accesso') AS profilo_id;

SELECT is(
  dbops.fn_pgtap_codice_errore(format('SELECT config.fn_lega_profilo_identita(%s, %s)',
                                      (SELECT profilo_id FROM _prof), (SELECT identita_id FROM _p))),
  'E_PERMESSO_NEGATO',
  '8) un operatore lega un profilo: E_PERMESSO_NEGATO');

SELECT is(
  (SELECT count(*)::int FROM config.profili_accesso_bindings pab
    WHERE pab.identita_digitale_id = (SELECT identita_id FROM _p)),
  0,
  '9) … e il legame non c''e''');

SELECT is(
  dbops.fn_pgtap_codice_errore($q$SELECT config.fn_scrivi_profilo_accesso('AD_HOC', '_PGTAP_PORTA_ACC_X', 'x')$q$),
  'E_PERMESSO_NEGATO',
  '10) un operatore scrive un profilo: E_PERMESSO_NEGATO');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$SELECT * FROM anagrafiche.fn_crea_operatore(
           p_cognome := 'Porta', p_nome := 'pgTAP', p_codice_fiscale := %L, p_sesso := 'M',
           p_username := %L, p_email := %L, p_password_hash := 'pgtap-nessun-login',
           p_qualifica_id := (SELECT q.id FROM config.qualifiche q WHERE q.codice_interno = 'DIPENDENTE'))$q$,
    dbops.fn_pgtap_cf_libero(), '_pgtap_porta_acc_op', '_pgtap_porta_acc_op@example.com')),
  'E_PERMESSO_NEGATO',
  '11) un operatore crea un operatore: E_PERMESSO_NEGATO');

SELECT is(
  dbops.fn_pgtap_codice_errore(format($q$SELECT script.fn_crea_utente_tecnico('chiusura_scadenze_daily', %L)$q$,
                                      (SELECT emittente_codice FROM _e))),
  'E_PERMESSO_NEGATO',
  '12) un operatore crea un utente tecnico: E_PERMESSO_NEGATO');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('SELECT config.fn_lega_profilo_reparto(%s, %s)',
                                      (SELECT profilo_id FROM _prof),
                                      (SELECT uo.id FROM config.unita_organizzative uo WHERE uo.attivo ORDER BY uo.id LIMIT 1))),
  'E_PERMESSO_NEGATO',
  '13) un operatore lega un reparto: E_PERMESSO_NEGATO');

DO $vuoto$ BEGIN PERFORM set_config('app.current_user_id', '', false); END $vuoto$;

SELECT is(
  dbops.fn_pgtap_codice_errore(format('SELECT config.fn_lega_profilo_identita(%s, %s)',
                                      (SELECT profilo_id FROM _prof), (SELECT identita_id FROM _p))),
  'E_PERMESSO_NEGATO',
  '14) senza utente in sessione il legame rifiuta (fail-closed)');

DO $ctx2$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx2$;

-- ============================================================
-- 15-16 Le fixture
-- ============================================================
SELECT is(
  dbops.fn_dati_di_sviluppo_ammessi_su_valori('PRODUZIONE')::text || '|'
    || dbops.fn_dati_di_sviluppo_ammessi_su_valori('SVILUPPO')::text,
  'false|true',
  '15) la regola del cancello: PRODUZIONE no, SVILUPPO si''');

SELECT is(
  (SELECT COALESCE(array_agg(p.oid::regproc::text ORDER BY 1), ARRAY[]::text[])
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('dbops.fn_pgtap_fixture_crea_operatore'::regproc,
                    'dbops.fn_pgtap_fixture_crea_utente_tecnico'::regproc)
      -- le chiamate, con la parentesi: i commenti del corpo nominano le stesse funzioni
      AND NOT (position('dbops.fn_dati_di_sviluppo_ammessi_su_valori(' IN p.prosrc) > 0
               AND position('dbops.fn_dati_di_sviluppo_ammessi_su_valori(' IN p.prosrc)
                   < greatest(position('fn_applica_crea_operatore(' IN p.prosrc),
                              position('fn_applica_crea_utente_tecnico(' IN p.prosrc)))),
  ARRAY[]::text[],
  '16) le due fixture chiedono il cancello prima della primitiva');

-- ============================================================
-- 17-18 Dal SUPER_ADMIN
-- ============================================================
-- ⚠️ La scrittura in un'istruzione e la rilettura nelle successive.
CREATE TEMP TABLE _legame ON COMMIT DROP AS
SELECT dbops.fn_pgtap_lega_profilo_identita((SELECT profilo_id FROM _prof), (SELECT identita_id FROM _p)) AS binding_id;

SELECT is(
  (SELECT pab.profilo_accesso_id FROM config.profili_accesso_bindings pab
    WHERE pab.id = (SELECT binding_id FROM _legame)
      AND pab.identita_digitale_id = (SELECT identita_id FROM _p)),
  (SELECT profilo_id FROM _prof),
  '17) dal builder il profilo nasce e si lega all''identita''');

SELECT is(script.fn_utente_di_sessione(), (SELECT auth_user_id FROM _e),
  '18) dopo il builder il contesto e'' di nuovo l''operatore');

SELECT * FROM finish();
ROLLBACK;
