-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_credenziale_per_email — la credenziale di un'email, con
--   username e vesti, per il dialog di conferma del riuso; e la madre
--   anagrafiche.fn_crea_operatore_v2 che la legge dalla stessa funzione.
--   Brief: brief-db-blocco-login-per-credenziale, sezione 17.
--   ChangeSet: 20260927-40 (la funzione), 20260927-41 (la madre).
--
-- ⭐ Casi COSTRUITI: la credenziale senza vesti e' un auth_user nudo creato
--   qui; quella con una veste e' un operatore della fixture
--   dbops.fn_pgtap_crea_operatore_umano. Il risultato atteso si legge dalle
--   tabelle, non dalla funzione esaminata.
--
-- Elenco test (plan 9):
--   La funzione
--    1) esiste, con la firma (text)
--    2) email di nessuno -> zero righe
--    3) email NULL, vuota o di soli spazi -> zero righe
--    4) credenziale senza vesti, email scritta in MAIUSCOLO e con spazi:
--       una riga, con l'auth_user_id e lo username della credenziale
--    5) ...e vesti = [] (la credenziale c'e' anche senza vesti)
--    6) credenziale con una veste OPERATORE: una veste sola...
--    7) ...con ruolo, stato e denominazione del soggetto letti dalle tabelle
--   La madre (regola del 2)
--    8) il rifiuto E_CREDENZIALE_DA_CONFERMARE nomina lo username che la
--       funzione restituisce
--    9) la madre chiama la funzione e non compone piu' le vesti da se'
--
-- ⚠️ Il 9 e' un presidio sul TESTO della madre: conta la chiamata (nome
--   seguito da `(`) e l'assenza di un'aggregazione jsonb propria. Il corpo
--   della madre non nomina l'aggregazione nemmeno nei commenti.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Fixture
-- ============================================================
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

-- Una credenziale nuda: auth_user senza vesti, email con le maiuscole.
CREATE OR REPLACE FUNCTION pg_temp.mk_cred(p_tag text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer; v_k text := substring(md5(clock_timestamp()::text || random()::text) from 1 for 8);
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_cred_' || p_tag || '_' || v_k, 'hash', true, false, false,
            'Nome', 'Cognome', 'Cred.' || p_tag || '.' || v_k || '@Example.com', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

-- ⛔ La riga si rilegge in un'ISTRUZIONE SEPARATA: nella stessa istruzione
--   il JOIN vedrebbe la snapshot di prima della scrittura.
CREATE TEMP TABLE _nuda (id integer, email text, username text);
INSERT INTO _nuda (id) SELECT pg_temp.mk_cred('nuda');
UPDATE _nuda n SET email = au.email, username = au.username
  FROM django.auth_user au WHERE au.id = n.id;

CREATE TEMP TABLE _op AS
SELECT o.auth_user_id, o.identita_id, o.soggetto_id
  FROM dbops.fn_pgtap_crea_operatore_umano('credenziale per email', false) o;
ALTER TABLE _op ADD COLUMN email text;
UPDATE _op p SET email = au.email FROM django.auth_user au WHERE au.id = p.auth_user_id;

-- ============================================================
-- 1-3) La funzione, e le email che non portano una credenziale
-- ============================================================
SELECT has_function('script', 'fn_get_credenziale_per_email', ARRAY['text'],
    '1) script.fn_get_credenziale_per_email(text) esiste');

SELECT is(
    (SELECT count(*)::int FROM script.fn_get_credenziale_per_email(
         'nessuno.' || md5(clock_timestamp()::text) || '@example.com')),
    0,
    '2) email di nessuno: zero righe');

SELECT is(
    (SELECT count(*)::int FROM script.fn_get_credenziale_per_email(NULL))
  + (SELECT count(*)::int FROM script.fn_get_credenziale_per_email(''))
  + (SELECT count(*)::int FROM script.fn_get_credenziale_per_email('   ')),
    0,
    '3) email NULL, vuota o di soli spazi: zero righe (la stringa vuota non e'' una chiave)');

-- ============================================================
-- 4-5) Credenziale senza vesti
-- ============================================================
CREATE TEMP TABLE _r_nuda AS
SELECT c.* FROM script.fn_get_credenziale_per_email(
    '  ' || upper((SELECT email FROM _nuda)) || ' ') c;

SELECT is(
    (SELECT count(*)::text || '|' || min(auth_user_id)::text || '|' || min(username) FROM _r_nuda),
    '1|' || (SELECT id::text FROM _nuda) || '|' || (SELECT username FROM _nuda),
    '4) email in maiuscolo e con spazi: una riga, auth_user_id e username della credenziale');

SELECT is(
    (SELECT vesti FROM _r_nuda),
    '[]'::jsonb,
    '5) credenziale senza vesti: vesti = [] (la riga c''e'' lo stesso)');

-- ============================================================
-- 6-7) Credenziale con una veste
-- ============================================================
CREATE TEMP TABLE _r_op AS
SELECT c.* FROM script.fn_get_credenziale_per_email((SELECT email FROM _op)) c;

SELECT is(
    (SELECT jsonb_array_length(vesti) FROM _r_op WHERE auth_user_id = (SELECT auth_user_id FROM _op)),
    1,
    '6) credenziale di un operatore: una veste sola');

SELECT is(
    (SELECT vesti -> 0 FROM _r_op),
    (SELECT jsonb_build_object(
                'ruolo_applicativo', idg.ruolo_applicativo,
                'attivo',            idg.attivo,
                'soggetto',          s.ragione_sociale_completa)
       FROM anagrafiche.identita_digitali idg
       JOIN anagrafiche.soggetti s ON s.id = (SELECT soggetto_id FROM _op)
      WHERE idg.id = (SELECT identita_id FROM _op)),
    '7) la veste porta ruolo, stato e denominazione del soggetto');

-- ============================================================
-- 8-9) La madre legge dalla stessa funzione (regola del 2)
-- ============================================================
-- ⚠️ Finestra differita: nel flusso A il consenso si controlla DOPO il
--   soggetto, e col preambolo IMMEDIATE il guard degli indirizzi del soggetto
--   appena creato parlerebbe al suo posto. In esercizio scatta al COMMIT.
SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _err8 AS
SELECT pg_temp.errore(format(
    $$SELECT * FROM anagrafiche.fn_crea_operatore_v2(
          p_cognome                      := 'Consenso',
          p_nome                         := 'pgTAP',
          p_codice_fiscale               := dbops.fn_pgtap_cf_libero(),
          p_username                     := 'ignorato',
          p_email                        := %L,
          p_password_hash                := 'hash-scelto-dall-admin',
          p_qualifica_id                 := (SELECT q.id FROM config.qualifiche q
                                              WHERE q.codice_interno = 'DIPENDENTE'),
          p_indirizzo_resid_dettaglio_id := dbops.fn_pgtap_crea_indirizzo_dettaglio('credenziale per email'),
          p_sesso := 'M')$$,
    (SELECT email FROM _nuda))) AS e;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(
    (SELECT e FROM _err8) LIKE 'E_CREDENZIALE_DA_CONFERMARE | %'
    AND (SELECT e FROM _err8) LIKE '%' || (SELECT username FROM _r_nuda) || '%',
    true,
    '8) il rifiuto della madre e'' E_CREDENZIALE_DA_CONFERMARE e nomina lo username che la funzione restituisce');

SELECT is(
    (SELECT (p.prosrc ~ 'script\.fn_get_credenziale_per_email\s*\(')::text || '|' ||
            (p.prosrc !~ 'jsonb_agg')::text
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'anagrafiche' AND p.proname = 'fn_crea_operatore_v2'),
    'true|true',
    '9) la madre chiama script.fn_get_credenziale_per_email e non compone le vesti da se''');

SELECT * FROM finish();
ROLLBACK;
