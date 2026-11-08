-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto e' lo SCORRERE DEL TEMPO (freno scaduto, attesa trascorsa, scadenza ricalcolata). Per costruirlo la fixture retrodata config.credenziali e config.credenziali_provenienze, che all'applicazione sono chiuse in scrittura per costruzione (90_end/20260925-24: scrivono solo le funzioni DEFINER). Un helper DEFINER che retrodatasse lo stato sarebbe chiamabile in esercizio e azzererebbe il freno: meglio un test marcato che una porta aperta. Le funzioni sotto test si chiamano come in esercizio.
-- pgTAP test per Zero ERP
--
-- Test: il login quando il tempo passa — freno scaduto, attesa trascorsa,
--   scadenza della riga di provenienza al rinnovo.
--   Brief: brief-db-blocco-login-per-credenziale, sezioni 2.4 e 2.5.
--   ChangeSet: 20260925-10 (check), -11 (registrazione).
--   Il resto del login gira come l'app in test-credenziale-login-v1.sql.
--
-- Elenco test (plan 5):
--    1) freno scaduto, passando dal check: il check passa e la coppia riparte (riga via)
--    2) freno scaduto, SENZA passare dal check: la registrazione riparte da 1, non somma
--    3) attesa NON ancora trascorsa (manca un secondo): il check chiede ancora l'attesa
--    4) attesa trascorsa: il check passa
--    5) al rinnovo di una coppia la scadenza (cleanup_at) si ricalcola da now()
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _par AS SELECT * FROM script.fn_login_parametri();

CREATE OR REPLACE FUNCTION pg_temp.mk_cred(p_etichetta text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_tempo_' || p_etichetta || '_' || substring(md5(clock_timestamp()::text) from 1 for 8),
            '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

-- Porta una credenziale alla soglia da una provenienza.
CREATE OR REPLACE FUNCTION pg_temp.alla_soglia(p_uid integer, p_prov inet) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    FOR i IN 1 .. (SELECT max_tentativi FROM _par) LOOP
        PERFORM script.fn_registra_tentativo_login(p_uid, sha256('pgtap-nome'::bytea), p_prov, false);
    END LOOP;
END $$;

-- Sposta indietro il freno della coppia (la fixture che solo l'owner puo' fare).
CREATE OR REPLACE FUNCTION pg_temp.scadi_freno(p_uid integer, p_prov inet) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE config.credenziali_provenienze p
       SET bloccato_fino_a = now() - interval '1 second'
      FROM config.credenziali c
     WHERE c.id = p.credenziale_id AND c.auth_user_id = p_uid AND p.provenienza = p_prov;
END $$;

CREATE TEMP TABLE _c AS
SELECT pg_temp.mk_cred('check') AS via_check, pg_temp.mk_cred('diretta') AS diretta,
       pg_temp.mk_cred('attesa') AS attesa,   pg_temp.mk_cred('rinnovo') AS rinnovo;

-- ============================================================
-- 1-2 Freno scaduto
-- ============================================================
SELECT pg_temp.alla_soglia((SELECT via_check FROM _c), '203.0.113.20'::inet);
SELECT pg_temp.scadi_freno((SELECT via_check FROM _c), '203.0.113.20'::inet);
SELECT script.fn_check_blocco_login((SELECT via_check FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.20'::inet);

SELECT is(
    (SELECT count(*)::integer FROM config.credenziali_provenienze p
       JOIN config.credenziali c ON c.id = p.credenziale_id
      WHERE c.auth_user_id = (SELECT via_check FROM _c)),
    0,
    '1) freno scaduto, dal check: il check passa e la coppia riparte da zero (riga cancellata)');

SELECT pg_temp.alla_soglia((SELECT diretta FROM _c), '203.0.113.21'::inet);
SELECT pg_temp.scadi_freno((SELECT diretta FROM _c), '203.0.113.21'::inet);

SELECT is(
    (SELECT format('%s|%s', r ->> 'tentativi', r ->> 'bloccato')
       FROM (SELECT script.fn_registra_tentativo_login((SELECT diretta FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.21'::inet, false) AS r) x),
    '1|false',
    '2) freno scaduto, senza il check: la registrazione riparte da 1 invece di frenare al primo errore');

-- ============================================================
-- 3-4 Attesa
-- ============================================================
DO $$
BEGIN
    FOR i IN 1 .. (SELECT tetto_credenziale FROM _par) LOOP
        PERFORM script.fn_registra_tentativo_login((SELECT attesa FROM _c), sha256('pgtap-nome'::bytea), ('198.51.100.' || i)::inet, false);
    END LOOP;
END $$;

-- L'attesa dovuta ora e' la base (al tetto esatto).
UPDATE config.credenziali
   SET ultimo_fallimento_at = now() - make_interval(secs => (SELECT attesa_base_secondi FROM _par) - 1)
 WHERE auth_user_id = (SELECT attesa FROM _c);

SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login((SELECT attesa FROM _c), sha256('pgtap-nome'::bytea), '192.0.2.30'::inet) $$,
    '%riprovare fra %secondi%',
    '3) a un secondo dalla fine dell''attesa: ancora E_LOGIN_ATTESA');

UPDATE config.credenziali
   SET ultimo_fallimento_at = now() - make_interval(secs => (SELECT attesa_base_secondi FROM _par) + 1)
 WHERE auth_user_id = (SELECT attesa FROM _c);

SELECT lives_ok(
    $$ SELECT script.fn_check_blocco_login((SELECT attesa FROM _c), sha256('pgtap-nome'::bytea), '192.0.2.30'::inet) $$,
    '4) attesa trascorsa: il check passa (rallenta, non chiude)');

-- ============================================================
-- 5 Rinnovo della scadenza
-- ============================================================
SELECT script.fn_registra_tentativo_login((SELECT rinnovo FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.40'::inet, false);
UPDATE config.credenziali_provenienze p
   SET cleanup_at = now() - interval '10 days'
  FROM config.credenziali c
 WHERE c.id = p.credenziale_id AND c.auth_user_id = (SELECT rinnovo FROM _c);
SELECT script.fn_registra_tentativo_login((SELECT rinnovo FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.40'::inet, false);

SELECT is(
    (SELECT p.cleanup_at FROM config.credenziali_provenienze p
       JOIN config.credenziali c ON c.id = p.credenziale_id
      WHERE c.auth_user_id = (SELECT rinnovo FROM _c)),
    now() + make_interval(days => (SELECT r.ttl_days FROM dbops.fn_cleanup_at_regola('config', 'credenziali_provenienze') r WHERE r.motivo_salto IS NULL)),
    '5) al rinnovo di una coppia la scadenza si ricalcola: now() + ttl della regola CLEANUP_AT');

SELECT * FROM finish();
ROLLBACK;
