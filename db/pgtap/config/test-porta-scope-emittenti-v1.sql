-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: la porta 10, lo scope emittenti, si apre solo dal verbo.
-- Riferimento: brief-db-porte-aperte-dalla-sola-guc §10 (giro 10; D-A a, D-P a,
--   D-Q a di Tid, 2026-11-23/24); changeSet 20_code/script/20261124-01 (la
--   primitiva, con la GUC sull'auth_user_id), -02 (il verbo SECURITY DEFINER col
--   guard del SUPER_ADMIN), 20_code/config/20261124-04 (il guard del DELETE: GUC
--   sulla riga E proprietario), 90_end/20261124-06 (la primitiva riservata).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il verbo e' SECURITY DEFINER col search_path fissato; la primitiva e il
--     guard restano INVOKER (il guard vede chi scrive);
--   - l'app non esegue la primitiva: il permesso del verbo non si aggira;
--   - il verbo chiede il SUPER_ADMIN in prima riga: un operatore, o nessun utente,
--     riceve E_PERMESSO_NEGATO e la riga non cambia;
--   - l'applicazione non cancella la riga diretta, ne' con la GUC accesa ('on') ne'
--     col valore giusto (l'auth_user_id della riga): dal giro 10-bis (§14) la tabella
--     e' in sola lettura per l'app, e il DELETE si ferma sul privilegio (42501) prima
--     del guard. La porta del guard («GUC sulla riga e proprietario») resta per gli
--     scrittori privilegiati, e la attraversa il verbo;
--   - dal verbo, chiamato da un SUPER_ADMIN, l'operatore passa all'altra azienda e
--     la GUC resta vuota.
--
-- ⚠️ Nessun caso «due emittenti»: la tabella non ha RLS, e chi passa il guard e'
--   il SUPER_ADMIN, che vede tutte le aziende. Non c'e' un perimetro da provare.
-- L'operatore e' COSTRUITO (dbops.fn_pgtap_crea_emittente_operatore): non e'
--   SUPER_ADMIN su nessun database. Il SUPER_ADMIN lo costruisce il builder
--   dbops.fn_pgtap_sposta_scope_operatore, che chiama il verbo vero.
-- Gira come l'applicazione (runner di default). ⚠️ Da proprietario chi scrive e' il
--   proprietario: 7 e 9 sono rossi per costruzione (il privilegio non lo ferma, e
--   col valore giusto la porta gli si apre).
--
-- Elenco test (plan 12):
--    1) il verbo: SECURITY DEFINER, search_path fissato
--    2) la primitiva e il guard: SECURITY INVOKER
--    3) l'app non esegue la primitiva, e PUBLIC nemmeno
--    4) un operatore chiama il verbo: E_PERMESSO_NEGATO
--    5) … e la riga non cambia
--    6) senza utente in sessione il verbo rifiuta: E_PERMESSO_NEGATO (fail-closed)
--    7) l'app accende la GUC ('on') e cancella la riga diretta: rifiutata (42501)
--    8) … e la riga c'e' ancora
--    9) ⭐ l'app scrive la GUC con l'auth_user_id della riga e cancella diretta:
--       rifiutata (42501, la sola lettura)
--   10) dal verbo, da SUPER_ADMIN, l'operatore passa all'altra azienda
--   11) la riga e' quella nuova, una sola
--   12) dopo il verbo la GUC e' vuota, e il contesto e' di nuovo l'operatore
-- ------------------------------------------------------------

BEGIN;

-- Un'azienda nuova col suo operatore, non SUPER_ADMIN; una seconda azienda.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

CREATE TEMP TABLE _b ON COMMIT DROP AS
SELECT e.emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente() e;

-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- Il verbo, come istruzione da provare: sposta l'operatore sull'azienda B.
CREATE OR REPLACE FUNCTION pg_temp.verbo()
RETURNS text LANGUAGE sql AS $f$
  SELECT format('SELECT script.fn_change_user_emittenti_scope(%s, ARRAY[%s]::bigint[])',
                (SELECT auth_user_id FROM _e), (SELECT emittente_fiscale_id FROM _b));
$f$;

-- Una cancellazione diretta dell'app, con la GUC scritta nella stessa istruzione.
CREATE OR REPLACE FUNCTION pg_temp.diretta(p_guc text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format($q$WITH porta AS (
                    SELECT set_config('zeroerp.allow_user_emittente_delete_override', %L, true))
                  DELETE FROM config.user_emittenti_fiscali
                   WHERE auth_user_id = %s AND EXISTS (SELECT 1 FROM porta)$q$,
                p_guc, (SELECT auth_user_id FROM _e));
$f$;

-- L'azienda dell'operatore, come la dice la tabella.
CREATE OR REPLACE FUNCTION pg_temp.azienda()
RETURNS bigint LANGUAGE sql AS $f$
  SELECT uef.emittente_fiscale_id FROM config.user_emittenti_fiscali uef
   WHERE uef.auth_user_id = (SELECT auth_user_id FROM _e);
$f$;

-- ============================================================
-- 1-3 La forma
-- ============================================================
SELECT is(
  (SELECT p.prosecdef AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search\_path=%')
     FROM pg_catalog.pg_proc p
    WHERE p.oid = 'script.fn_change_user_emittenti_scope'::regproc),
  true,
  '1) il verbo: SECURITY DEFINER, search_path fissato');

SELECT is(
  (SELECT bool_or(p.prosecdef) FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('script.fn_applica_user_emittenti_scope'::regproc,
                    'config.trgfn_user_emittenti_fiscali_guard_delete'::regproc)),
  false,
  '2) la primitiva e il guard: SECURITY INVOKER');

SELECT is(
  has_function_privilege('zeroerp_app', 'script.fn_applica_user_emittenti_scope'::regproc, 'EXECUTE')
  OR has_function_privilege('public', 'script.fn_applica_user_emittenti_scope'::regproc, 'EXECUTE'),
  false,
  '3) l''app non esegue la primitiva, e PUBLIC nemmeno');

-- ============================================================
-- 4-6 Il permesso del verbo
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.verbo()), 'E_PERMESSO_NEGATO',
          '4) un operatore chiama il verbo: E_PERMESSO_NEGATO');

SELECT is(pg_temp.azienda(), (SELECT emittente_fiscale_id FROM _e),
          '5) … e la riga non cambia: l''operatore resta sulla sua azienda');

DO $vuoto$ BEGIN PERFORM set_config('app.current_user_id', '', false); END $vuoto$;

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.verbo()), 'E_PERMESSO_NEGATO',
          '6) senza utente in sessione il verbo rifiuta (fail-closed)');

DO $ctx2$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx2$;

-- ============================================================
-- 7-9 La porta del DELETE, senza il verbo
-- ============================================================
-- ⚠️ Dal giro 10-bis la tabella e' in sola lettura per l'app: il DELETE diretto si
--   ferma sul privilegio (42501), prima del guard. La porta del guard («GUC sulla
--   riga e proprietario») resta per gli scrittori privilegiati, e la attraversa il
--   verbo (10-12).
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.diretta('on')), '42501',
          '7) l''app accende la GUC e cancella la riga diretta: rifiutata (sola lettura)');

SELECT is(pg_temp.azienda(), (SELECT emittente_fiscale_id FROM _e),
          '8) … e la riga c''e'' ancora');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.diretta((SELECT auth_user_id FROM _e)::text)),
          '42501',
          '9) l''app scrive la GUC con l''auth_user_id della riga e cancella diretta: rifiutata (sola lettura)');

-- ============================================================
-- 10-12 Dal verbo, da SUPER_ADMIN
-- ============================================================
-- ⚠️ La scrittura in un'istruzione e la rilettura nelle successive: nella stessa
--   istruzione lo snapshot non vedrebbe la riga appena scritta.
CREATE TEMP TABLE _esito ON COMMIT DROP AS
SELECT dbops.fn_pgtap_sposta_scope_operatore(
           (SELECT auth_user_id FROM _e), (SELECT emittente_fiscale_id FROM _b)) AS esito;

SELECT is((SELECT (esito ->> 'changed')::boolean FROM _esito), true,
          '10) dal verbo, da SUPER_ADMIN, l''operatore passa all''altra azienda');

SELECT is(
  (SELECT count(*)::int || ' / ' || (min(uef.emittente_fiscale_id) = (SELECT emittente_fiscale_id FROM _b))::text
     FROM config.user_emittenti_fiscali uef
    WHERE uef.auth_user_id = (SELECT auth_user_id FROM _e)),
  '1 / true',
  '11) la riga e'' quella dell''azienda nuova, una sola');

SELECT is(
  coalesce(current_setting('zeroerp.allow_user_emittente_delete_override', true), '')
    || ' / ' || (script.fn_utente_di_sessione() = (SELECT auth_user_id FROM _e))::text,
  ' / true',
  '12) dopo il verbo la GUC e'' vuota, e il contesto e'' di nuovo l''operatore');

SELECT * FROM finish();
ROLLBACK;
