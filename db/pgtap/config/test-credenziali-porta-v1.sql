-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la PORTA delle tabelle della credenziale e la struttura che resta.
--   Brief: brief-db-blocco-login-per-credenziale, sezioni 2.2 e 4.
--   ChangeSet: 90_end/20260925-24 (forward), 90_end/ci_apply/20260205-41
--   (v_tabelle_sola_lettura_app), scripts/sql/provision_zeroerp.sql (fase post) (POSTURA
--   DICHIARATA); 90_end/20260925-22 (FK con CASCADE), -25 (DROP colonne).
--   R-7 (sezione 13): 90_end/20260925-62 e le stesse due sedi per le gemelle del
--   nome tentato; 20260925-57/-58 (retention alla nascita), -59 (passo del freno).
--
-- ⭐ E' il presidio che tiene allineate le TRE sedi della postura (linee-guida
--   §11.8): verde su dev col solo forward, rosso su un database ricostruito se
--   una delle altre due manca. Postura letta con has_*_privilege(ruolo, …), mai
--   con information_schema.role_table_grants (cieco fuori dal ruolo), e
--   accanto il COMPORTAMENTO: come app, UPDATE … WHERE false -> 42501, su una
--   colonna che esiste (su una assente risponderebbe 42703, rosso per il motivo
--   sbagliato).
--
-- ⚠️ 3, 4 e 13 provano il 42501 COME APP: da owner (la prova dell'SQL estratto
--   prima dell'apply) sono rossi per costruzione, verdi solo nel runner.
--
-- Elenco test (plan 13):
--    1) config.credenziali: all'app SELECT si', INSERT/UPDATE/DELETE no
--    2) config.credenziali_provenienze: idem
--    3) come app, UPDATE di config.credenziali -> 42501
--    4) come app, DELETE di config.credenziali_provenienze -> 42501
--    5) le funzioni che scrivono sono DEFINER, i lettori e i guard INVOKER
--    6) l'app esegue tutte le funzioni della credenziale
--    7) il proprietario delle DEFINER e' il proprietario delle tabelle
--    8) le quattro colonne della credenziale non esistono piu' su identita_digitali
--    9) i due trigger della credenziale ci sono (anti-lockout, retention)
--   10) cancellare l'auth_user si porta via lo stato (CASCADE) — skip() dove la
--       FK non esiste (CI: Liquibase gira prima di manage.py migrate). Dal
--       2026-10-06 si cancella dal verbo script.fn_elimina_credenziale, da
--       SUPER_ADMIN: l'app non ha piu' il DELETE diretto
--   Le gemelle del nome tentato (R-7)
--   11) config.nomi_tentati: all'app SELECT si', INSERT/UPDATE/DELETE no
--   12) config.nomi_tentati_provenienze: idem
--   13) come app, INSERT in config.nomi_tentati -> 42501
--   (il 5 conta anche fn_login_freno_passo, il 9 anche i due trigger alla
--   nascita delle gemelle)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- 1-4 La porta
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', has_table_privilege('zeroerp_app', 'config.credenziali', 'SELECT')::text,
                   has_table_privilege('zeroerp_app', 'config.credenziali', 'INSERT, UPDATE, DELETE')::text)),
    'true|false',
    '1) config.credenziali: all''app SELECT si'', nessuna scrittura');

SELECT is(
    (SELECT format('%s|%s', has_table_privilege('zeroerp_app', 'config.credenziali_provenienze', 'SELECT')::text,
                   has_table_privilege('zeroerp_app', 'config.credenziali_provenienze', 'INSERT, UPDATE, DELETE')::text)),
    'true|false',
    '2) config.credenziali_provenienze: all''app SELECT si'', nessuna scrittura');

SELECT throws_ok(
    $$ UPDATE config.credenziali SET id = id WHERE false $$,
    '42501', NULL,
    '3) come app, UPDATE di config.credenziali: permesso negato');

SELECT throws_ok(
    $$ DELETE FROM config.credenziali_provenienze WHERE false $$,
    '42501', NULL,
    '4) come app, DELETE di config.credenziali_provenienze: permesso negato');

-- ============================================================
-- 5-7 Le funzioni
-- ============================================================
CREATE TEMP TABLE _fn AS
SELECT p.oid, p.proname, p.prosecdef, pg_get_userbyid(p.proowner) AS proprietario
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'script'
   AND p.proname IN ('fn_check_blocco_login', 'fn_registra_tentativo_login',
                     'fn_azzera_tentativi_credenziale', 'fn_imposta_deve_cambiare_password',
                     'fn_blocca_credenziale', 'fn_sblocca_credenziale',
                     'fn_get_deve_cambiare_password', 'fn_guard_super_admin',
                     'fn_login_parametri', 'fn_login_attesa_secondi',
                     'fn_login_freno_passo');

SELECT is(
    (SELECT string_agg(proname || '=' || CASE WHEN prosecdef THEN 'DEFINER' ELSE 'INVOKER' END, ',' ORDER BY proname) FROM _fn),
    'fn_azzera_tentativi_credenziale=DEFINER,fn_blocca_credenziale=DEFINER,fn_check_blocco_login=DEFINER,'
    'fn_get_deve_cambiare_password=INVOKER,fn_guard_super_admin=INVOKER,fn_imposta_deve_cambiare_password=DEFINER,'
    'fn_login_attesa_secondi=INVOKER,fn_login_freno_passo=INVOKER,fn_login_parametri=INVOKER,fn_registra_tentativo_login=DEFINER,'
    'fn_sblocca_credenziale=DEFINER',
    '5) scrivono le DEFINER, leggono e sorvegliano le INVOKER (una firma per nome: niente overload rimasti)');

SELECT is(
    (SELECT bool_and(has_function_privilege('zeroerp_app', oid, 'EXECUTE')) FROM _fn),
    true,
    '6) l''app esegue tutte le funzioni della credenziale');

SELECT is(
    (SELECT bool_and(proprietario = (SELECT pg_get_userbyid(relowner) FROM pg_class
                                      WHERE oid = 'config.credenziali'::regclass))
       FROM _fn WHERE prosecdef),
    true,
    '7) le DEFINER appartengono al proprietario delle tabelle (DEFINER del proprietario, non di un superuser)');

-- ============================================================
-- 8-9 La struttura
-- ============================================================
SELECT is(
    (SELECT count(*)::integer FROM information_schema.columns
      WHERE table_schema = 'anagrafiche' AND table_name = 'identita_digitali'
        AND column_name IN ('tentativi_falliti', 'bloccato_fino_a',
                            'deve_cambiare_password', 'totp_obbligatorio')),
    0,
    '8) le quattro colonne della credenziale non esistono piu'' su identita_digitali (D-1, D-7, D-10)');

SELECT is(
    (SELECT string_agg(tgname, ',' ORDER BY tgname) FROM pg_trigger
      WHERE NOT tgisinternal
        AND tgname IN ('trg_credenziali_a10_guard_ultimo_super_admin_ins_upd',
                       'trg_credenziali_provenienze_m50_cleanup_at_ins',
                       'trg_nomi_tentati_m50_cleanup_at_ins',
                       'trg_nomi_tentati_provenienze_m50_cleanup_at_ins')),
    'trg_credenziali_a10_guard_ultimo_super_admin_ins_upd,trg_credenziali_provenienze_m50_cleanup_at_ins,'
    'trg_nomi_tentati_m50_cleanup_at_ins,trg_nomi_tentati_provenienze_m50_cleanup_at_ins',
    '9) i trigger della credenziale (anti-lockout, retention alla nascita) e quelli di retention delle gemelle del nome');

-- ============================================================
-- 10 CASCADE (solo dove la FK c'e')
-- ============================================================
INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                              first_name, last_name, email, date_joined)
VALUES ('_pgtap_porta_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now());
CREATE TEMP TABLE _u AS SELECT max(id) AS id FROM django.auth_user WHERE username LIKE '\_pgtap\_porta\_%';
SELECT script.fn_registra_tentativo_login((SELECT id FROM _u), sha256('pgtap-nome'::bytea), '203.0.113.50'::inet, false);

CREATE TEMP TABLE _fk AS
SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_config_credenziali_auth_user') AS c;

-- La cancellazione si fa solo dove la FK c'e': altrimenti lascerebbe un orfano
-- che il test non ha niente da dire.
-- ⚠️ Dal 2026-10-06 l'app non ha piu' il DELETE su django.auth_user: una
--   credenziale si elimina dal verbo script.fn_elimina_credenziale, da
--   SUPER_ADMIN (brief-db-elimina-credenziale-senza-veste §4.2). La credenziale
--   del test non ha vesti ne' storia, quindi il verbo la elimina; la sua
--   regola la prova db/pgtap/config/test-elimina-credenziale-v1.sql.
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-porta', true);
DO $sa$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $sa$;
SELECT script.fn_elimina_credenziale((SELECT id FROM _u)) WHERE (SELECT c FROM _fk);

SELECT CASE
    WHEN NOT (SELECT c FROM _fk)
    THEN skip('10) la FK verso django.auth_user non esiste qui (CI: Liquibase gira prima di manage.py migrate, 90_end/20260925-22 resta MARK_RAN)', 1)
    ELSE is((SELECT count(*)::integer FROM config.credenziali WHERE auth_user_id = (SELECT id FROM _u)),
            0,
            '10) cancellare l''auth_user si porta via lo stato della credenziale (e le provenienze, per CASCADE dalla madre)')
END;

-- ============================================================
-- 11-13 Le gemelle del nome tentato (R-7): la stessa porta
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', has_table_privilege('zeroerp_app', 'config.nomi_tentati', 'SELECT')::text,
                   has_table_privilege('zeroerp_app', 'config.nomi_tentati', 'INSERT, UPDATE, DELETE')::text)),
    'true|false',
    '11) config.nomi_tentati: all''app SELECT si'', nessuna scrittura');

SELECT is(
    (SELECT format('%s|%s', has_table_privilege('zeroerp_app', 'config.nomi_tentati_provenienze', 'SELECT')::text,
                   has_table_privilege('zeroerp_app', 'config.nomi_tentati_provenienze', 'INSERT, UPDATE, DELETE')::text)),
    'true|false',
    '12) config.nomi_tentati_provenienze: all''app SELECT si'', nessuna scrittura');

SELECT throws_ok(
    $$ INSERT INTO config.nomi_tentati (nome_digest, ultimo_fallimento_at)
       SELECT sha256('pgtap-porta'::bytea), now() WHERE false $$,
    '42501', NULL,
    '13) come app, INSERT in config.nomi_tentati: permesso negato');

SELECT * FROM finish();
ROLLBACK;
