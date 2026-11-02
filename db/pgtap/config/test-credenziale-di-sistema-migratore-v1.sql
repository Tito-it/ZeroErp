-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il SOGGETTO del test e' la sessione del migratore, la
--   sola strada da cui una credenziale di sistema si blocca (D-1, l'uscita
--   d'emergenza). dbops.fn_sessione_del_migratore legge session_user: la sola
--   prova e' una connessione vera come lui. Il verso negativo (dall'app il
--   blocco e' rifiutato) e' in test-credenziale-di-sistema-v1.sql, col runner
--   di default.
--
-- Test: il blocco di una credenziale di sistema dal server.
--   Brief: brief-db-credenziale-verbi-amministratore, R-DB-A6 (decisione D-1
--   di Tid del 2026-10-03).
--   ChangeSet: 20_code/script/20261003-01, -02, -03.
--
-- Elenco test (plan 6):
--   1) il runner owner e' la sessione del migratore (se rosso, il resto non
--      dice niente: il runner owner di questa macchina non e' chi migra)
--   2) dal server senza un SUPER_ADMIN dichiarato -> E_PERMESSO_NEGATO (il
--      blocco ha sempre un autore, chk_credenziali_blocco)
--   3) dal server, con il SUPER_ADMIN dichiarato, la credenziale di sistema
--      si blocca: la riga porta chi e perche'
--   4) la check continua a dire CREDENZIALE_DI_SISTEMA: il motivo si toglie
--      nella madre, non nella regola
--   5) l'obbligo del secondo fattore resta rifiutato anche dal server
--   6) lo sblocco la riapre
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

CREATE TEMP TABLE _sa  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-sistema-server', true);
CREATE TEMP TABLE _tec AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

SELECT is(dbops.fn_sessione_del_migratore(), true,
    format('1) il runner owner (%s) e'' la sessione del migratore', session_user));

SELECT set_config('app.current_user_id', '', true);
SELECT throws_like(
    $$ SELECT script.fn_blocca_credenziale((SELECT auth_user_id FROM _tec), 'chiave rubata') $$,
    '%Non hai i permessi per questa operazione%',
    '2) dal server senza SUPER_ADMIN dichiarato: E_PERMESSO_NEGATO');

DO $f$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $f$;
SELECT script.fn_blocca_credenziale((SELECT auth_user_id FROM _tec), '  chiave rubata  ');
SELECT is(
    (SELECT format('%s|%s|%s', (c.bloccata_at IS NOT NULL)::text,
                   (c.bloccata_da = (SELECT auth_user_id FROM _sa))::text, c.motivo_blocco)
       FROM config.credenziali c WHERE c.auth_user_id = (SELECT auth_user_id FROM _tec)),
    'true|true|chiave rubata',
    '3) dal server la credenziale di sistema si blocca: quando, chi, perche''');

SELECT is(
    script.fn_check_credenziale_bloccabile((SELECT auth_user_id FROM _tec)) -> 0 ->> 'reason',
    'CREDENZIALE_DI_SISTEMA',
    '4) la regola non cambia col chiamante: e'' la madre che toglie il motivo dal server');

SELECT throws_like(
    $$ SELECT script.fn_imposta_totp_obbligatorio((SELECT auth_user_id FROM _tec), true) $$,
    '%Le credenziali di sistema non si modificano da qui%',
    '5) accendere il secondo fattore resta rifiutato anche dal server');

SELECT script.fn_sblocca_credenziale((SELECT auth_user_id FROM _tec));
SELECT is(
    (SELECT count(*)::int FROM config.credenziali c
      WHERE c.auth_user_id = (SELECT auth_user_id FROM _tec) AND c.bloccata_at IS NOT NULL),
    0,
    '6) lo sblocco la riapre (l''uscita resta aperta)');

SELECT * FROM finish();
ROLLBACK;
