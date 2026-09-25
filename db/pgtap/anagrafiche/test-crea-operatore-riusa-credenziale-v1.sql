-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_crea_operatore_v2 — UNA PERSONA, UNA CREDENZIALE (D-6)
--   e la veste OPERATORE che nasce SPENTA (regola unica dell'invito, R-2).
--   Brief: brief-db-blocco-login-per-credenziale, sezione 5.2 e sezione 12
--   (test 25-26 del §6).
--   ChangeSet: 20260925-42 (la madre), -40 (il building block dell'email),
--   -43 (il check dell'invito).
--
-- ⭐ Casi COSTRUITI: la credenziale «gia' esistente» e' un auth_user nudo,
--   creato qui con password, username e nome suoi. Una veste portale in piu'
--   non aggiungerebbe niente: la madre non legge le altre vesti, solo quella
--   OPERATORE.
--
-- ⚠️ La finestra differita: la madre scrive il soggetto persona fisica e SOLO
--   al passo 4 i suoi indirizzi, e il guard degli indirizzi e' DEFERRABLE.
--   Ogni chiamata che deve riuscire sta fra SET CONSTRAINTS ALL DEFERRED e
--   IMMEDIATE, con un indirizzo di dettaglio: alla riapertura i guard
--   scattano su un operatore finito (stessa forma di
--   dbops.fn_pgtap_crea_operatore_umano).
--
-- Elenco test (plan 13):
--   Il riuso (test 25)
--    1) email di una credenziale esistente, scritta in minuscolo: credenziale
--       RIUSATA, stesso auth_user_id
--    2) lo username restituito e' quello della credenziale, non quello scelto
--    3) nessuna credenziale nuova: ne' con quell'email ne' con lo username scelto
--    4) password e nome della credenziale intatti (la password passata e' ignorata)
--    5) la veste OPERATORE e' nata SPENTA, con la sua risorsa umana
--    6) e l'operatore e' invitabile (fn_check_operatore_invitabile)
--   Il rifiuto (test 26)
--    7) la stessa email di nuovo, veste OPERATORE spenta -> E_CREDENZIALE_GIA_OPERATORE
--    8) ...e con la veste accesa (invito accettato) -> stesso codice
--   La credenziale nuova (R-2)
--    9) email di nessuno: credenziale NUOVA (credenziale_riusata = false)
--   10) ...con la veste OPERATORE SPENTA
--   11) ...e is_active = false: nessuna veste utilizzabile finche' l'invito non e' accettato
--   Atomicita' e firma
--   12) riuso che fallisce a meta' (cognome vuoto): nessuna veste resta sulla credenziale
--   13) la firma con p_attivo non esiste piu'
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- Una credenziale «di un'altra porta»: auth_user nudo, con password, username
-- e nome suoi, email con le maiuscole.
CREATE OR REPLACE FUNCTION pg_temp.mk_cred(p_tag text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer; v_k text := substring(md5(clock_timestamp()::text || random()::text) from 1 for 8);
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_cliente_' || p_tag || '_' || v_k, 'hash-del-cliente', true, false, false,
            'Nome', 'DelCliente', 'Cliente.' || p_tag || '.' || v_k || '@Example.com', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

-- La madre, con i soli dati che il test fa variare.
CREATE OR REPLACE FUNCTION pg_temp.crea_op(p_email text, p_username text, p_cognome text DEFAULT 'Riuso')
RETURNS TABLE (auth_user_id integer, username text, credenziale_riusata boolean)
LANGUAGE sql AS $$
    SELECT m.auth_user_id, m.username, m.credenziale_riusata
      FROM anagrafiche.fn_crea_operatore_v2(
               p_cognome                      := p_cognome,
               p_nome                         := 'pgTAP',
               p_codice_fiscale               := dbops.fn_pgtap_cf_libero(),
               p_username                     := p_username,
               p_email                        := p_email,
               p_password_hash                := 'hash-scelto-dall-admin',
               p_qualifica_id                 := (SELECT q.id FROM config.qualifiche q
                                                   WHERE q.codice_interno = 'DIPENDENTE'),
               p_indirizzo_resid_dettaglio_id := dbops.fn_pgtap_crea_indirizzo_dettaglio('riuso credenziale')) m
$$;

-- ⛔ La riga si rilegge in un'ISTRUZIONE SEPARATA: nella stessa istruzione
--   il JOIN vedrebbe la snapshot di prima della scrittura.
CREATE TEMP TABLE _cli (id integer, email text, username text);
INSERT INTO _cli (id) SELECT pg_temp.mk_cred('riuso');
UPDATE _cli c SET email = au.email, username = au.username
  FROM django.auth_user au WHERE au.id = c.id;

-- ============================================================
-- 1-6) Il riuso (test 25)
-- ============================================================
CREATE TEMP TABLE _scelto AS
SELECT '_pgtap_scelto_' || substring(md5(clock_timestamp()::text) from 1 for 8) AS username;

SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _r1 AS
SELECT * FROM pg_temp.crea_op(lower((SELECT email FROM _cli)), (SELECT username FROM _scelto));
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(
    (SELECT credenziale_riusata::text || '|' || (auth_user_id = (SELECT id FROM _cli))::text FROM _r1),
    'true|true',
    '1) email esistente scritta in minuscolo: credenziale RIUSATA, stesso auth_user_id');

SELECT is(
    (SELECT username FROM _r1),
    (SELECT username::text FROM _cli),
    '2) lo username restituito e'' quello della credenziale, non quello scelto dall''admin');

SELECT is(
    (SELECT count(*)::int FROM django.auth_user
      WHERE lower(email) = lower((SELECT email FROM _cli))
         OR username = (SELECT username FROM _scelto)),
    1,
    '3) nessuna credenziale nuova: una sola con quell''email, nessuna con lo username scelto');

SELECT is(
    (SELECT password || '|' || first_name || '|' || last_name FROM django.auth_user
      WHERE id = (SELECT id FROM _cli)),
    'hash-del-cliente|Nome|DelCliente',
    '4) password e nome della credenziale intatti: la password passata e'' ignorata');

SELECT is(
    (SELECT string_agg(i.attivo::text || '/' || (ru.id IS NOT NULL)::text, ',')
       FROM anagrafiche.identita_digitali i
       LEFT JOIN anagrafiche.risorse_umane ru ON ru.soggetto_ruolo_id = i.soggetto_ruolo_id
      WHERE i.auth_user_id = (SELECT id FROM _cli)
        AND i.ruolo_applicativo = 'OPERATORE'),
    'false/true',
    '5) una veste OPERATORE, nata SPENTA, con la sua risorsa umana');

SELECT is(
    (script.fn_check_operatore_invitabile((SELECT id FROM _cli)))->>'invitabile',
    'true',
    '6) l''operatore sulla credenziale riusata e'' invitabile (l''invito accende la veste)');

-- ============================================================
-- 7-8) Il rifiuto (test 26)
-- ============================================================
SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM pg_temp.crea_op(%L, %L)$$,
        upper((SELECT email FROM _cli)), '_pgtap_secondo_' || substring(md5(clock_timestamp()::text) from 1 for 8))),
    'E_CREDENZIALE_GIA_OPERATORE',
    '7) la stessa email, veste OPERATORE spenta (invito pendente) -> E_CREDENZIALE_GIA_OPERATORE');

-- L'invito accettato.
UPDATE anagrafiche.identita_digitali
   SET attivo = true
 WHERE auth_user_id = (SELECT id FROM _cli)
   AND ruolo_applicativo = 'OPERATORE';

SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT * FROM pg_temp.crea_op(%L, %L)$$,
        (SELECT email FROM _cli), '_pgtap_terzo_' || substring(md5(clock_timestamp()::text) from 1 for 8))),
    'E_CREDENZIALE_GIA_OPERATORE',
    '8) ...e con la veste accesa -> stesso codice');

-- ============================================================
-- 9-11) La credenziale nuova (R-2)
-- ============================================================
CREATE TEMP TABLE _nuova_em AS
SELECT '_pgtap_nuova_' || substring(md5(clock_timestamp()::text) from 1 for 8) AS k;

SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _r2 AS
SELECT * FROM pg_temp.crea_op((SELECT k FROM _nuova_em) || '@example.com', (SELECT k FROM _nuova_em));
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(
    (SELECT credenziale_riusata::text || '|' || username FROM _r2),
    'false|' || (SELECT k FROM _nuova_em),
    '9) email di nessuno: credenziale NUOVA, con lo username scelto');

SELECT is(
    (SELECT string_agg(i.attivo::text, ',') FROM anagrafiche.identita_digitali i
      WHERE i.auth_user_id = (SELECT auth_user_id FROM _r2)
        AND i.ruolo_applicativo = 'OPERATORE'),
    'false',
    '10) ...con la veste OPERATORE SPENTA (R-2: la accende l''invito)');

SELECT is(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _r2)),
    false,
    '11) ...e is_active = false: nessuna veste utilizzabile finche'' l''invito non e'' accettato');

-- ============================================================
-- 12-13) Atomicita' e firma
-- ============================================================
CREATE TEMP TABLE _cli2 AS SELECT pg_temp.mk_cred('atomico') AS id;

-- Il riuso passa lo step 1 (credenziale trovata e bloccata) e muore allo
-- step 2 (flusso A senza cognome): niente di quanto fatto prima deve restare.
CREATE TEMP TABLE _err12 AS
SELECT pg_temp.codice_errore(format(
           $$SELECT * FROM pg_temp.crea_op(%L, 'ignorato', '')$$,
           (SELECT email FROM django.auth_user WHERE id = (SELECT id FROM _cli2)))) AS codice;

SELECT is(
    (SELECT codice FROM _err12) || '|' ||
    (SELECT count(*)::text FROM anagrafiche.identita_digitali
      WHERE auth_user_id = (SELECT id FROM _cli2)),
    'E_ADMIN_VALIDAZIONE|0',
    '12) riuso che muore a meta'' saga (cognome vuoto): E_ADMIN_VALIDAZIONE, e nessuna veste resta sulla credenziale');

SELECT hasnt_function('anagrafiche', 'fn_crea_operatore_v2',
    ARRAY['uuid','text','text','text','text','text','text','integer','integer','date','character',
          'boolean','boolean','date','date','integer','bigint','bigint'],
    '13) la firma con p_attivo non esiste piu''');

SELECT * FROM finish();
ROLLBACK;
