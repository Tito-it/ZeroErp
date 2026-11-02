-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il SOGGETTO del test e' la sessione del migratore, il
--   terzo attore ammesso a disabilitare il secondo fattore di un altro (il
--   caso senza via d'uscita). dbops.fn_sessione_del_migratore legge
--   session_user: la sola prova e' una connessione vera come lui. Il verso
--   negativo (l'app non e' il migratore, e un altro senza privilegi non
--   disabilita) e' in test-totp-porta-v1.sql e test-totp-device-verbi-v1.sql,
--   col runner di default.
--
-- Test: lo sblocco del secondo fattore dal server.
--   Brief: brief-db-secondo-fattore-totp, sezione 3 (decisione di Tid del
--   2026-09-29: lo sblocco lo fa la sessione di chi amministra il database).
--   ChangeSet: 20_code/dbops/20260929-08 (fn_sessione_del_migratore),
--   -09 (la sync chiede al BB), 20_code/script/20260929-22, -26 (la traccia,
--   D-T5) e 00_schema/dbops/20260929-25 (l'evento ammesso).
--
-- Elenco test (plan 5):
--   1) il runner owner e' la sessione del migratore (se rosso, il resto non
--      dice niente: il runner owner di questa macchina non e' chi migra)
--   2) senza utente in sessione e senza motivo -> E_TOTP_MOTIVO_OBBLIGATORIO
--   3) senza utente in sessione, con motivo: il device sparisce
--   4) D-T5: la traccia in dbops.sessioni_utente (evento TOTP_DISABILITATO)
--   5) la sync degli owner lascia ancora passare il migratore (la guardia
--      ora chiede al BB)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- Fixture: l'utente registra e conferma il proprio device (ramo «utente stesso»).
CREATE TEMP TABLE _u AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-TOTP-migratore', false);
DO $f$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _u));
    PERFORM script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-M', '["m1","m2"]'::jsonb);
    PERFORM script.fn_totp_conferma_device((SELECT auth_user_id FROM _u), 5000);
END
$f$;

SELECT is(dbops.fn_sessione_del_migratore(), true,
    format('1) il runner owner (%s) e'' la sessione del migratore', session_user));

-- Dal server non c'e' un utente applicativo.
SELECT set_config('app.current_user_id', '', true);

SELECT throws_like(
    $$ SELECT script.fn_totp_disabilita_device((SELECT auth_user_id FROM _u), NULL) $$,
    '%Indicare il motivo della disattivazione%',
    '2) il migratore senza motivo: E_TOTP_MOTIVO_OBBLIGATORIO');

SELECT script.fn_totp_disabilita_device((SELECT auth_user_id FROM _u), 'unico amministratore, telefono e codici persi');
SELECT is((SELECT stato FROM script.fn_get_totp_device((SELECT auth_user_id FROM _u))), 'ASSENTE',
    '3) il migratore con motivo: il device sparisce');

SELECT is(
    (SELECT format('%s|%s|%s|%s', count(*), max(s.dettaglio ->> 'via'),
                   bool_and(s.dettaglio ->> 'sessione' = session_user::text)::text,
                   max(s.dettaglio ->> 'motivo'))
       FROM dbops.sessioni_utente s
      WHERE s.auth_user_id = (SELECT auth_user_id FROM _u) AND s.evento = 'TOTP_DISABILITATO'),
    '1|SERVER|true|unico amministratore, telefono e codici persi',
    '4) D-T5: la traccia nell''audit degli accessi — da dove, chi (il ruolo di login), perche''');

SELECT lives_ok(
    $$ SELECT dbops.fn_sync_functions_owner() $$,
    '5) fn_sync_functions_owner come migratore: la guardia (dal BB) lascia passare');

SELECT * FROM finish();
ROLLBACK;
