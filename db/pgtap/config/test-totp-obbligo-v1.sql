-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'OBBLIGO del secondo fattore — la risposta unica e le sue due fonti.
--   Brief: brief-db-secondo-fattore-totp, sezione 2 (decisione di Tid del
--   2026-09-28: obbligo = flag sulla credenziale OPPURE profilo privilegiato;
--   D-T1: un segno sul profilo, sempre acceso sul SUPER_ADMIN).
--   ChangeSet: 00_schema/config/20260929-05, -06; 20_code/script/20260929-10
--   (fn_is_super_admin_account), -11 (fn_is_super_admin dal BB), -12
--   (fn_imposta_totp_obbligatorio), -13 (fn_totp_obbligatorio).
--
-- ⭐ Il profilo privilegiato si COSTRUISCE: un profilo AD_HOC col segno,
--   legato all'identita' di un operatore umano. L'obbligo segue il binding.
--
-- Elenco test (plan 15):
--   La credenziale
--    1) nessuna fonte: (false, NULL)
--    2) chi non e' SUPER_ADMIN non impone l'obbligo -> E_PERMESSO_NEGATO
--    3) un SUPER_ADMIN lo impone: (true, CREDENZIALE)
--    4) ...e lo toglie: (false, NULL), la riga resta con false
--    5) id non valido -> E_AUTH_CHIAMATA_NON_VALIDA
--    6) credenziale che non esiste: (false, NULL) — e' una lettura
--   Il profilo
--    7) un profilo AD_HOC col segno, legato all'identita': (true, PROFILO)
--    8) spento il binding, l'obbligo se ne va: (false, NULL)
--   Il SUPER_ADMIN
--    9) il SUPER_ADMIN ha l'obbligo: (true, PROFILO)
--   10) ...anche in veste CLIENTE_PORTALE: la credenziale vale per tutte le porte
--   11) ...mentre il bypass dei permessi in quella veste resta spento
--       (fn_is_super_admin: il cancello della veste non si e' perso)
--   12) fn_is_super_admin in veste OPERATORE: true, come prima dell'estrazione
--   13) fn_is_super_admin_account di un operatore senza SUPER_ADMIN: false
--   14) la credenziale prevale: SUPER_ADMIN con il flag sulla credenziale -> CREDENZIALE
--   Il vincolo
--   15) spegnere il segno sul profilo SUPER_ADMIN -> 23514
--
-- ⚠️ Gira come l'APPLICAZIONE (il backend scrive oggi profili e binding
--   direttamente: e' la strada di scrittura del segno, brief §2.2). I test
--   che cambiano la veste stanno in fondo al loro blocco e la ripristinano.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _u  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-TOTP-obbligo', false);
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-TOTP-obbligo-SA', true);

CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

CREATE OR REPLACE FUNCTION pg_temp.obbligo(p_auth_user_id integer) RETURNS text
LANGUAGE sql AS $$
    SELECT format('%s|%s', o.obbligatorio::text, COALESCE(o.motivo, 'NULL'))
      FROM script.fn_totp_obbligatorio(p_auth_user_id) o;
$$;

-- ============================================================
-- 1-6 La credenziale
-- ============================================================
SELECT is(pg_temp.obbligo((SELECT auth_user_id FROM _u)), 'false|NULL',
    '1) nessuna fonte: nessun obbligo');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _u));
SELECT throws_like(
    $$ SELECT script.fn_imposta_totp_obbligatorio((SELECT auth_user_id FROM _u), true) $$,
    '%Non hai i permessi per questa operazione%',
    '2) chi non e'' SUPER_ADMIN non impone l''obbligo');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT script.fn_imposta_totp_obbligatorio((SELECT auth_user_id FROM _u), true);
SELECT is(pg_temp.obbligo((SELECT auth_user_id FROM _u)), 'true|CREDENZIALE',
    '3) un SUPER_ADMIN lo impone sulla credenziale: CREDENZIALE');

SELECT script.fn_imposta_totp_obbligatorio((SELECT auth_user_id FROM _u), false);
SELECT is(
    (SELECT format('%s|%s', pg_temp.obbligo((SELECT auth_user_id FROM _u)), c.totp_obbligatorio::text)
       FROM config.credenziali c WHERE c.auth_user_id = (SELECT auth_user_id FROM _u)),
    'false|NULL|false',
    '4) ...e lo toglie: nessun obbligo, la riga resta con false');

SELECT throws_like(
    $$ SELECT * FROM script.fn_totp_obbligatorio(0) $$,
    '%Chiamata non valida a%',
    '5) id non valido: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT is(pg_temp.obbligo((SELECT max(id) + 1000 FROM django.auth_user)), 'false|NULL',
    '6) credenziale che non esiste: nessun obbligo (e'' una lettura)');

-- ============================================================
-- 7-8 Il profilo
-- ============================================================
INSERT INTO config.profili_accesso (tipo, codice, descrizione, richiede_secondo_fattore)
VALUES ('AD_HOC', '_PGTAP_TOTP_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        'pgTAP: profilo privilegiato', true);
CREATE TEMP TABLE _p AS
SELECT max(id) AS profilo_id FROM config.profili_accesso WHERE codice LIKE '\_PGTAP\_TOTP\_%';

DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita((SELECT profilo_id FROM _p), (SELECT identita_id FROM _u)); END $lega$;

SELECT is(pg_temp.obbligo((SELECT auth_user_id FROM _u)), 'true|PROFILO',
    '7) un profilo col segno legato all''identita'': PROFILO');

UPDATE config.profili_accesso_bindings
   SET attivo = false
 WHERE identita_digitale_id = (SELECT identita_id FROM _u);
SELECT is(pg_temp.obbligo((SELECT auth_user_id FROM _u)), 'false|NULL',
    '8) spento il binding, l''obbligo se ne va: segue i binding');

-- ============================================================
-- 9-14 Il SUPER_ADMIN
-- ============================================================
SELECT is(pg_temp.obbligo((SELECT auth_user_id FROM _sa)), 'true|PROFILO',
    '9) il SUPER_ADMIN ha l''obbligo: PROFILO');

SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
SELECT is(pg_temp.obbligo((SELECT auth_user_id FROM _sa)), 'true|PROFILO',
    '10) ...anche in veste CLIENTE_PORTALE: la credenziale vale per tutte le porte');

SELECT is(script.fn_is_super_admin((SELECT auth_user_id FROM _sa)), false,
    '11) ...mentre il bypass dei permessi in quella veste resta spento');
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));

SELECT is(script.fn_is_super_admin((SELECT auth_user_id FROM _sa)), true,
    '12) fn_is_super_admin in veste OPERATORE: true, come prima dell''estrazione');

SELECT is(script.fn_is_super_admin_account((SELECT auth_user_id FROM _u)), false,
    '13) fn_is_super_admin_account di un operatore senza SUPER_ADMIN: false');

SELECT script.fn_imposta_totp_obbligatorio((SELECT auth_user_id FROM _sa), true);
SELECT is(pg_temp.obbligo((SELECT auth_user_id FROM _sa)), 'true|CREDENZIALE',
    '14) la credenziale prevale: il motivo e'' CREDENZIALE anche per un SUPER_ADMIN');

-- ============================================================
-- 15 Il vincolo
-- ============================================================
SELECT throws_ok(
    $$ UPDATE config.profili_accesso SET richiede_secondo_fattore = false
        WHERE tipo = 'SUPER_ADMIN' $$,
    '23514', NULL,
    '15) il segno sul profilo SUPER_ADMIN non si spegne (CHECK)');

SELECT * FROM finish();
ROLLBACK;
