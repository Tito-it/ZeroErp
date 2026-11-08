-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il login per CREDENZIALE e PROVENIENZA — freno sulla coppia, attesa
--   crescente sulla credenziale, azzeramento, cambio password obbligatorio.
--   Brief: brief-db-blocco-login-per-credenziale, sezioni 2-4 e 6.
--   ChangeSet: 20260925-04 … -11, -16, -17, -19, -52, -59 … -61 (e i seed -20,
--   CLEANUP_AT id 21). Dal R-7 le chiamate passano il digest del nome: qui la
--   credenziale c'e' sempre, quindi il digest non si legge (i casi del nome
--   inesistente stanno in test-login-nome-inesistente-v1.sql).
--
-- ⭐ Casi COSTRUITI, non popolazione: ogni credenziale nasce nel test. Un
--   auth_user nudo (nessuna identita') e' il caso piu' forte per «nessun filtro
--   su veste»: il codice non legge piu' identita_digitali, e una veste portale
--   non aggiungerebbe niente che la credenziale senza vesti non dica gia'.
--
-- ⚠️ I numeri non sono scritti qui: soglia, tetto, attesa si leggono da
--   script.fn_login_parametri(), cosi' il test segue il seed invece di
--   fotografarlo.
--
-- Elenco test (plan 22):
--   Il freno sulla provenienza
--    1) credenziale senza riga: il check passa
--    2) credenziale SENZA NESSUNA IDENTITA': il fallimento conta (tentativi = 1)
--    3) alla soglia dalla provenienza P1: il check da P1 -> E_UTENTE_BLOCCATO,
--       con i minuti rimanenti nel messaggio (20260925-52)
--    4) ⭐ stessa credenziale da P2: il check passa (il titolare entra dalla sua macchina)
--    5) credenziale con veste OPERATORE, fallimenti da P1 e P2: una riga per
--       provenienza, non per veste, e la credenziale li somma tutti
--   L'attesa crescente
--    6) al tetto, da provenienze tutte diverse (nessuna alla soglia): nessun
--       freno di coppia, ma il check chiede l'attesa -> E_LOGIN_ATTESA
--    7) un tentativo rifiutato per attesa non conta
--    8) fn_login_attesa_secondi: sotto il tetto 0
--    9) ...al tetto la base, un fallimento dopo il doppio
--   10) ...e si ferma al massimo, anche con un conteggio enorme
--   Retention
--   11) la prima riga di provenienza nasce con cleanup_at = ultimo fallimento + ttl
--   Azzeramento (D-2)
--   12) un accesso riuscito da P2 azzera la credenziale e la SOLA coppia P2:
--       ⭐ il freno su P1 (la macchina di chi attacca) resta
--   13) fn_azzera_tentativi_credenziale senza provenienza (il reset): tutto via
--   Chiamate non valide
--   14) registrazione con provenienza NULL -> E_AUTH_CHIAMATA_NON_VALIDA
--   15) check con provenienza NULL -> E_AUTH_CHIAMATA_NON_VALIDA
--   16) registrazione su un auth_user inesistente -> E_CREDENZIALE_NON_TROVATA
--   Cambio password obbligatorio (D-7)
--   17) credenziale senza riga: fn_get_deve_cambiare_password = false
--   18) fn_imposta_deve_cambiare_password crea la riga; la lettura da' true
--   19) fn_get_user_profile legge il flag dalla credenziale
--   20) fn_get_operatore_detail legge il flag dalla credenziale
--   Firme e parametri
--   21) le firme vecchie (senza provenienza) non esistono piu'
--   22) un parametro del login vuoto -> E_CONFIG_MANCANTE (niente ripiego)
--
-- ⚠️ Gira come l'APPLICAZIONE: le funzioni del login sono DEFINER e l'app ha
--   solo SELECT sulle tabelle della credenziale. I casi che chiedono di
--   RETRODATARE lo stato (freno scaduto, attesa trascorsa) stanno in
--   test-credenziale-login-tempo-v1.sql, marcato owner.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(22);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _par AS SELECT * FROM script.fn_login_parametri();

-- Una credenziale nuda: auth_user senza nessuna identita'.
CREATE OR REPLACE FUNCTION pg_temp.mk_cred(p_etichetta text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_cred_' || p_etichetta || '_' || substring(md5(clock_timestamp()::text) from 1 for 8),
            '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

CREATE TEMP TABLE _c AS
SELECT pg_temp.mk_cred('nuda')  AS nuda,
       pg_temp.mk_cred('attesa') AS attesa,
       pg_temp.mk_cred('vuota')  AS vuota;

CREATE TEMP TABLE _op AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ============================================================
-- 1-5 Il freno sulla provenienza
-- ============================================================
SELECT lives_ok(
    $$ SELECT script.fn_check_blocco_login((SELECT nuda FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.1'::inet) $$,
    '1) credenziale senza riga: il check passa');

SELECT is(
    (script.fn_registra_tentativo_login((SELECT nuda FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.1'::inet, false) ->> 'tentativi')::integer,
    1,
    '2) credenziale senza nessuna identita'': il fallimento CONTA (prima non contava)');

-- Fino alla soglia da P1 (il primo fallimento e' gia' registrato).
DO $$
BEGIN
    FOR i IN 2 .. (SELECT max_tentativi FROM _par) LOOP
        PERFORM script.fn_registra_tentativo_login((SELECT nuda FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.1'::inet, false);
    END LOOP;
END $$;

-- ⚠️ Un numero, non «qualcosa»: un %s rimasto letterale (segnaposto senza
--   valore) passerebbe un LIKE su «riprovare fra % minuti» (20260925-52).
SELECT throws_matching(
    $$ SELECT script.fn_check_blocco_login((SELECT nuda FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.1'::inet) $$,
    'da questa postazione: riprovare fra [0-9]+ minuti',
    '3) alla soglia da P1: il check da P1 solleva E_UTENTE_BLOCCATO, con i minuti');

SELECT lives_ok(
    $$ SELECT script.fn_check_blocco_login((SELECT nuda FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.2'::inet) $$,
    '4) stessa credenziale da P2: il check passa — il freno e'' della coppia, non del titolare');

DO $$
BEGIN
    FOR i IN 1 .. 3 LOOP
        PERFORM script.fn_registra_tentativo_login((SELECT auth_user_id FROM _op), sha256('pgtap-nome'::bytea), '203.0.113.1'::inet, false);
    END LOOP;
    FOR i IN 1 .. 2 LOOP
        PERFORM script.fn_registra_tentativo_login((SELECT auth_user_id FROM _op), sha256('pgtap-nome'::bytea), '203.0.113.2'::inet, false);
    END LOOP;
END $$;

SELECT is(
    (SELECT format('%s|%s', c.fallimenti_consecutivi,
                   string_agg(host(p.provenienza) || '=' || p.tentativi_falliti, ',' ORDER BY p.provenienza))
       FROM config.credenziali c
       JOIN config.credenziali_provenienze p ON p.credenziale_id = c.id
      WHERE c.auth_user_id = (SELECT auth_user_id FROM _op)
      GROUP BY c.fallimenti_consecutivi),
    '5|203.0.113.1=3,203.0.113.2=2',
    '5) veste OPERATORE: una riga per provenienza (non per veste), la credenziale li somma tutti');

-- ============================================================
-- 6-10 L'attesa crescente
-- ============================================================
-- Tetto raggiunto da provenienze tutte DIVERSE: nessuna coppia arriva alla soglia.
DO $$
BEGIN
    FOR i IN 1 .. (SELECT tetto_credenziale FROM _par) LOOP
        PERFORM script.fn_registra_tentativo_login(
            (SELECT attesa FROM _c), sha256('pgtap-nome'::bytea), ('198.51.100.' || i)::inet, false);
    END LOOP;
END $$;

SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login((SELECT attesa FROM _c), sha256('pgtap-nome'::bytea), '192.0.2.1'::inet) $$,
    '%Troppi tentativi non riusciti: riprovare fra %secondi%',
    '6) al tetto da provenienze tutte diverse: nessun freno di coppia, ma l''attesa -> E_LOGIN_ATTESA');

SELECT is(
    (SELECT c.fallimenti_consecutivi FROM config.credenziali c WHERE c.auth_user_id = (SELECT attesa FROM _c)),
    (SELECT tetto_credenziale FROM _par),
    '7) il tentativo rifiutato per attesa non ha contato');

SELECT is(
    script.fn_login_attesa_secondi((SELECT tetto_credenziale - 1 FROM _par),
        (SELECT tetto_credenziale FROM _par), (SELECT attesa_base_secondi FROM _par),
        (SELECT attesa_max_secondi FROM _par)),
    0,
    '8) fn_login_attesa_secondi: sotto il tetto, nessuna attesa');

SELECT is(
    ARRAY[script.fn_login_attesa_secondi(10, 10, 2, 60), script.fn_login_attesa_secondi(11, 10, 2, 60)],
    ARRAY[2, 4],
    '9) al tetto la base, un fallimento dopo il doppio');

SELECT is(
    ARRAY[script.fn_login_attesa_secondi(15, 10, 2, 60), script.fn_login_attesa_secondi(100000, 10, 2, 60)],
    ARRAY[60, 60],
    '10) si ferma al massimo, anche con un conteggio enorme (nessun overflow)');

-- ============================================================
-- 11 Retention
-- ============================================================
SELECT is(
    (SELECT bool_and(p.cleanup_at = p.ultimo_fallimento_at
                     + make_interval(days => (SELECT r.ttl_days FROM dbops.fn_cleanup_at_regola('config', 'credenziali_provenienze') r WHERE r.motivo_salto IS NULL)))
       FROM config.credenziali_provenienze p
       JOIN config.credenziali c ON c.id = p.credenziale_id
      WHERE c.auth_user_id = (SELECT attesa FROM _c)),
    true,
    '11) ogni riga di provenienza nasce con cleanup_at = ultimo fallimento + ttl della regola CLEANUP_AT');

-- ============================================================
-- 12-13 Azzeramento (D-2)
-- ============================================================
SELECT script.fn_registra_tentativo_login((SELECT nuda FROM _c), sha256('pgtap-nome'::bytea), '203.0.113.2'::inet, true);

SELECT is(
    (SELECT format('%s|%s', c.fallimenti_consecutivi,
                   (SELECT string_agg(host(p.provenienza) || ':' || (p.bloccato_fino_a > now())::text, ',')
                      FROM config.credenziali_provenienze p WHERE p.credenziale_id = c.id))
       FROM config.credenziali c WHERE c.auth_user_id = (SELECT nuda FROM _c)),
    '0|203.0.113.1:true',
    '12) accesso riuscito da P2: fallimenti a zero, ma il freno su P1 resta — un login del titolare non regala tentativi a chi attacca');

SELECT script.fn_azzera_tentativi_credenziale((SELECT auth_user_id FROM _op));  -- senza provenienza: il reset

SELECT is(
    (SELECT format('%s|%s', c.fallimenti_consecutivi,
                   (SELECT count(*) FROM config.credenziali_provenienze p WHERE p.credenziale_id = c.id))
       FROM config.credenziali c WHERE c.auth_user_id = (SELECT auth_user_id FROM _op)),
    '0|0',
    '13) fn_azzera_tentativi_credenziale senza provenienza (il reset, D-2): fallimenti e tutte le provenienze via');

-- ============================================================
-- 14-16 Chiamate non valide
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_registra_tentativo_login((SELECT nuda FROM _c), sha256('pgtap-nome'::bytea), NULL, false) $$,
    '%Chiamata non valida a script.fn_registra_tentativo_login%',
    '14) registrazione con provenienza NULL: E_AUTH_CHIAMATA_NON_VALIDA (NULL non e'' una chiave)');

SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login((SELECT nuda FROM _c), sha256('pgtap-nome'::bytea), NULL) $$,
    '%Chiamata non valida a script.fn_check_blocco_login%',
    '15) check con provenienza NULL: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    $$ SELECT script.fn_registra_tentativo_login((SELECT max(id) + 1000 FROM django.auth_user), sha256('pgtap-nome'::bytea), '203.0.113.9'::inet, false) $$,
    '%Credenziale non trovata%',
    '16) registrazione su un auth_user inesistente: E_CREDENZIALE_NON_TROVATA (in CI la FK non c''e'')');

-- ============================================================
-- 17-20 Cambio password obbligatorio (D-7)
-- ============================================================
SELECT is(
    script.fn_get_deve_cambiare_password((SELECT vuota FROM _c)),
    false,
    '17) credenziale senza riga: deve_cambiare_password = false (il default dell''assenza, in un posto solo)');

SELECT script.fn_imposta_deve_cambiare_password((SELECT vuota FROM _c), true);

SELECT is(
    (SELECT format('%s|%s', script.fn_get_deve_cambiare_password((SELECT vuota FROM _c))::text,
                   (SELECT count(*) FROM config.credenziali c WHERE c.auth_user_id = (SELECT vuota FROM _c)))),
    'true|1',
    '18) fn_imposta_deve_cambiare_password crea la riga, e la lettura da'' true');

CREATE TEMP TABLE _umano AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-cred', false);
SELECT script.fn_imposta_deve_cambiare_password((SELECT auth_user_id FROM _umano), true);

SELECT is(
    script.fn_get_user_profile((SELECT auth_user_id FROM _umano)) ->> 'deve_cambiare_password',
    'true',
    '19) fn_get_user_profile legge deve_cambiare_password dalla credenziale');

SELECT is(
    (SELECT d.deve_cambiare_password FROM script.fn_get_operatore_detail((SELECT auth_user_id FROM _umano)) d),
    true,
    '20) fn_get_operatore_detail legge deve_cambiare_password dalla credenziale');

-- ============================================================
-- 21-22 Firme e parametri
-- ============================================================
SELECT is(
    (SELECT count(*)::integer FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.oid::regprocedure::text IN (
                'script.fn_check_blocco_login(integer)',
                'script.fn_registra_tentativo_login(integer,boolean)',
                -- senza il digest del nome (20260925-60/-61, R-7)
                'script.fn_check_blocco_login(integer,inet)',
                'script.fn_registra_tentativo_login(integer,inet,boolean)')),
    0,
    '21) le firme vecchie (senza provenienza, senza digest del nome) non esistono piu''');

-- ⚠️ Per ultimo: cambia un parametro (il ROLLBACK lo rimette).
-- ⚠️ Dal 2026-10-31 (brief-db-liste-datatable-grezze-secondo-giro, D-5) il guard
--   a07 rifiuta in scrittura un vuoto su un INTERO_POSITIVO: per provare che il
--   LETTORE resta fail-loud (non da' per scontato il guard) il parametro si
--   dichiara prima TESTO, l'unica strada da cui un valore fuori forma entra.
UPDATE config.parameters SET tipo_valore = 'TESTO' WHERE code = 'login_tetto_credenziale';
UPDATE config.parameters SET default_value = '' WHERE code = 'login_tetto_credenziale';

SELECT throws_like(
    $$ SELECT * FROM script.fn_login_parametri() $$,
    '%Configurazione mancante: parametro login_tetto_credenziale%',
    '22) un parametro del login vuoto: E_CONFIG_MANCANTE, nessun valore di ripiego nel codice');

SELECT * FROM finish();
ROLLBACK;
