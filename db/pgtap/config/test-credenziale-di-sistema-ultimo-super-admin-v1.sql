-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture spegne i legami SUPER_ADMIN che il database ha, per
--   costruire l'ultimo: dal giro 10-bis le tabelle che danno l'accesso sono in sola
--   lettura per l'app, e nessun verbo spegne un legame (brief-db-porte-aperte-dalla-sola-guc
--   §14, 2026-11-26). Il motivo dell'ultimo SUPER_ADMIN non dipende dalla sessione del
--   migratore, che filtra solo CREDENZIALE_DI_SISTEMA.
-- pgTAP test per Zero ERP
--
-- Test: l'ULTIMO SUPER_ADMIN fra i motivi del blocco di una credenziale.
--   Separato da test-credenziale-di-sistema-v1.sql (casi 14-16 di allora), che gira
--   come l'applicazione: la sessione del proprietario e' quella del migratore, e il
--   verbo le lascia bloccare una credenziale di sistema.
--   Brief: brief-db-credenziale-verbi-amministratore, R-DB-A5 + R-DB-A6.
--
-- Elenco test (plan 3):
--    1) la check sull'ultimo SUPER_ADMIN -> ULTIMO_SUPER_ADMIN, chiave di sempre
--    2) la madre solleva quel motivo -> E_PROFILO_ULTIMO_SUPER_ADMIN
--    3) un'altra credenziale resta bloccabile: '[]'
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _sa  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-sistema', true);
CREATE TEMP TABLE _op  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP-sistema', false);
CREATE TEMP TABLE _tec AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                              first_name, last_name, email, date_joined)
VALUES ('_pgtap_qualunque_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now());
CREATE TEMP TABLE _t AS SELECT max(id) AS bersaglio FROM django.auth_user WHERE username LIKE '\_pgtap\_qualunque\_%';

-- Chi agisce: il contesto operatore su un utente dato.
CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

-- Chi agisce: il SUPER_ADMIN del test.
DO $agisci$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $agisci$;

-- ============================================================
-- 1-3 L'ultimo SUPER_ADMIN
-- ============================================================
-- Spegne tutti i binding SUPER_ADMIN tranne quello del SA del test.
UPDATE config.profili_accesso_bindings pab
   SET attivo = false
  FROM config.profili_accesso pa
 WHERE pa.id = pab.profilo_accesso_id
   AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
   AND pab.attivo = true
   AND pab.identita_digitale_id <> (SELECT identita_id FROM _sa);

SELECT is(
    (SELECT format('%s|%s|%s|%s', jsonb_array_length(m), m -> 0 ->> 'codice',
                   m -> 0 ->> 'reason', m -> 0 ->> 'reason_key')
       FROM (SELECT script.fn_check_credenziale_bloccabile((SELECT auth_user_id FROM _sa)) AS m) x),
    '1|E_PROFILO_ULTIMO_SUPER_ADMIN|ULTIMO_SUPER_ADMIN|amministrazione.accessi.blocca_reason.ultimo_super_admin',
    '1) l''ultimo SUPER_ADMIN: ULTIMO_SUPER_ADMIN, con la chiave che il backend usava gia''');


SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$ SELECT script.fn_blocca_credenziale((SELECT auth_user_id FROM _sa), 'prova su me stesso') $$),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '2) la madre solleva il primo motivo: E_PROFILO_ULTIMO_SUPER_ADMIN');

SELECT is(
    script.fn_check_credenziale_bloccabile((SELECT auth_user_id FROM _op)),
    '[]'::jsonb,
    '3) un operatore qualunque resta bloccabile anche con un solo SUPER_ADMIN');

SELECT * FROM finish();
ROLLBACK;
