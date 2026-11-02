-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: UNA CREDENZIALE SENZA VESTE SI ELIMINA DALL'APPLICAZIONE.
--   Brief: brief-db-elimina-credenziale-senza-veste (D-1…D-3 di Tid, fail-closed
--   e sede della traccia decisi il 2026-10-06).
--   ChangeSet: 00_schema/config/20261006-10 (config.credenziali_eliminate),
--   20_code/script/20261006-11 (fn_credenziale_ha_vesti), 20_code/anagrafiche/
--   20261006-12 (vw_accessi_altri sul BB), 20_code/script/20261006-13
--   (fn_check_credenziale_eliminabile), -14 (fn_elimina_credenziale),
--   90_end/20261006-15 (la porta), loop ci_apply 20260205-41 e
--   provision_zeroerp.sql (fase post) (le altre due sedi).
--
-- ⭐ I soggetti si COSTRUISCONO: il SUPER_ADMIN e l'operatore senza privilegi
--   sono umani (dbops.fn_pgtap_crea_operatore_umano); le credenziali senza veste
--   nascono in django.auth_user; la storia e' una riga di
--   config.parameter_overrides (FK NO ACTION verso auth_user, senza RLS).
--
-- ⭐ DUE MONDI, E SI PROVANO TUTTI E DUE. Dove le FK del ponte django esistono
--   (dbdev) il verbo elimina; dove non esistono (CI, installazione nuova:
--   Liquibase gira prima di manage.py migrate) la check e' fail-closed e il
--   verbo rifiuta con E_CREDENZIALE_STORIA_NON_VERIFICABILE. I test 4, 6, 9-11
--   asseriscono il ramo del mondo in cui girano, mai uno skip muto: in CI
--   provano il fail-closed, su dev l'eliminazione.
--
-- Elenco test (plan 18):
--   La regola
--    1) fn_credenziale_ha_vesti: senza vesti false, con una veste true
--    2) ⭐ veste SPENTA: ha vesti lo stesso (D-1), e la check dice CON_VESTI
--    3) la vista e la check leggono la stessa regola: la credenziale senza
--       veste e' NESSUNA_VESTE nel presidio
--    4) credenziale senza vesti ne' storia: '[]' (ponte) / STORIA_NON_VERIFICABILE
--    5) id non valido -> E_AUTH_CHIAMATA_NON_VALIDA
--    6) con una riga di storia: CON_STORIA, e il motivo nomina la tabella
--       (ponte) / STORIA_NON_VERIFICABILE
--   Il verbo
--    7) chi non e' SUPER_ADMIN e' rifiutato per il permesso
--    8) credenziale inesistente -> E_CREDENZIALE_NON_TROVATA
--    9) SUPER_ADMIN elimina la credenziale senza vesti (ponte) / rifiutato e
--       la credenziale resta (senza ponte)
--   10) ...le righe CASCADE se ne vanno con lei, e resta la traccia con lo
--       username e chi l'ha eliminata (ponte) / nessuna traccia (senza ponte)
--   11) ...e non e' piu' nel presidio (ponte) / c'e' ancora (senza ponte)
--   12) una credenziale con una veste spenta: rifiutata con E_CREDENZIALE_CON_VESTI
--   13) una credenziale con storia: rifiutata, col dove nella frase (ponte) /
--       E_CREDENZIALE_STORIA_NON_VERIFICABILE
--   14) ⭐ il verbo CHIAMA la check e non contiene i suoi predicati (§12.5.2)
--   La struttura e la porta
--   15) ⛔ nessuna FK RESTRICT/NO ACTION verso una tabella che segue auth_user
--       in CASCADE (un «nipote» che la check non vede)
--   16) check e verbo SECURITY DEFINER col search_path bloccato, il BB INVOKER
--   17) all'app: SELECT soltanto su config.credenziali_eliminate, niente DELETE
--       su django.auth_user, EXECUTE su check e verbo
--   18) come app: DELETE di django.auth_user e UPDATE della traccia -> 42501
--
-- ⚠️ Gira come l'APPLICAZIONE: i verbi sono DEFINER e leggono chi agisce dalla
--   GUC, come in esercizio. ⚠️ Il 18 prova il 42501 COME APP: da owner (la
--   prova dell'SQL estratto prima dell'apply) e' rosso per costruzione.
-- ⚠️ La riga di config.credenziali che si porta via il CASCADE di una
--   credenziale bloccata da SE' STESSA (bloccata_da = auth_user_id, NO ACTION
--   sulla stessa riga) qui non si costruisce: la scrive solo un verbo DEFINER
--   e il bloccante e' sempre un SUPER_ADMIN con vesti. La regola che la esclude
--   e' derivata dal catalogo nella check (commento di testata del -13).
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-elimina', true);
CREATE TEMP TABLE _op AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP-elimina', false);

-- Due credenziali senza veste: una pulita, una con una riga di storia.
INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                              first_name, last_name, email, date_joined)
VALUES ('_pgtap_elimina_pulita_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now()),
       ('_pgtap_elimina_storia_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now());
CREATE TEMP TABLE _t AS
SELECT (SELECT max(id) FROM django.auth_user WHERE username LIKE '\_pgtap\_elimina\_pulita\_%') AS pulita,
       (SELECT max(id) FROM django.auth_user WHERE username LIKE '\_pgtap\_elimina\_storia\_%') AS storia;

-- La pulita ha una riga che le APPARTIENE (CASCADE): lo stato della credenziale.
SELECT script.fn_registra_tentativo_login((SELECT pulita FROM _t), sha256('pgtap-elimina'::bytea),
                                          '203.0.113.60'::inet, false);

-- La storia: un override di parametro intestato alla credenziale (FK NO ACTION).
-- Su un parametro che AMMETTE override (2026-10-25, brief-db-parametri-senza-override):
-- il primo per id e' tx_id_bypass_enabled, che vale per tutti e lo rifiuterebbe.
-- E di forma TESTO (2026-10-31, D-5 di brief-db-liste-datatable-grezze-secondo-giro):
-- 'pgtap' su un parametro numerico lo rifiuterebbe il guard a07.
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_user_id)
SELECT min(p.id), 'pgtap', (SELECT storia FROM _t) FROM config.parameters p
 WHERE p.ammette_override
   AND p.tipo_valore = 'TESTO';

-- La veste spenta: l'operatore senza privilegi, con la sua veste disattivata.
UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = (SELECT identita_id FROM _op);

-- Il mondo in cui gira il test: le FK del ponte django ci sono?
CREATE TEMP TABLE _ponte AS
SELECT EXISTS (SELECT 1 FROM pg_constraint c
                WHERE c.contype   = 'f'
                  AND c.conrelid  = 'anagrafiche.identita_digitali'::regclass
                  AND c.confrelid = to_regclass('django.auth_user')) AS c;

-- Esegue un'istruzione e ne restituisce lo SQLSTATE (NULL se passa).
CREATE OR REPLACE FUNCTION pg_temp.prova_sql(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    RETURN SQLSTATE;
END $$;

-- Chi agisce: il contesto operatore su un utente dato.
CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

-- ============================================================
-- 1-6 La regola
-- ============================================================
SELECT is(
    format('%s|%s', script.fn_credenziale_ha_vesti((SELECT pulita FROM _t))::text,
                    script.fn_credenziale_ha_vesti((SELECT auth_user_id FROM _op))::text),
    'false|true',
    '1) fn_credenziale_ha_vesti: senza vesti false, con una veste true');

SELECT is(
    (SELECT format('%s|%s|%s|%s', jsonb_array_length(m), m -> 0 ->> 'codice',
                   m -> 0 ->> 'reason', m -> 0 ->> 'reason_key')
       FROM (SELECT script.fn_check_credenziale_eliminabile((SELECT auth_user_id FROM _op)) AS m) x),
    '1|E_CREDENZIALE_CON_VESTI|CON_VESTI|amministrazione.accessi.elimina_reason.con_vesti',
    '2) una veste SPENTA e'' una veste (D-1): un motivo, CON_VESTI, con codice e chiave');

SELECT is(
    (SELECT string_agg(motivo, ',') FROM dbops.vw_credenziali_da_sanare
      WHERE auth_user_id = (SELECT pulita FROM _t)),
    'NESSUNA_VESTE',
    '3) la credenziale senza veste e'' NESSUNA_VESTE nel presidio (la stessa regola della check)');

SELECT is(
    (SELECT CASE WHEN (SELECT c FROM _ponte) THEN m::text ELSE m -> 0 ->> 'reason' END
       FROM (SELECT script.fn_check_credenziale_eliminabile((SELECT pulita FROM _t)) AS m) x),
    CASE WHEN (SELECT c FROM _ponte) THEN '[]' ELSE 'STORIA_NON_VERIFICABILE' END,
    '4) senza vesti ne'' storia: nessun motivo (ponte) / STORIA_NON_VERIFICABILE (senza ponte)');

SELECT throws_like(
    $$ SELECT script.fn_check_credenziale_eliminabile(0) $$,
    '%Chiamata non valida a%',
    '5) id non valido: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT is(
    (SELECT format('%s|%s|%s', m -> 0 ->> 'codice', m -> 0 ->> 'reason',
                   COALESCE(m -> 0 -> 'dettaglio' ->> 'dove', '-'))
       FROM (SELECT script.fn_check_credenziale_eliminabile((SELECT storia FROM _t)) AS m) x),
    CASE WHEN (SELECT c FROM _ponte)
         THEN 'E_CREDENZIALE_CON_STORIA|CON_STORIA|["config.parameter_overrides"]'
         ELSE 'E_CREDENZIALE_STORIA_NON_VERIFICABILE|STORIA_NON_VERIFICABILE|-' END,
    '6) con una riga di storia: CON_STORIA e il dove nomina la tabella (ponte) / fail-closed (senza ponte)');

-- ============================================================
-- 7-14 Il verbo
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _op));
SELECT throws_like(
    $$ SELECT script.fn_elimina_credenziale((SELECT pulita FROM _t)) $$,
    '%Non hai i permessi per questa operazione%',
    '7) chi non e'' SUPER_ADMIN: E_PERMESSO_NEGATO, prima di guardare la credenziale');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT throws_like(
    $$ SELECT script.fn_elimina_credenziale(2147483647) $$,
    '%Credenziale non trovata%',
    '8) credenziale inesistente: E_CREDENZIALE_NON_TROVATA');

-- Il gesto: nel mondo senza ponte deve rifiutare, e il test lo pretende.
CREATE TEMP TABLE _esito (errore text);
DO $gesto$
BEGIN
    PERFORM script.fn_elimina_credenziale((SELECT pulita FROM _t));
    INSERT INTO _esito VALUES (NULL);
EXCEPTION WHEN OTHERS THEN
    INSERT INTO _esito VALUES (SQLERRM);
END
$gesto$;

SELECT is(
    (SELECT CASE WHEN errore IS NULL THEN 'eliminata' ELSE errore END FROM _esito),
    CASE WHEN (SELECT c FROM _ponte) THEN 'eliminata'
         ELSE 'Non è possibile verificare se questa credenziale ha una storia: non si elimina.' END,
    '9) SUPER_ADMIN elimina la credenziale senza vesti (ponte) / rifiutata, fail-closed (senza ponte)');

SELECT is(
    format('%s|%s|%s',
           (SELECT count(*) FROM django.auth_user WHERE id = (SELECT pulita FROM _t)),
           (SELECT count(*) FROM config.credenziali WHERE auth_user_id = (SELECT pulita FROM _t)),
           (SELECT count(*) FROM config.credenziali_eliminate e
             WHERE e.auth_user_id = (SELECT pulita FROM _t)
               AND e.username LIKE '\_pgtap\_elimina\_pulita\_%'
               AND e.eliminata_da = (SELECT auth_user_id FROM _sa))),
    CASE WHEN (SELECT c FROM _ponte) THEN '0|0|1' ELSE '1|1|0' END,
    '10) la credenziale e il suo stato (CASCADE) se ne vanno, resta la traccia con username e autore (ponte) / tutto resta (senza ponte)');

SELECT is(
    (SELECT count(*)::int FROM dbops.vw_credenziali_da_sanare
      WHERE auth_user_id = (SELECT pulita FROM _t)),
    CASE WHEN (SELECT c FROM _ponte) THEN 0 ELSE 1 END,
    '11) eliminata, la credenziale esce dal presidio (ponte) / resta accesa (senza ponte)');

SELECT throws_like(
    $$ SELECT script.fn_elimina_credenziale((SELECT auth_user_id FROM _op)) $$,
    '%Questa credenziale ha delle vesti: non si elimina.%',
    '12) una credenziale con una veste spenta: E_CREDENZIALE_CON_VESTI');

SELECT throws_like(
    $$ SELECT script.fn_elimina_credenziale((SELECT storia FROM _t)) $$,
    CASE WHEN (SELECT c FROM _ponte)
         THEN '%ha già lasciato traccia nell''applicazione (config.parameter_overrides)%'
         ELSE '%Non è possibile verificare se questa credenziale ha una storia%' END,
    '13) una credenziale con storia: rifiutata col dove nella frase (ponte) / fail-closed (senza ponte)');

-- §12.5.2: non «gli esiti coincidono», ma «la madre non contiene il predicato».
SELECT is(
    (SELECT format('%s|%s|%s|%s',
                   -- ::text: format('%s') su un boolean stampa t/f.
                   (s ~ 'fn_check_credenziale_eliminabile\s*\(')::text,
                   (s ~ 'identita_digitali')::text,
                   (s ~ 'fn_credenziale_ha_vesti')::text,
                   (s ~ 'pg_constraint')::text)
       FROM (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS s
               FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname = 'script' AND p.proname = 'fn_elimina_credenziale') x),
    'true|false|false|false',
    '14) fn_elimina_credenziale chiama la check e non riscrive le sue regole');

-- ============================================================
-- 15-18 La struttura e la porta
-- ============================================================
-- ⛔ La check vede le FK verso auth_user, non quelle verso le tabelle che la
--   seguono in CASCADE. Un RESTRICT/NO ACTION su una di quelle (un nipote)
--   farebbe fallire il DELETE senza un motivo: se questo test e' rosso, la
--   check va estesa prima di accettare la FK nuova.
SELECT is(
    (SELECT string_agg(format('%s -> %s', c.conrelid::regclass, c.confrelid::regclass), ', ')
       FROM pg_constraint c
      WHERE c.contype = 'f'
        AND c.confdeltype IN ('r', 'a')
        AND c.confrelid IN (SELECT f.conrelid FROM pg_constraint f
                             WHERE f.contype = 'f'
                               AND f.confrelid = to_regclass('django.auth_user')
                               AND f.confdeltype = 'c')),
    NULL,
    '15) nessuna FK RESTRICT/NO ACTION verso una tabella che segue auth_user in CASCADE');

SELECT is(
    (SELECT string_agg(format('%s:%s:%s', p.proname, p.prosecdef::text,
                              COALESCE(array_to_string(p.proconfig, ';'), '-')), ' ' ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname IN ('fn_credenziale_ha_vesti', 'fn_check_credenziale_eliminabile',
                          'fn_elimina_credenziale')),
    'fn_check_credenziale_eliminabile:true:search_path=pg_catalog, public, pg_temp '
    'fn_credenziale_ha_vesti:false:- '
    'fn_elimina_credenziale:true:search_path=pg_catalog, public, pg_temp',
    '16) check e verbo DEFINER col search_path bloccato, il BB INVOKER');

SELECT is(
    format('%s|%s|%s|%s|%s',
           has_table_privilege('zeroerp_app', 'config.credenziali_eliminate', 'SELECT')::text,
           has_table_privilege('zeroerp_app', 'config.credenziali_eliminate', 'INSERT, UPDATE, DELETE')::text,
           has_table_privilege('zeroerp_app', 'django.auth_user', 'DELETE')::text,
           has_function_privilege('zeroerp_app', 'script.fn_elimina_credenziale(integer)', 'EXECUTE')::text,
           has_function_privilege('zeroerp_app', 'script.fn_check_credenziale_eliminabile(integer)', 'EXECUTE')::text),
    'true|false|false|true|true',
    '17) all''app: la traccia in sola lettura, niente DELETE su auth_user, check e verbo eseguibili');

-- Come app il permesso si controlla prima di guardare le righe: WHERE false
-- basta. Colonne che esistono (su una assente risponderebbe 42703).
SELECT is(
    format('%s|%s',
           (SELECT CASE WHEN x IS NULL THEN 'passa' ELSE x END
              FROM (SELECT pg_temp.prova_sql('DELETE FROM django.auth_user WHERE false') AS x) a),
           (SELECT CASE WHEN x IS NULL THEN 'passa' ELSE x END
              FROM (SELECT pg_temp.prova_sql('UPDATE config.credenziali_eliminate SET username = username WHERE false') AS x) b)),
    '42501|42501',
    '18) come app: DELETE di django.auth_user e UPDATE della traccia -> 42501');

SELECT * FROM finish();
ROLLBACK;
