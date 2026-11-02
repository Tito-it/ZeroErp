-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la risposta del login NON dice se il nome esiste (R-7) — freno e
--   attesa valgono per il NOME TENTATO, esista o no.
--   Brief: brief-db-blocco-login-per-credenziale, sezione 13.
--   ChangeSet: 20260925-55 … -62 (tabelle gemelle, retention, passo del freno,
--   check e registrazione a due chiavi, porta).
--
-- ⭐ Casi COSTRUITI: la credenziale nasce nel test, il nome inesistente e' un
--   digest fabbricato qui (mai visto dal database). Il cuore e' il 9: la stessa
--   sequenza di fallimenti su una credenziale vera e su un nome inesistente
--   deve dare, passo per passo, lo STESSO ritorno e lo STESSO rifiuto. E' la
--   proprieta' che R-7 chiede, scritta come confronto e non come elenco di casi.
--
-- ⚠️ I numeri non sono scritti qui: soglia, durata, tetto si leggono da
--   script.fn_login_parametri(), cosi' il test segue il seed invece di
--   fotografarlo.
--
-- Elenco test (plan 16):
--   Il passo del freno (fn_login_freno_passo, puro sui valori)
--    1) una riga nuova: 1 tentativo, nessun freno (se la soglia e' > 1)
--    2) alla soglia: freno fino ad adesso + blocco_minuti
--    3) un freno scaduto riparte da 1
--    4) un fallimento durante il freno lo rinnova
--   Il nome inesistente
--    5) il fallimento CONTA (tentativi = 1)...
--    6) ...su config.nomi_tentati, per digest
--    7) ...e nessuna riga in config.credenziali
--    8) le righe del nome nascono con la scadenza (cleanup_at, le due tabelle)
--    9) ⭐ STESSA sequenza su credenziale vera e nome inesistente: stessi
--       ritorni della registrazione e stesso rifiuto del check alla soglia
--   10) alla soglia da P1: il check del nome solleva E_UTENTE_BLOCCATO, coi minuti
--   11) stesso nome da P2: passa (il freno e' della coppia)
--   12) al tetto da provenienze tutte diverse: E_LOGIN_ATTESA anche per il nome
--   Chiamate non valide
--   13) check con digest di 31 byte -> E_AUTH_CHIAMATA_NON_VALIDA
--   14) check con digest NULL -> E_AUTH_CHIAMATA_NON_VALIDA
--   15) registrazione di un SUCCESSO senza credenziale -> E_AUTH_CHIAMATA_NON_VALIDA
--   16) nome inesistente senza righe: il check passa
--
-- Gira come l'APPLICAZIONE: le funzioni del login sono DEFINER, l'app sulle
--   tabelle ha solo SELECT.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _par AS SELECT * FROM script.fn_login_parametri();

-- Digest di un nome che non esiste: fabbricato qui, unico per corsa.
CREATE OR REPLACE FUNCTION pg_temp.dg(p_etichetta text) RETURNS bytea
LANGUAGE sql AS $$
    SELECT sha256(convert_to('_pgtap_nome_' || p_etichetta || '_' || txid_current()::text
                             || '_' || md5(random()::text), 'UTF8'));
$$;

CREATE TEMP TABLE _n AS
SELECT pg_temp.dg('freno')     AS freno,
       pg_temp.dg('parita')    AS parita,
       pg_temp.dg('attesa')    AS attesa,
       pg_temp.dg('mai')       AS mai;

-- Una credenziale nuda per il confronto del 9.
INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                              first_name, last_name, email, date_joined)
VALUES ('_pgtap_nome_parita_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now());
CREATE TEMP TABLE _c AS
SELECT max(id) AS parita FROM django.auth_user WHERE username LIKE '\_pgtap\_nome\_parita\_%';

CREATE TEMP TABLE _cred_prima AS SELECT count(*) AS n FROM config.credenziali;

-- ============================================================
-- 1-4 Il passo del freno
-- ============================================================
SELECT is(
    (SELECT f.tentativi || '|' || (f.bloccato_fino_a IS NULL)
       FROM script.fn_login_freno_passo(0, NULL, now(),
                                        GREATEST((SELECT max_tentativi FROM _par), 2),
                                        (SELECT blocco_minuti FROM _par)) f),
    '1|true',
    '1) riga nuova: un tentativo, nessun freno');

SELECT is(
    (SELECT f.tentativi || '|' || (f.bloccato_fino_a = now() + make_interval(mins => (SELECT blocco_minuti FROM _par)))
       FROM script.fn_login_freno_passo((SELECT max_tentativi FROM _par) - 1, NULL, now(),
                                        (SELECT max_tentativi FROM _par),
                                        (SELECT blocco_minuti FROM _par)) f),
    (SELECT max_tentativi FROM _par) || '|true',
    '2) alla soglia: freno fino ad adesso + blocco_minuti');

SELECT is(
    (SELECT f.tentativi
       FROM script.fn_login_freno_passo((SELECT max_tentativi FROM _par), now() - interval '1 second', now(),
                                        (SELECT max_tentativi FROM _par),
                                        (SELECT blocco_minuti FROM _par)) f),
    1,
    '3) un freno scaduto riparte da uno');

SELECT is(
    (SELECT f.tentativi || '|' || (f.bloccato_fino_a = now() + make_interval(mins => (SELECT blocco_minuti FROM _par)))
       FROM script.fn_login_freno_passo((SELECT max_tentativi FROM _par), now() + interval '1 minute', now(),
                                        (SELECT max_tentativi FROM _par),
                                        (SELECT blocco_minuti FROM _par)) f),
    ((SELECT max_tentativi FROM _par) + 1) || '|true',
    '4) un fallimento durante il freno lo rinnova');

-- ============================================================
-- 5-8 Il nome inesistente conta
-- ============================================================
SELECT is(
    (script.fn_registra_tentativo_login(NULL, (SELECT freno FROM _n), '203.0.113.71'::inet, false) ->> 'tentativi')::integer,
    1,
    '5) un fallimento su un nome inesistente CONTA (prima non contava)');

SELECT is(
    (SELECT fallimenti_consecutivi FROM config.nomi_tentati WHERE nome_digest = (SELECT freno FROM _n)),
    1,
    '6) ...su config.nomi_tentati, per digest');

SELECT is(
    (SELECT count(*) FROM config.credenziali),
    (SELECT n FROM _cred_prima),
    '7) ...e nessuna riga in config.credenziali');

SELECT is(
    (SELECT (nt.cleanup_at IS NOT NULL) || '|' || bool_and(p.cleanup_at IS NOT NULL)
       FROM config.nomi_tentati nt
       JOIN config.nomi_tentati_provenienze p ON p.nome_tentato_id = nt.id
      WHERE nt.nome_digest = (SELECT freno FROM _n)
      GROUP BY nt.cleanup_at),
    'true|true',
    '8) le righe del nome nascono con la scadenza (le due tabelle)');

-- ============================================================
-- 9 ⭐ La parita': stessa sequenza, stessa risposta
-- ============================================================
CREATE TEMP TABLE _seq (passo integer, chiave text, esito text);

DO $$
DECLARE
    v_esito text;
BEGIN
    FOR i IN 1 .. (SELECT max_tentativi FROM _par) LOOP
        INSERT INTO _seq VALUES
            (i, 'credenziale',
             script.fn_registra_tentativo_login((SELECT parita FROM _c), sha256('ignorato'::bytea),
                                                '203.0.113.72'::inet, false)::text),
            (i, 'nome',
             script.fn_registra_tentativo_login(NULL, (SELECT parita FROM _n),
                                                '203.0.113.72'::inet, false)::text);
    END LOOP;

    -- Il check alla soglia: codice e messaggio del rifiuto.
    BEGIN
        PERFORM script.fn_check_blocco_login((SELECT parita FROM _c), sha256('ignorato'::bytea), '203.0.113.72'::inet);
        v_esito := 'passa';
    EXCEPTION WHEN OTHERS THEN
        v_esito := SQLSTATE || ' ' || SQLERRM;
    END;
    INSERT INTO _seq VALUES (0, 'credenziale', v_esito);

    BEGIN
        PERFORM script.fn_check_blocco_login(NULL, (SELECT parita FROM _n), '203.0.113.72'::inet);
        v_esito := 'passa';
    EXCEPTION WHEN OTHERS THEN
        v_esito := SQLSTATE || ' ' || SQLERRM;
    END;
    INSERT INTO _seq VALUES (0, 'nome', v_esito);
END $$;

SELECT is(
    (SELECT string_agg(esito, ' ; ' ORDER BY passo) FROM _seq WHERE chiave = 'nome'),
    (SELECT string_agg(esito, ' ; ' ORDER BY passo) FROM _seq WHERE chiave = 'credenziale'),
    '9) stessa sequenza su credenziale vera e nome inesistente: stessi ritorni, stesso rifiuto alla soglia');

-- ============================================================
-- 10-12 Il freno e l'attesa del nome
-- ============================================================
DO $$
BEGIN
    FOR i IN 2 .. (SELECT max_tentativi FROM _par) LOOP
        PERFORM script.fn_registra_tentativo_login(NULL, (SELECT freno FROM _n), '203.0.113.71'::inet, false);
    END LOOP;
END $$;

SELECT throws_matching(
    $$ SELECT script.fn_check_blocco_login(NULL, (SELECT freno FROM _n), '203.0.113.71'::inet) $$,
    'da questa postazione: riprovare fra [0-9]+ minuti',
    '10) alla soglia da P1: il check del nome solleva E_UTENTE_BLOCCATO, con i minuti');

SELECT lives_ok(
    $$ SELECT script.fn_check_blocco_login(NULL, (SELECT freno FROM _n), '203.0.113.79'::inet) $$,
    '11) stesso nome da P2: passa — il freno e'' della coppia');

DO $$
BEGIN
    FOR i IN 1 .. (SELECT tetto_credenziale FROM _par) LOOP
        PERFORM script.fn_registra_tentativo_login(NULL, (SELECT attesa FROM _n), ('198.51.100.' || i)::inet, false);
    END LOOP;
END $$;

SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login(NULL, (SELECT attesa FROM _n), '192.0.2.71'::inet) $$,
    '%Troppi tentativi non riusciti: riprovare fra %secondi%',
    '12) al tetto da provenienze tutte diverse: E_LOGIN_ATTESA anche per un nome inesistente');

-- ============================================================
-- 13-16 Chiamate non valide, e il nome mai provato
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login(NULL, substring(sha256('x'::bytea) from 1 for 31), '192.0.2.72'::inet) $$,
    '%Chiamata non valida a script.fn_check_blocco_login%',
    '13) digest di 31 byte -> E_AUTH_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login(NULL, NULL, '192.0.2.72'::inet) $$,
    '%Chiamata non valida a script.fn_check_blocco_login%',
    '14) digest NULL -> E_AUTH_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    $$ SELECT script.fn_registra_tentativo_login(NULL, (SELECT mai FROM _n), '192.0.2.72'::inet, true) $$,
    '%Chiamata non valida a script.fn_registra_tentativo_login%',
    '15) un SUCCESSO senza credenziale -> E_AUTH_CHIAMATA_NON_VALIDA (un nome inesistente non entra)');

SELECT lives_ok(
    $$ SELECT script.fn_check_blocco_login(NULL, (SELECT mai FROM _n), '192.0.2.72'::inet) $$,
    '16) nome inesistente mai provato: il check passa');

SELECT * FROM finish();
ROLLBACK;
