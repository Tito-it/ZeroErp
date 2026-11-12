-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'email della credenziale e' UNICA senza distinguere maiuscole e
--   minuscole (D-9) — l'indice su django.auth_user, il building block che la
--   legge, il guard di fn_crea_auth_user.
--   Brief: brief-db-blocco-login-per-credenziale, sezione 5.1 e sezione 12
--   (test 22-24 del §6).
--   ChangeSet: 20260925-40 (script.fn_get_auth_user_id_for_email),
--   20260925-41 (fn_crea_auth_user), 20260925-44 (90_end, l'indice).
--
-- ⚠️ L'INDICE IN CI NON C'E', E IL TEST LO SA DAL REGISTRO, NON DALL'INDICE.
--   ix_auth_user_email_lower_unique nasce in 90_end con onFail CONTINUE: in CI
--   Liquibase gira tutto prima di `manage.py migrate`, quindi il changeSet
--   salta e NON si registra. Il ramo si sceglie leggendo databasechangelog:
--     - 20260925-44 registrato -> l'indice DEVE esserci, con quella forma, e
--       il vecchio (20260401-20) no: test 5-8 veri, 9 saltato;
--     - non registrato (CI) -> test 5-8 saltati, 9 vero.
--   ⛔ Non dalla presenza dell'indice: un indice che su dev non fosse nato
--   farebbe saltare in silenzio proprio i test che lo devono trovare.
--
-- Elenco test (plan 9):
--   Il building block script.fn_get_auth_user_id_for_email
--    1) trova la credenziale con l'email scritta in MAIUSCOLO e con spazi ai bordi
--    2) email NULL e '' -> NULL (la stringa vuota non e' una chiave)
--    3) email di nessuno -> NULL
--   fn_crea_auth_user (test 24 del brief)
--    4) un'email che differisce solo per le maiuscole -> E_ADMIN_EMAIL_DUPLICATA
--   L'indice (dove il changeSet -44 e' registrato)
--    5) forma: UNIQUE su lower(email), WHERE email <> ''
--    6) il vecchio ix_auth_user_email_unique non c'e' piu'
--    7) (test 22) Mario@x e mario@x con INSERT diretto: il secondo -> 23505
--    8) (test 23) due credenziali con email '' : entrambe ammesse
--   Dove l'indice NON c'e' (CI)
--    9) due credenziali con la stessa email: il building block solleva
--       E_CREDENZIALE_EMAIL_AMBIGUA invece di sceglierne una
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Fixture
-- ============================================================

-- Una credenziale nuda con l'email data (INSERT diretto: e' cio' che fa la
-- seconda strada di creazione del backend, che non passa dal guard).
CREATE OR REPLACE FUNCTION pg_temp.mk_cred(p_email text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_email_' || substring(md5(clock_timestamp()::text || random()::text) from 1 for 10),
            '!', true, false, false, '', '', p_email, now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

-- Il ramo: il changeSet dell'indice e' registrato su questo database?
CREATE TEMP TABLE _ramo AS
SELECT EXISTS (SELECT 1 FROM databasechangelog
                WHERE id = '20260925-44-unique-auth-user-email-senza-maiuscole') AS indice_atteso;

-- Un'email libera, per corsa.
CREATE TEMP TABLE _em AS
SELECT 'Pgtap.Email.' || substring(md5(clock_timestamp()::text) from 1 for 8) || '@Example.com' AS email;

CREATE TEMP TABLE _cred AS
SELECT pg_temp.mk_cred((SELECT email FROM _em)) AS id;

-- ============================================================
-- 1-3) Il building block
-- ============================================================
SELECT is(
    script.fn_get_auth_user_id_for_email('  ' || upper((SELECT email FROM _em)) || ' '),
    (SELECT id FROM _cred),
    '1) fn_get_auth_user_id_for_email trova la credenziale con l''email in MAIUSCOLO e spazi ai bordi');

SELECT is(
    ARRAY[script.fn_get_auth_user_id_for_email(NULL), script.fn_get_auth_user_id_for_email(''),
          script.fn_get_auth_user_id_for_email('   ')],
    ARRAY[NULL, NULL, NULL]::integer[],
    '2) email NULL, vuota o di soli spazi -> NULL: la stringa vuota non e'' una chiave');

SELECT is(
    script.fn_get_auth_user_id_for_email('nessuno.' || md5(clock_timestamp()::text) || '@example.com'),
    NULL::integer,
    '3) email di nessuno -> NULL');

-- ============================================================
-- 4) (test 24) fn_crea_auth_user: solo le maiuscole diverse -> duplicata
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_auth_user(p_username := %L, p_email := %L, p_password_hash := 'x')$$,
        '_pgtap_email_dup_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        lower((SELECT email FROM _em)))),
    'E_ADMIN_EMAIL_DUPLICATA',
    '4) fn_crea_auth_user con l''email in minuscolo di una esistente -> E_ADMIN_EMAIL_DUPLICATA');

-- ============================================================
-- 5-8) L'indice, dove il changeSet -44 e' registrato
-- ============================================================
SELECT CASE WHEN (SELECT indice_atteso FROM _ramo) THEN
    is((SELECT count(*)::int FROM pg_indexes
         WHERE schemaname = 'django' AND tablename = 'auth_user'
           AND indexname = 'ix_auth_user_email_lower_unique'
           AND indexdef ILIKE 'CREATE UNIQUE INDEX%(lower((email)::text))%WHERE%email%<>%''''%'),
       1,
       '5) ix_auth_user_email_lower_unique: UNIQUE su lower(email), solo email valorizzate')
ELSE skip('changeSet 20260925-44 non registrato (CI: Liquibase gira prima di Django e il changeSet e'' onFail CONTINUE)', 1)
END;

SELECT CASE WHEN (SELECT indice_atteso FROM _ramo) THEN
    is((SELECT count(*)::int FROM pg_indexes
         WHERE schemaname = 'django' AND tablename = 'auth_user'
           AND indexname = 'ix_auth_user_email_unique'),
       0,
       '6) il vecchio ix_auth_user_email_unique (distingueva le maiuscole) e'' ritirato')
ELSE skip('changeSet 20260925-44 non registrato (CI)', 1)
END;

SELECT CASE WHEN (SELECT indice_atteso FROM _ramo) THEN
    throws_ok(format('SELECT pg_temp.mk_cred(%L)', upper((SELECT email FROM _em))),
              '23505', NULL,
              '7) (test 22) la stessa email in maiuscolo con INSERT diretto: rifiutata dall''indice')
ELSE skip('changeSet 20260925-44 non registrato (CI)', 1)
END;

SELECT CASE WHEN (SELECT indice_atteso FROM _ramo) THEN
    lives_ok($$SELECT pg_temp.mk_cred(''), pg_temp.mk_cred('')$$,
             '8) (test 23) due credenziali con email vuota: entrambe ammesse')
ELSE skip('changeSet 20260925-44 non registrato (CI)', 1)
END;

-- ============================================================
-- 9) Dove l'indice NON c'e': due credenziali, stessa email -> il building
--    block solleva, non sceglie
-- ============================================================
-- ⛔ La seconda credenziale in un'ISTRUZIONE SEPARATA: il building block e'
--   STABLE, e nella stessa istruzione vedrebbe la snapshot di prima.
DO $dup$
BEGIN
    IF NOT (SELECT indice_atteso FROM _ramo) THEN
        PERFORM pg_temp.mk_cred(upper((SELECT email FROM _em)));
    END IF;
END $dup$;

SELECT CASE WHEN NOT (SELECT indice_atteso FROM _ramo) THEN
    is(dbops.fn_pgtap_codice_errore(format(
           $$SELECT script.fn_get_auth_user_id_for_email(%L)$$,
           (SELECT email FROM _em))),
       'E_CREDENZIALE_EMAIL_AMBIGUA',
       '9) due credenziali con la stessa email a meno delle maiuscole -> E_CREDENZIALE_EMAIL_AMBIGUA')
ELSE skip('l''indice unico c''e'': due credenziali con la stessa email non si possono costruire', 1)
END;

SELECT * FROM finish();
ROLLBACK;
