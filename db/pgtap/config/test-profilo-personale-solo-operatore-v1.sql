-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un profilo personale (AD_HOC, SUPER_ADMIN) si lega solo a una veste
--       OPERATORE, in tutti e due i versi: il legame nuovo e la veste che
--       cambia tipo col legame addosso (E_PROFILO_PERSONALE_SOLO_OPERATORE)
-- ChangeSet: 20261127-49 (config.trgfn_profili_accesso_bindings_guard_coerenza),
--            20261127-50 (anagrafiche.trgfn_identita_digitali_guard_coerenza)
-- Brief: brief-db-accessi-area-clienti, giro 4 (D-G4-2)
--
-- Perche' la regola: i profili si raccolgono per credenziale e tipo di veste
-- (script.fn_get_profili_accesso_applicabili), e sui portali una persona ha
-- una veste per soggetto (20261127-48). Un profilo personale su una di loro
-- varrebbe per tutte.
--
-- Gira come l'applicazione, nel contesto di un SUPER_ADMIN costruito: i legami
-- li scrive il verbo config.fn_lega_profilo_identita, la strada vera dell'app
-- (le tabelle dei legami sono in sola lettura per lei). La veste che cambia
-- tipo la scrive la fixture dbops.fn_pgtap_imposta_veste: l'app non ha UPDATE
-- su identita_digitali, e il guard vale per ogni strada.
--
-- ⚠️ Non costruito qui: il legame SPENTO su una veste dei portali. Il verbo lo
--   crea acceso e l'app non scrive la tabella; il ramo che lo copre e' lo stesso
--   del legame acceso (il guard non legge `attivo`), e il verso opposto lo
--   prova il caso 6 con un legame acceso.
--
-- Elenco test (plan 6):
--    1) AD_HOC su una veste CLIENTE_PORTALE: E_PROFILO_PERSONALE_SOLO_OPERATORE
--    2) SUPER_ADMIN su una veste FORNITORE_PORTALE: lo stesso codice
--    3) AD_HOC su una veste SHOP_CUSTOMER spenta: lo stesso codice, la veste
--       spenta non cambia la regola
--    4) AD_HOC su una veste OPERATORE: il legame nasce
--    5) la frase: tipo del profilo e tipo della veste
--    6) la veste OPERATORE col legame AD_HOC che diventa CLIENTE_PORTALE: lo
--       stesso codice, dal guard della veste
-- ------------------------------------------------------------
BEGIN;

-- Il mondo prima del contesto: un operatore che ricevera' il profilo.
CREATE TEMP TABLE _op AS
SELECT o.auth_user_id, o.identita_id
  FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP g4 profilo personale') o;

CREATE TEMP TABLE _sa AS
SELECT o.auth_user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('g4-profilo-personale', true) o;

-- Il cliente e il fornitore nascono nel contesto di un operatore che lavora
-- dentro un emittente: il super admin «tutti gli emittenti» non crea clienti.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _sr AS
SELECT (SELECT c.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_cliente_ba('g4-profilo-cli') c) AS cli,
       dbops.fn_pgtap_crea_soggetto_ruolo(dbops.fn_pgtap_crea_soggetto_pg('pgTAP g4 profilo fornitore'), 'FO') AS fo;
SET CONSTRAINTS ALL IMMEDIATE;

-- Una credenziale nuda con tre vesti dei portali: due accese, una spenta.
CREATE TEMP TABLE _v (nome text PRIMARY KEY, identita_id bigint);
DO $$
DECLARE
    v_auth integer;  -- ⚠️ niente %TYPE su django.*
    v_id   anagrafiche.identita_digitali.id%TYPE;
    v_r    record;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_g4_profilo_' || substring(md5(clock_timestamp()::text) FROM 1 FOR 8),
            '!', false, false, false, '', '', '', now())
    RETURNING id INTO v_auth;

    FOR v_r IN
        SELECT * FROM (VALUES ('cliente',   (SELECT cli FROM _sr), 'CLIENTE_PORTALE',   true),
                              ('fornitore', (SELECT fo  FROM _sr), 'FORNITORE_PORTALE', true),
                              ('shop',      (SELECT cli FROM _sr), 'SHOP_CUSTOMER',     false)) x(nome, sr, ruolo, accesa)
    LOOP
        INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (v_r.sr, v_auth, v_r.ruolo::config.ruolo_applicativo, false)
        RETURNING id INTO v_id;
        IF v_r.accesa THEN
            PERFORM dbops.fn_pgtap_imposta_veste(v_id, jsonb_build_object('attivo', true));
        END IF;
        INSERT INTO _v VALUES (v_r.nome, v_id);
    END LOOP;
END $$;

-- Da qui il contesto e' il SUPER_ADMIN costruito: i verbi dei profili e dei
-- legami lo chiedono.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $ctx$;

-- Un profilo AD_HOC costruito, e il SUPER_ADMIN del catalogo.
CREATE TEMP TABLE _p AS
SELECT config.fn_scrivi_profilo_accesso('AD_HOC'::config.tipo_profilo_accesso,
           'PGTAP_G4_ADH_' || k, 'Profilo pgTAP personale', '[]'::jsonb, '[]'::jsonb, '{}'::jsonb) AS adh,
       (SELECT pa.id FROM config.profili_accesso pa WHERE pa.codice = 'SUPER_ADMIN') AS sa
  FROM (SELECT replace(gen_random_uuid()::text, '-', '') AS k) x;

-- ============================================================
-- 1-4 Il legame nuovo
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format('SELECT config.fn_lega_profilo_identita(%s, %s)',
        (SELECT adh FROM _p), (SELECT identita_id FROM _v WHERE nome = 'cliente'))),
    'E_PROFILO_PERSONALE_SOLO_OPERATORE',
    '1) un profilo AD_HOC su una veste CLIENTE_PORTALE si ferma');

SELECT is(
    dbops.fn_pgtap_codice_errore(format('SELECT config.fn_lega_profilo_identita(%s, %s)',
        (SELECT sa FROM _p), (SELECT identita_id FROM _v WHERE nome = 'fornitore'))),
    'E_PROFILO_PERSONALE_SOLO_OPERATORE',
    '2) il profilo SUPER_ADMIN su una veste FORNITORE_PORTALE si ferma');

SELECT is(
    dbops.fn_pgtap_codice_errore(format('SELECT config.fn_lega_profilo_identita(%s, %s)',
        (SELECT adh FROM _p), (SELECT identita_id FROM _v WHERE nome = 'shop'))),
    'E_PROFILO_PERSONALE_SOLO_OPERATORE',
    '3) un profilo AD_HOC su una veste SHOP_CUSTOMER spenta si ferma: la veste spenta non cambia la regola');

CREATE TEMP TABLE _l AS
SELECT config.fn_lega_profilo_identita((SELECT adh FROM _p), (SELECT identita_id FROM _op)) AS binding_id;

SELECT ok(
    EXISTS (SELECT 1
              FROM config.profili_accesso_bindings pab
             WHERE pab.id = (SELECT binding_id FROM _l)
               AND pab.identita_digitale_id = (SELECT identita_id FROM _op)
               AND pab.profilo_accesso_id = (SELECT adh FROM _p)),
    '4) un profilo AD_HOC su una veste OPERATORE: il legame nasce');

-- ============================================================
-- 5 La frase
-- ============================================================
SELECT throws_like(
    format('SELECT config.fn_lega_profilo_identita(%s, %s)',
           (SELECT adh FROM _p), (SELECT identita_id FROM _v WHERE nome = 'cliente')),
    '%profilo AD_HOC si assegna solo a un operatore, non a una veste CLIENTE_PORTALE%',
    '5) la frase dice il tipo del profilo e il tipo della veste');

-- ============================================================
-- 6 Il verso opposto: la veste che cambia tipo
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT dbops.fn_pgtap_imposta_veste(%s, jsonb_build_object('ruolo_applicativo', 'CLIENTE_PORTALE',
                                                                     'soggetto_ruolo_id', %s))$$,
        (SELECT identita_id FROM _op), (SELECT cli FROM _sr))),
    'E_PROFILO_PERSONALE_SOLO_OPERATORE',
    '6) la veste OPERATORE col profilo AD_HOC che diventa CLIENTE_PORTALE si ferma, dal guard della veste');

SELECT * FROM finish();
ROLLBACK;
