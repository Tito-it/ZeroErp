-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la PORTA del device del secondo fattore e la FORMA che la regge.
--   Brief: brief-db-secondo-fattore-totp, sezioni 3 e 4.
--   ChangeSet: 90_end/20260929-24 (forward), 90_end/ci_apply/20260205-41
--   (v_tabelle_sola_lettura_app), scripts/sql/provision_zeroerp.sql (fase post) (POSTURA
--   DICHIARATA); 00_schema/config/20260929-07 (forma), 90_end/20260929-23
--   (il CHECK sul SUPER_ADMIN); 20_code/script/20260929-12 → -22,
--   20261001-35 (fn_totp_ricifra_segreto, brief-db-totp-ricifra-segreto §3.5).
--
-- ⭐ E' il presidio che tiene allineate le TRE sedi della postura (linee-guida
--   §11.8): verde su dev col solo forward, rosso su un database ricostruito se
--   una delle altre due manca. Postura letta con has_*_privilege(ruolo, …), e
--   accanto il COMPORTAMENTO come app su una colonna che esiste.
--
-- Elenco test (plan 12):
--    1) config.auth_totp_device: all'app SELECT si', INSERT/UPDATE/DELETE no
--    2) come app, UPDATE di config.auth_totp_device -> 42501
--    3) i verbi che scrivono sono DEFINER, le letture e i guard INVOKER
--       (fn_totp_obbligatorio e' DEFINER: la risposta non dipende da chi chiede)
--    4) le DEFINER hanno il search_path bloccato
--    5) il proprietario delle DEFINER e' il proprietario della tabella
--    6) l'app esegue tutte le funzioni del secondo fattore
--    7) la forma: ultimo_passo_usato c'e', ultimo_codice_usato e abilitato no
--    8) i quattro CHECK della forma ci sono
--    9) un device confermato senza passo non puo' esistere (CHECK)
--   10) credenziali.totp_obbligatorio e profili_accesso.richiede_secondo_fattore
--       ci sono, NOT NULL
--   11) il CHECK del SUPER_ADMIN c'e', e il profilo 9100 ha il segno
--   12) fn_sessione_del_migratore: l'app NON e' la sessione del migratore
--
-- ⚠️ 2 e 12 provano l'APP: da owner (il migratore) sono rossi per
--   costruzione, verdi solo nel runner.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- 1-2 La porta
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', has_table_privilege('zeroerp_app', 'config.auth_totp_device', 'SELECT')::text,
                   has_table_privilege('zeroerp_app', 'config.auth_totp_device', 'INSERT, UPDATE, DELETE')::text)),
    'true|false',
    '1) config.auth_totp_device: all''app SELECT si'', nessuna scrittura');

SELECT throws_ok(
    $$ UPDATE config.auth_totp_device SET ultimo_passo_usato = ultimo_passo_usato WHERE false $$,
    '42501', NULL,
    '2) come app, UPDATE di config.auth_totp_device: permesso negato');

-- ============================================================
-- 3-6 Le funzioni
-- ============================================================
CREATE TEMP TABLE _fn AS
SELECT p.oid, p.proname, p.prosecdef, p.proconfig, pg_get_userbyid(p.proowner) AS proprietario
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'script'
   AND p.proname IN ('fn_imposta_totp_obbligatorio', 'fn_totp_obbligatorio',
                     'fn_get_totp_device', 'fn_guard_utente_stesso',
                     'fn_check_totp_recovery_hash', 'fn_is_super_admin_account',
                     'fn_totp_registra_device', 'fn_totp_conferma_device',
                     'fn_totp_registra_uso', 'fn_totp_consuma_recovery',
                     'fn_totp_rigenera_recovery', 'fn_totp_disabilita_device',
                     'fn_totp_ricifra_segreto');

SELECT is(
    (SELECT string_agg(format('%s=%s', proname, CASE WHEN prosecdef THEN 'D' ELSE 'I' END), ',' ORDER BY proname COLLATE "C") FROM _fn),
    'fn_check_totp_recovery_hash=I,fn_get_totp_device=I,fn_guard_utente_stesso=I,'
    || 'fn_imposta_totp_obbligatorio=D,fn_is_super_admin_account=I,fn_totp_conferma_device=D,'
    || 'fn_totp_consuma_recovery=D,fn_totp_disabilita_device=D,fn_totp_obbligatorio=D,'
    || 'fn_totp_registra_device=D,fn_totp_registra_uso=D,fn_totp_ricifra_segreto=D,'
    || 'fn_totp_rigenera_recovery=D',
    '3) scrivono le DEFINER; letture, guard e check INVOKER (fn_totp_obbligatorio DEFINER)');

SELECT is(
    (SELECT count(*)::int FROM _fn
      WHERE prosecdef AND NOT ('search_path=pg_catalog, public, pg_temp' = ANY (COALESCE(proconfig, '{}')))),
    0,
    '4) le DEFINER hanno il search_path bloccato');

SELECT is(
    (SELECT count(*)::int FROM _fn
      WHERE prosecdef
        AND proprietario <> (SELECT pg_get_userbyid(c.relowner) FROM pg_class c
                              WHERE c.oid = 'config.auth_totp_device'::regclass)),
    0,
    '5) il proprietario delle DEFINER e'' il proprietario della tabella');

SELECT is(
    (SELECT count(*)::int FROM _fn WHERE NOT has_function_privilege('zeroerp_app', oid, 'EXECUTE')),
    0,
    '6) l''app esegue tutte le funzioni del secondo fattore');

-- ============================================================
-- 7-9 La forma del device
-- ============================================================
SELECT is(
    (SELECT string_agg(a.attname, ',' ORDER BY a.attname COLLATE "C")
       FROM pg_attribute a
      WHERE a.attrelid = 'config.auth_totp_device'::regclass AND NOT a.attisdropped
        AND a.attname IN ('ultimo_passo_usato', 'ultimo_codice_usato', 'abilitato', 'confermato')),
    'confermato,ultimo_passo_usato',
    '7) la forma: il passo c''e'', il testo del codice e abilitato no');

SELECT is(
    (SELECT string_agg(c.conname, ',' ORDER BY c.conname COLLATE "C")
       FROM pg_constraint c
      WHERE c.conrelid = 'config.auth_totp_device'::regclass AND c.contype = 'c'
        AND c.conname LIKE 'chk\_auth\_totp\_device\_%'),
    'chk_auth_totp_device_confermato_passo,chk_auth_totp_device_passo,'
    || 'chk_auth_totp_device_recovery_array,chk_auth_totp_device_segreto',
    '8) i quattro CHECK della forma');

-- Come owner (la fixture la scrive il verbo, qui si prova la rete sotto):
-- l'app non puo' scrivere, quindi si prova il predicato del vincolo.
SELECT is(
    (SELECT pg_get_constraintdef(c.oid)
       FROM pg_constraint c
      WHERE c.conrelid = 'config.auth_totp_device'::regclass
        AND c.conname = 'chk_auth_totp_device_confermato_passo'),
    'CHECK (((NOT confermato) OR (ultimo_passo_usato IS NOT NULL)))',
    '9) un device confermato senza passo non puo'' esistere');

-- ============================================================
-- 10-12 Le sedi dell'obbligo e il migratore
-- ============================================================
SELECT is(
    (SELECT string_agg(format('%s.%s=%s', c.relname, a.attname, a.attnotnull::text), ',' ORDER BY c.relname COLLATE "C")
       FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
      WHERE (a.attrelid, a.attname) IN (('config.credenziali'::regclass, 'totp_obbligatorio'),
                                        ('config.profili_accesso'::regclass, 'richiede_secondo_fattore'))),
    'credenziali.totp_obbligatorio=true,profili_accesso.richiede_secondo_fattore=true',
    '10) le due sedi dell''obbligo ci sono, NOT NULL');

SELECT is(
    -- ::text esplicito: format('%s') su un booleano stampa t/f.
    (SELECT format('%s|%s',
                   EXISTS (SELECT 1 FROM pg_constraint c
                            WHERE c.conrelid = 'config.profili_accesso'::regclass
                              AND c.conname = 'chk_profili_accesso_super_admin_secondo_fattore')::text,
                   (SELECT bool_and(pa.richiede_secondo_fattore) FROM config.profili_accesso pa
                     WHERE pa.tipo = 'SUPER_ADMIN')::text)),
    'true|true',
    '11) il CHECK del SUPER_ADMIN c''e'' e il profilo SUPER_ADMIN ha il segno');

SELECT is(dbops.fn_sessione_del_migratore(), false,
    '12) l''app non e'' la sessione del migratore (rosso da owner per costruzione)');

SELECT * FROM finish();
ROLLBACK;
