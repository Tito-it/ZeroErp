-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_sync_auth_user_is_active (§7.1.2 WIP
-- multi-face-auth, post-cutover §13.3.4).
--
-- La funzione post-cutover legge SOLO da identita_digitali (niente
-- fallback legacy su risorse_umane_auth_user, niente doppia verifica
-- OPERATORE). Deve gestire correttamente i 5 ruoli applicativi
-- OPERATORE / CLIENTE_PORTALE / FORNITORE_PORTALE / SHOP_CUSTOMER
-- (API_CLIENT escluso: non ha corrispondente auth_user nel modello
-- attuale).
-- ⚠️ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): DISABILITATO
-- non e' piu' un tipo di veste. Una veste si spegne con attivo = false
-- e tiene il tipo; la tabella viva rifiuta DISABILITATO. Il test 9, che
-- spegneva la veste cambiandone il tipo, ora prova il rifiuto.
--
-- Il test esistente test-sync-auth-user-is-active.sql copre OPERATORE
-- regression via RUA legacy (ora vista); questo file copre i 4 ruoli
-- nuovi + edge case guard/orfano.
--
-- Semantica attesa:
--   - NULL / <=0 p_auth_user_id -> raise E_PARAMETRO_INVALIDO
--   - Utente senza identita -> return false (no modifica auth_user)
--   - veste attiva con finestra valida + soggetto attivo ->
--     should_active = true
--   - veste con attivo=false -> should_active = false
--   - veste fuori finestra (valido_al < script.fn_data_operativa()) ->
--     should_active = false
--   - DISABILITATO non si scrive: E_RUOLO_APPLICATIVO_RITIRATO
--
-- Indice test (1..10):
--    1. Guard: p_auth_user_id NULL -> raise
--    2. Guard: p_auth_user_id = 0 -> raise
--    3. Utente orfano (nessuna identita) -> return false
--    4. CLIENTE_PORTALE attiva + soggetto attivo -> auth_user.is_active=true
--    5. CLIENTE_PORTALE con identita attivo=false -> auth_user.is_active=false
--    6. CLIENTE_PORTALE fuori finestra temporale -> auth_user.is_active=false
--    7. FORNITORE_PORTALE attiva -> auth_user.is_active=true
--    8. SHOP_CUSTOMER attiva -> auth_user.is_active=true
--    9. Cambio ruolo_applicativo a DISABILITATO -> rifiutato
--       (E_RUOLO_APPLICATIVO_RITIRATO, rev 2026-10-02)
--   10. Identita riattivata dopo disabilitazione -> auth_user.is_active=true
--
-- BEGIN; + ROLLBACK a fine file (isolamento completo).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- =========================================================
-- 1) Guard: p_auth_user_id NULL -> raise E_PARAMETRO_INVALIDO
-- =========================================================
SELECT throws_ok(
    $$ SELECT anagrafiche.fn_sync_auth_user_is_active(NULL::integer) $$,
    NULL,
    NULL,
    '1. Guard: auth_user_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 2) Guard: p_auth_user_id = 0 -> raise E_PARAMETRO_INVALIDO
-- =========================================================
SELECT throws_ok(
    $$ SELECT anagrafiche.fn_sync_auth_user_is_active(0::integer) $$,
    NULL,
    NULL,
    '2. Guard: auth_user_id <= 0 -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 3) Utente orfano (auth_user esiste ma nessuna identita) -> false
-- =========================================================
DO $pgtap$
DECLARE
    v_au int;
BEGIN
    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_sync_orfano_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au;

    CREATE TEMP TABLE _t_au_orfano (au_id int);
    INSERT INTO _t_au_orfano VALUES (v_au);
END
$pgtap$;

SELECT ok(
    anagrafiche.fn_sync_auth_user_is_active(
        (SELECT au_id FROM _t_au_orfano)
    ) = false,
    '3. Utente orfano (nessuna identita) -> return false (no-op)'
);

-- =========================================================
-- Setup casi 4..10: 3 auth_user distinti + 3 SR diversi (CL/FO/CL
-- per SHOP) per rispettare uq_identita_digitali_soggetto_ruolo_attivo.
-- =========================================================
CREATE TEMP TABLE _t_setup (
    case_cli_au       int,      -- CLIENTE_PORTALE auth_user
    case_cli_sr       bigint,   -- SR cliente
    case_cli_id_id    bigint,   -- identita id
    case_cli_ready    boolean DEFAULT false,
    case_forn_au      int,      -- FORNITORE_PORTALE
    case_forn_sr      bigint,
    case_forn_id_id   bigint,
    case_forn_ready   boolean DEFAULT false,
    case_shop_au      int,      -- SHOP_CUSTOMER
    case_shop_sr      bigint,
    case_shop_id_id   bigint,
    case_shop_ready   boolean DEFAULT false
);
INSERT INTO _t_setup DEFAULT VALUES;

-- Setup CLIENTE_PORTALE
DO $pgtap$
DECLARE
    v_sr bigint; v_au int; v_id bigint;
BEGIN
    -- SR cliente con soggetto attivo, senza identita attiva
    SELECT c.soggetto_ruolo_id INTO v_sr
      FROM anagrafiche.clienti c
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
     WHERE s.attivo = true
       AND NOT EXISTS (
           SELECT 1 FROM anagrafiche.identita_digitali id
            WHERE id.soggetto_ruolo_id = c.soggetto_ruolo_id
              AND id.attivo = true
       )
     ORDER BY c.soggetto_ruolo_id
     LIMIT 1;

    IF v_sr IS NULL THEN RETURN; END IF;

    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_sync_cli_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au;

    v_id := anagrafiche.fn_crea_veste_portale(v_au, v_sr, 'CLIENTE_PORTALE', true);

    UPDATE _t_setup
       SET case_cli_au = v_au, case_cli_sr = v_sr,
           case_cli_id_id = v_id, case_cli_ready = true;
END
$pgtap$;

-- Setup FORNITORE_PORTALE
DO $pgtap$
DECLARE
    v_sr bigint; v_au int; v_id bigint;
BEGIN
    SELECT f.soggetto_ruolo_id INTO v_sr
      FROM anagrafiche.fornitori f
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.soggetto_ruolo_id
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
     WHERE s.attivo = true
       AND NOT EXISTS (
           SELECT 1 FROM anagrafiche.identita_digitali id
            WHERE id.soggetto_ruolo_id = f.soggetto_ruolo_id
              AND id.attivo = true
       )
     ORDER BY f.soggetto_ruolo_id
     LIMIT 1;

    IF v_sr IS NULL THEN RETURN; END IF;

    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_sync_forn_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au;

    v_id := anagrafiche.fn_crea_veste_portale(v_au, v_sr, 'FORNITORE_PORTALE', true);

    UPDATE _t_setup
       SET case_forn_au = v_au, case_forn_sr = v_sr,
           case_forn_id_id = v_id, case_forn_ready = true;
END
$pgtap$;

-- Setup SHOP_CUSTOMER (SR cliente diverso da quello del caso CLIENTE_PORTALE)
DO $pgtap$
DECLARE
    v_sr bigint; v_au int; v_id bigint;
    v_sr_cli bigint;
BEGIN
    SELECT case_cli_sr INTO v_sr_cli FROM _t_setup;

    SELECT c.soggetto_ruolo_id INTO v_sr
      FROM anagrafiche.clienti c
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
     WHERE s.attivo = true
       AND c.soggetto_ruolo_id <> COALESCE(v_sr_cli, 0::bigint)
       AND NOT EXISTS (
           SELECT 1 FROM anagrafiche.identita_digitali id
            WHERE id.soggetto_ruolo_id = c.soggetto_ruolo_id
              AND id.attivo = true
       )
     ORDER BY c.soggetto_ruolo_id
     LIMIT 1;

    IF v_sr IS NULL THEN RETURN; END IF;

    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_sync_shop_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au;

    v_id := anagrafiche.fn_crea_veste_portale(v_au, v_sr, 'SHOP_CUSTOMER', true);

    UPDATE _t_setup
       SET case_shop_au = v_au, case_shop_sr = v_sr,
           case_shop_id_id = v_id, case_shop_ready = true;
END
$pgtap$;

-- =========================================================
-- NOTA sulle asserzioni 4..10
-- =========================================================
-- Verifichiamo solo lo STATO FINALE di auth_user.is_active dopo la
-- chiamata a fn_sync_auth_user_is_active. Il valore di ritorno della
-- funzione (bool "ha modificato") e' un dettaglio implementativo che
-- dipende dallo stato precedente: se auth_user era gia' al valore
-- atteso, la funzione ritorna false (no-op legittimo). L'invariante
-- semantica che testiamo e' "post-sync, auth_user.is_active riflette
-- lo stato dell'identita".

-- =========================================================
-- 4) CLIENTE_PORTALE attiva + soggetto attivo -> auth_user.is_active=true
-- =========================================================
UPDATE django.auth_user SET is_active = false
 WHERE id = (SELECT case_cli_au FROM _t_setup WHERE case_cli_ready);

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT case_cli_au FROM _t_setup WHERE case_cli_ready)
)
 WHERE (SELECT case_cli_ready FROM _t_setup);

SELECT CASE
    WHEN (SELECT case_cli_ready FROM _t_setup)
    THEN ok(
        (SELECT is_active FROM django.auth_user
          WHERE id = (SELECT case_cli_au FROM _t_setup)) = true,
        '4. CLIENTE_PORTALE attiva + soggetto attivo -> auth_user.is_active=true'
    )
    ELSE skip('Nessun cliente libero: test 4 skippato', 1)
END;

-- =========================================================
-- 5) CLIENTE_PORTALE con identita attivo=false -> auth_user.is_active=false
-- =========================================================
UPDATE anagrafiche.identita_digitali SET attivo = false
 WHERE id = (SELECT case_cli_id_id FROM _t_setup WHERE case_cli_ready);

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT case_cli_au FROM _t_setup WHERE case_cli_ready)
)
 WHERE (SELECT case_cli_ready FROM _t_setup);

SELECT CASE
    WHEN (SELECT case_cli_ready FROM _t_setup)
    THEN ok(
        (SELECT is_active FROM django.auth_user
          WHERE id = (SELECT case_cli_au FROM _t_setup)) = false,
        '5. CLIENTE_PORTALE con identita.attivo=false -> auth_user.is_active=false'
    )
    ELSE skip('Setup 4 non ready: test 5 skippato', 1)
END;

-- =========================================================
-- 6) CLIENTE_PORTALE fuori finestra (valido_al < script.fn_data_operativa()) -> is_active=false
-- =========================================================
-- Sposto sia valido_dal sia valido_al nel passato per rispettare il
-- vincolo chk_identita_digitali_date (valido_dal <= valido_al).
UPDATE anagrafiche.identita_digitali
   SET attivo = true,
       valido_dal = script.fn_data_operativa() - INTERVAL '2 days',
       valido_al  = script.fn_data_operativa() - INTERVAL '1 day'
 WHERE id = (SELECT case_cli_id_id FROM _t_setup WHERE case_cli_ready);

UPDATE django.auth_user SET is_active = true
 WHERE id = (SELECT case_cli_au FROM _t_setup WHERE case_cli_ready);

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT case_cli_au FROM _t_setup WHERE case_cli_ready)
)
 WHERE (SELECT case_cli_ready FROM _t_setup);

SELECT CASE
    WHEN (SELECT case_cli_ready FROM _t_setup)
    THEN ok(
        (SELECT is_active FROM django.auth_user
          WHERE id = (SELECT case_cli_au FROM _t_setup)) = false,
        '6. CLIENTE_PORTALE fuori finestra temporale (valido_al ieri) -> auth_user.is_active=false'
    )
    ELSE skip('Setup non ready: test 6 skippato', 1)
END;

-- Reset finestra per i test successivi (CLIENTE_PORTALE torna aperto).
UPDATE anagrafiche.identita_digitali
   SET valido_dal = script.fn_data_operativa(),
       valido_al  = NULL
 WHERE id = (SELECT case_cli_id_id FROM _t_setup WHERE case_cli_ready);

-- =========================================================
-- 7) FORNITORE_PORTALE attiva -> auth_user.is_active=true
-- =========================================================
UPDATE django.auth_user SET is_active = false
 WHERE id = (SELECT case_forn_au FROM _t_setup WHERE case_forn_ready);

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT case_forn_au FROM _t_setup WHERE case_forn_ready)
)
 WHERE (SELECT case_forn_ready FROM _t_setup);

SELECT CASE
    WHEN (SELECT case_forn_ready FROM _t_setup)
    THEN ok(
        (SELECT is_active FROM django.auth_user
          WHERE id = (SELECT case_forn_au FROM _t_setup)) = true,
        '7. FORNITORE_PORTALE attiva -> auth_user.is_active=true'
    )
    ELSE skip('Nessun fornitore libero: test 7 skippato', 1)
END;

-- =========================================================
-- 8) SHOP_CUSTOMER attiva -> auth_user.is_active=true
-- =========================================================
UPDATE django.auth_user SET is_active = false
 WHERE id = (SELECT case_shop_au FROM _t_setup WHERE case_shop_ready);

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT case_shop_au FROM _t_setup WHERE case_shop_ready)
)
 WHERE (SELECT case_shop_ready FROM _t_setup);

SELECT CASE
    WHEN (SELECT case_shop_ready FROM _t_setup)
    THEN ok(
        (SELECT is_active FROM django.auth_user
          WHERE id = (SELECT case_shop_au FROM _t_setup)) = true,
        '8. SHOP_CUSTOMER attiva -> auth_user.is_active=true'
    )
    ELSE skip('Nessun secondo cliente libero: test 8 skippato', 1)
END;

-- =========================================================
-- 9) Cambio ruolo_applicativo a DISABILITATO -> rifiutato
--    (rev 2026-10-02, R-DB-1): spegnere una veste e' attivo = false,
--    il tipo resta. Il guard di coerenza parla prima del CHECK
--    chk_identita_digitali_ruolo_non_ritirato; il codice viaggia nel
--    canale CONSTRAINT_NAME dell'eccezione P0001.
-- =========================================================

SELECT CASE
    WHEN (SELECT case_cli_ready FROM _t_setup)
    THEN is(
        dbops.fn_pgtap_codice_errore(format(
            $$UPDATE anagrafiche.identita_digitali
                 SET ruolo_applicativo = 'DISABILITATO'::config.ruolo_applicativo
               WHERE id = %s$$,
            (SELECT case_cli_id_id FROM _t_setup))),
        'E_RUOLO_APPLICATIVO_RITIRATO',
        '9. ruolo_applicativo=DISABILITATO -> rifiutato (E_RUOLO_APPLICATIVO_RITIRATO)'
    )
    ELSE skip('Setup non ready: test 9 skippato', 1)
END;

-- =========================================================
-- 10) Riattivazione: ruolo -> CLIENTE_PORTALE + attivo=true -> is_active=true
-- =========================================================
UPDATE anagrafiche.identita_digitali
   SET ruolo_applicativo = 'CLIENTE_PORTALE'::config.ruolo_applicativo,
       attivo = true
 WHERE id = (SELECT case_cli_id_id FROM _t_setup WHERE case_cli_ready);

UPDATE django.auth_user SET is_active = false
 WHERE id = (SELECT case_cli_au FROM _t_setup WHERE case_cli_ready);

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT case_cli_au FROM _t_setup WHERE case_cli_ready)
)
 WHERE (SELECT case_cli_ready FROM _t_setup);

SELECT CASE
    WHEN (SELECT case_cli_ready FROM _t_setup)
    THEN ok(
        (SELECT is_active FROM django.auth_user
          WHERE id = (SELECT case_cli_au FROM _t_setup)) = true,
        '10. Riattivazione ruolo CLIENTE_PORTALE + attivo=true -> auth_user.is_active=true'
    )
    ELSE skip('Setup non ready: test 10 skippato', 1)
END;

SELECT * FROM finish();
ROLLBACK;
