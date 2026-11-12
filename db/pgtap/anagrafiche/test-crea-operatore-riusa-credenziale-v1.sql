-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_crea_operatore_v2 — UNA PERSONA, UNA CREDENZIALE (D-6)
--   e la veste OPERATORE che nasce SPENTA (regola unica dell'invito, R-2).
--   Brief: brief-db-blocco-login-per-credenziale, sezione 5.2 e sezione 12
--   (test 25-26 del §6).
--   ChangeSet: 20260925-42 e -51 (la madre), -40 (il building block
--   dell'email), -43 (il check dell'invito).
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
-- Elenco test (plan 20):
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
--   Il consenso e l'altra persona (§12.7, 20260925-51)
--   14) riuso SENZA consenso -> E_CREDENZIALE_DA_CONFERMARE, e niente scritto
--   15) ...la frase nomina lo username trovato (per il dialog)
--   16) consenso che dichiara un'ALTRA credenziale -> E_CREDENZIALE_DA_CONFERMARE
--   17) credenziale con veste su una persona fisica, flusso A con un altro CF
--       -> E_CREDENZIALE_ALTRA_PERSONA, anche col consenso
--   18) ...flusso B con un altro soggetto -> E_CREDENZIALE_ALTRA_PERSONA
--   19) ...flusso A con lo STESSO CF: stessa persona, parla E_ADMIN_CF_DUPLICATO
--   20) ...flusso B con lo STESSO soggetto: l'identita' passa, serve il consenso
--
-- ⭐ La credenziale «di una persona fisica» ha una veste SHOP_CUSTOMER su un
--   ruolo cliente di un soggetto persona fisica: il rifiuto «gia' operatore»
--   guarda solo le vesti OPERATORE, quindi non la copre, e il controllo
--   d'identita' e' l'unico che parla.
--   ⚠️ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): fino a quel giorno
--   la fixture era un operatore disattivato nella forma di allora (veste
--   DISABILITATO). Da R-DB-1 un operatore disattivato resta OPERATORE con
--   attivo = false, cioe' «gia' operatore» (test 7), e il tipo DISABILITATO
--   la tabella viva lo rifiuta: la fixture sposta la veste su un ruolo
--   cliente dello stesso soggetto, che e' cio' che il test voleva dire.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);

-- ============================================================
-- Fixture
-- ============================================================

-- Codice e frase dell'errore (la frase serve al 15).
CREATE OR REPLACE FUNCTION pg_temp.errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text; v_m text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME, v_m = MESSAGE_TEXT;
    RETURN v_c || ' | ' || v_m;
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
CREATE OR REPLACE FUNCTION pg_temp.crea_op(p_email text, p_username text, p_cognome text DEFAULT 'Riuso',
                                           p_riusa integer DEFAULT NULL, p_soggetto uuid DEFAULT NULL,
                                           p_cf text DEFAULT NULL)
RETURNS TABLE (auth_user_id integer, username text, credenziale_riusata boolean)
LANGUAGE sql AS $$
    SELECT m.auth_user_id, m.username, m.credenziale_riusata
      FROM anagrafiche.fn_crea_operatore_v2(
               p_soggetto_id                  := p_soggetto,
               p_cognome                      := p_cognome,
               p_nome                         := 'pgTAP',
               p_codice_fiscale               := COALESCE(p_cf, dbops.fn_pgtap_cf_libero()),
               p_username                     := p_username,
               p_email                        := p_email,
               p_password_hash                := 'hash-scelto-dall-admin',
               p_qualifica_id                 := (SELECT q.id FROM config.qualifiche q
                                                   WHERE q.codice_interno = 'DIPENDENTE'),
               p_indirizzo_resid_dettaglio_id := dbops.fn_pgtap_crea_indirizzo_dettaglio('riuso credenziale'),
               p_riusa_auth_user_id           := p_riusa,
               p_sesso := 'M') m
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
-- Col consenso: la credenziale dichiarata e' quella che c'e' (§12.7).
SELECT * FROM pg_temp.crea_op(lower((SELECT email FROM _cli)), (SELECT username FROM _scelto),
                              p_riusa := (SELECT id FROM _cli));
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
    dbops.fn_pgtap_codice_errore(format(
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
    dbops.fn_pgtap_codice_errore(format(
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
SELECT dbops.fn_pgtap_codice_errore(format(
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

-- ============================================================
-- 14-20) Il consenso e l'altra persona (§12.7, 20260925-51)
-- ============================================================
CREATE TEMP TABLE _cli3 (id integer, email text, username text);
INSERT INTO _cli3 (id) SELECT pg_temp.mk_cred('consenso');
UPDATE _cli3 c SET email = au.email, username = au.username
  FROM django.auth_user au WHERE au.id = c.id;

-- ⚠️ Finestra differita: nel flusso A il consenso si controlla DOPO il
--   soggetto (i rifiuti definitivi parlano prima), e col preambolo IMMEDIATE
--   il guard degli indirizzi del soggetto appena creato parlerebbe al suo posto.
--   In esercizio quel guard scatta al COMMIT.
SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _err14 AS
SELECT pg_temp.errore(format($$SELECT * FROM pg_temp.crea_op(%L, 'ignorato')$$,
                             (SELECT email FROM _cli3))) AS e;
CREATE TEMP TABLE _err16 AS
SELECT dbops.fn_pgtap_codice_errore(format($$SELECT * FROM pg_temp.crea_op(%L, 'ignorato', p_riusa := %s)$$,
                                    (SELECT email FROM _cli3), (SELECT id FROM _cli))) AS c;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(
    split_part((SELECT e FROM _err14), ' | ', 1) || '|' ||
    (SELECT count(*)::text FROM anagrafiche.identita_digitali WHERE auth_user_id = (SELECT id FROM _cli3)),
    'E_CREDENZIALE_DA_CONFERMARE|0',
    '14) riuso senza consenso: E_CREDENZIALE_DA_CONFERMARE, e nessuna veste scritta');

SELECT ok(
    (SELECT e FROM _err14) LIKE '%' || (SELECT username FROM _cli3) || '%',
    '15) la frase nomina lo username della credenziale trovata (per il dialog)');

SELECT is(
    (SELECT c FROM _err16),
    'E_CREDENZIALE_DA_CONFERMARE',
    '16) consenso che dichiara un''altra credenziale: E_CREDENZIALE_DA_CONFERMARE');

-- Una credenziale con una veste su una PERSONA FISICA che non e' una veste
-- operatore: la veste dell'operatore umano diventa SHOP_CUSTOMER su un ruolo
-- cliente (CL) dello stesso soggetto; e un secondo operatore come «altra
-- persona» per il flusso B.
CREATE TEMP TABLE _pf AS
SELECT o.auth_user_id, o.soggetto_id, o.identita_id
  FROM dbops.fn_pgtap_crea_operatore_umano('riuso persona', false) o;
CREATE TEMP TABLE _altro AS
SELECT o.soggetto_id FROM dbops.fn_pgtap_crea_operatore_umano('riuso altra persona', false) o;

UPDATE anagrafiche.identita_digitali
   SET attivo            = false,
       ruolo_applicativo = 'SHOP_CUSTOMER'::config.ruolo_applicativo,
       soggetto_ruolo_id = dbops.fn_pgtap_crea_soggetto_ruolo((SELECT soggetto_id FROM _pf), 'CL')
 WHERE id = (SELECT identita_id FROM _pf);
SET CONSTRAINTS ALL IMMEDIATE;

ALTER TABLE _pf ADD COLUMN email text, ADD COLUMN cf text;
UPDATE _pf p SET email = au.email FROM django.auth_user au WHERE au.id = p.auth_user_id;
UPDATE _pf p SET cf = s.id_fiscale_univoco_cf_piva FROM anagrafiche.soggetti s WHERE s.id = p.soggetto_id;

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$SELECT * FROM pg_temp.crea_op(%L, 'ignorato', p_riusa := %s)$$,
                                 (SELECT email FROM _pf), (SELECT auth_user_id FROM _pf))),
    'E_CREDENZIALE_ALTRA_PERSONA',
    '17) veste su una persona fisica, flusso A con un altro CF: E_CREDENZIALE_ALTRA_PERSONA, anche col consenso');

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$SELECT * FROM pg_temp.crea_op(%L, 'ignorato', p_riusa := %s, p_soggetto := %L)$$,
                                 (SELECT email FROM _pf), (SELECT auth_user_id FROM _pf), (SELECT soggetto_id FROM _altro))),
    'E_CREDENZIALE_ALTRA_PERSONA',
    '18) ...flusso B con un altro soggetto: E_CREDENZIALE_ALTRA_PERSONA');

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$SELECT * FROM pg_temp.crea_op(%L, 'ignorato', p_riusa := %s, p_cf := %L)$$,
                                 (SELECT email FROM _pf), (SELECT auth_user_id FROM _pf), (SELECT cf FROM _pf))),
    'E_ADMIN_CF_DUPLICATO',
    '19) ...flusso A con lo STESSO CF: stessa persona, parla E_ADMIN_CF_DUPLICATO (si usa il soggetto esistente)');

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$SELECT * FROM pg_temp.crea_op(%L, 'ignorato', p_soggetto := %L)$$,
                                 (SELECT email FROM _pf), (SELECT soggetto_id FROM _pf))),
    'E_CREDENZIALE_DA_CONFERMARE',
    '20) ...flusso B con lo STESSO soggetto: l''identita'' passa, serve il consenso');

SELECT * FROM finish();
ROLLBACK;
