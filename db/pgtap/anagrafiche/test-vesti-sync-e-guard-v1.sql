-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un utente TECNICO
--   (dbops.fn_pgtap_crea_roster_processo scrive dbops.processi_identita, che
--   il ruolo applicativo non scrive) e lega un profilo a mano per provare il
--   rifiuto: stesso criterio di anagrafiche/test-area-accessi-v1.sql.
--
-- Test: il giro 2 delle vesti — la sincronizzazione che segue la veste che se
--       ne va, `tecnica` solo sull'operatore, il SUPER_ADMIN mai su un'identita'
--       tecnica, fn_crea_risorsa_umana (nome nuovo, veste spenta, rifiuti)
-- ChangeSet: 20261125-58 … -70
-- Brief: brief-db-accessi-area-clienti §5.1 (giro 2)
--
-- Elenco test (plan 14):
--   La sincronizzazione (S59)
--    1) cancellare l'ultima veste spegne la credenziale
--    2) spostare la veste su un'altra credenziale spegne quella di prima e
--       accende la nuova
--    3) il job spegne una credenziale accesa senza nessuna veste
--   I guard (S63)
--    4) tecnica = true su una veste di portale -> E_VESTE_TECNICA_SOLO_OPERATORE
--    5) il SUPER_ADMIN legato a un'identita' tecnica -> E_SUPER_ADMIN_SU_VESTE_TECNICA
--   I verbi (S6, S65, S22)
--    6) fn_crea_risorsa_umana: SUPER_ADMIN senza credenziale -> E_ADMIN_VALIDAZIONE
--    7) fn_crea_risorsa_umana: credenziale con una veste OPERATORE -> E_CREDENZIALE_GIA_OPERATORE
--    8) fn_crea_risorsa_umana: la veste nasce spenta per default
--    9) fn_crea_risorsa_umana_v2 e fn_crea_operatore_v2 non ci sono piu' (90_end/20261127-06)
--   La forma (presidi: il caso vero chiede di spegnere ogni altro
--   amministratore, o una seconda persona col suo ruolo e senza rapporto)
--   10) S61: il guard dell'ultimo SUPER_ADMIN sulla veste scatta anche sul
--       cambio di credenziale, ruolo, tipo e tecnica
--   11) S61: il guard del rapporto scatta anche sul DELETE
--   12) S62: il guard del rapporto acceso cerca anche il ruolo di prima
--   13) S60: la sync del rapporto scatta su INSERT, UPDATE di ruolo e DELETE
--   14) S63: fn_is_super_admin_account esclude le identita' tecniche
-- ------------------------------------------------------------
BEGIN;

-- L'utente tecnico si costruisce PRIMA del contesto (crea la sua azienda).
CREATE TEMP TABLE _tec AS
SELECT r.auth_user_id, r.identita_id
  FROM dbops.fn_pgtap_crea_roster_processo('send_pending_emails') r;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _op AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-G2-op', false);

CREATE TEMP TABLE _cli AS
SELECT c.soggetto_ruolo_id AS sr_id FROM dbops.fn_pgtap_crea_cliente_ba('giro2') c;
SET CONSTRAINTS ALL IMMEDIATE;

CREATE OR REPLACE FUNCTION pg_temp.credenziale(p_nome text, p_attiva boolean) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer;  -- ⚠️ niente %TYPE su django.*
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_g2_' || p_nome || '_' || substring(md5(clock_timestamp()::text) FROM 1 FOR 8),
            '!', p_attiva, false, false, '', '', '', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.attiva(p_auth_user_id integer) RETURNS boolean
LANGUAGE sql AS $$ SELECT is_active FROM django.auth_user WHERE id = p_auth_user_id $$;

-- ⚠️ format('%s', boolean) stampa t/f: gli attesi composti si scrivono cosi'.
-- Esegue un'istruzione e ne restituisce il codice di dominio (campo
-- CONSTRAINT di un P0001), lo SQLSTATE per un altro errore, 'ok' se passa.
CREATE OR REPLACE FUNCTION pg_temp.codice(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_codice text;  -- un nome d'errore, nessuna colonna
BEGIN
    EXECUTE p_sql;
    RETURN 'ok';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
    RETURN COALESCE(NULLIF(v_codice, ''), SQLSTATE);
END $$;

-- Tre credenziali: a con una veste cliente accesa (la cancellazione), b con
-- una veste accesa che passa a c (lo spostamento), d senza vesti e accesa.
CREATE TEMP TABLE _c AS
SELECT pg_temp.credenziale('a', false) AS a, pg_temp.credenziale('b', false) AS b,
       pg_temp.credenziale('c', false) AS c, pg_temp.credenziale('d', true)  AS d;

INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
VALUES ((SELECT sr_id FROM _cli), (SELECT a FROM _c), 'CLIENTE_PORTALE', true),
       ((SELECT sr_id FROM _cli), (SELECT b FROM _c), 'SHOP_CUSTOMER',   true);

-- ============================================================
-- 1-3 La sincronizzazione
-- ============================================================
CREATE TEMP TABLE _prima AS SELECT pg_temp.attiva((SELECT a FROM _c)) AS a;
DELETE FROM anagrafiche.identita_digitali WHERE auth_user_id = (SELECT a FROM _c);
SELECT is(
    format('%s|%s', (SELECT a FROM _prima), pg_temp.attiva((SELECT a FROM _c))),
    't|f',
    '1) la credenziale era accesa dalla sua veste; cancellata la veste, si spegne');

UPDATE anagrafiche.identita_digitali SET auth_user_id = (SELECT c FROM _c)
 WHERE auth_user_id = (SELECT b FROM _c);
SELECT is(
    format('%s|%s', pg_temp.attiva((SELECT b FROM _c)), pg_temp.attiva((SELECT c FROM _c))),
    'f|t',
    '2) la veste passa da b a c: b si spegne, c si accende');

CREATE TEMP TABLE _job AS SELECT anagrafiche.fn_sync_auth_user_expired() AS n;
SELECT is(
    format('%s|%s', (SELECT n >= 1 FROM _job), pg_temp.attiva((SELECT d FROM _c))),
    't|f',
    '3) il job spegne la credenziale accesa senza nessuna veste');

-- ============================================================
-- 4-5 I guard di tecnica
-- ============================================================
SELECT is(
    pg_temp.codice(format(
        $$INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo, tecnica)
          VALUES (%s, %s, 'CLIENTE_PORTALE', false, true)$$,
        (SELECT sr_id FROM _cli), (SELECT d FROM _c))),
    'E_VESTE_TECNICA_SOLO_OPERATORE',
    '4) tecnica = true su una veste di portale si rifiuta');

SELECT is(
    pg_temp.codice(format('SELECT config.fn_applica_lega_profilo_identita(config.fn_profilo_super_admin_id(), %s)',
                          (SELECT identita_id FROM _tec))),
    'E_SUPER_ADMIN_SU_VESTE_TECNICA',
    '5) il SUPER_ADMIN non si lega a un''identita'' tecnica');

-- ============================================================
-- 6-9 I verbi
-- ============================================================
SELECT is(
    pg_temp.codice(format(
        $$SELECT anagrafiche.fn_crea_risorsa_umana(p_soggetto_id := gen_random_uuid(),
                                                    p_qualifica_id := %s, p_is_super_admin := true)$$,
        (SELECT q.id FROM config.qualifiche q WHERE q.attivo ORDER BY q.id LIMIT 1))),
    'E_ADMIN_VALIDAZIONE',
    '6) il SUPER_ADMIN senza credenziale non si ignora: E_ADMIN_VALIDAZIONE');

SELECT is(
    pg_temp.codice(format(
        $$SELECT anagrafiche.fn_crea_risorsa_umana(p_soggetto_id := gen_random_uuid(),
                                                    p_qualifica_id := %s, p_auth_user_id := %s)$$,
        (SELECT q.id FROM config.qualifiche q WHERE q.attivo ORDER BY q.id LIMIT 1),
        (SELECT auth_user_id FROM _op))),
    'E_CREDENZIALE_GIA_OPERATORE',
    '7) una credenziale che ha gia'' una veste OPERATORE si rifiuta');

SELECT is(
    pg_get_function_arguments('anagrafiche.fn_crea_risorsa_umana'::regproc)
        LIKE '%p_attivo boolean DEFAULT false%',
    true,
    '8) fn_crea_risorsa_umana: la veste nasce spenta per default (p_attivo DEFAULT false)');

SELECT is(
    format('%s|%s',
           to_regproc('anagrafiche.fn_crea_risorsa_umana_v2') IS NULL,
           to_regproc('anagrafiche.fn_crea_operatore_v2') IS NULL),
    't|t',
    '9) i due _v2 non ci sono piu'': i verbi sono fn_crea_risorsa_umana e fn_crea_operatore');

-- ============================================================
-- 10-14 La forma
-- ============================================================
SELECT is(
    (SELECT pg_get_triggerdef(t.oid) LIKE '%auth_user_id%' AND pg_get_triggerdef(t.oid) LIKE '%soggetto_ruolo_id%'
            AND pg_get_triggerdef(t.oid) LIKE '%ruolo_applicativo%' AND pg_get_triggerdef(t.oid) LIKE '%tecnica%'
       FROM pg_trigger t
      WHERE t.tgrelid = 'anagrafiche.identita_digitali'::regclass
        AND t.tgfoid  = 'anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin'::regproc),
    true,
    '10) S61: il guard dell''ultimo SUPER_ADMIN sulla veste segue credenziale, ruolo, tipo e tecnica');

SELECT is(
    (SELECT bool_or(t.tgtype & 8 = 8) FROM pg_trigger t
      WHERE t.tgrelid = 'anagrafiche.risorse_umane'::regclass
        AND t.tgfoid  = 'anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin'::regproc),
    true,
    '11) S61: il guard dell''ultimo SUPER_ADMIN sul rapporto scatta anche sul DELETE');

SELECT is(
    (SELECT p.prosrc LIKE '%IN (OLD.soggetto_ruolo_id, NEW.soggetto_ruolo_id)%'
       FROM pg_proc p WHERE p.oid = 'anagrafiche.trgfn_risorse_umane_guard_identita_attiva'::regproc),
    true,
    '12) S62: il guard del rapporto acceso cerca la veste anche sul ruolo di prima');

SELECT is(
    (SELECT format('%s|%s|%s', bool_or(t.tgtype & 4 = 4), bool_or(t.tgtype & 8 = 8),
                   bool_or(pg_get_triggerdef(t.oid) LIKE '%soggetto_ruolo_id%'))
       FROM pg_trigger t
      WHERE t.tgrelid = 'anagrafiche.risorse_umane'::regclass
        AND t.tgfoid  = 'anagrafiche.trgfn_risorse_umane_sync_auth_user_active'::regproc),
    't|t|t',
    '13) S60: la sync del rapporto scatta su INSERT, DELETE e cambio di ruolo');

SELECT is(
    (SELECT p.prosrc LIKE '%NOT id.tecnica%'
       FROM pg_proc p WHERE p.oid = 'script.fn_is_super_admin_account'::regproc),
    true,
    '14) S63: fn_is_super_admin_account esclude le identita'' tecniche');

SELECT * FROM finish();
ROLLBACK;
