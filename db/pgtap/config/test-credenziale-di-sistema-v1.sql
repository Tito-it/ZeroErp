-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: I VERBI DELL'AMMINISTRATORE SU UNA CREDENZIALE DI SISTEMA, e il motivo
--   del blocco che viene dal DB.
--   Brief: brief-db-credenziale-verbi-amministratore, R-DB-A5 + R-DB-A6
--   (decisioni di Tid del 2026-10-03: D-1 uscita dal server, D-2 le uscite
--   restano aperte, D-3 classe CONFLITTO_STATO).
--   ChangeSet: 20_code/script/20261003-01 (fn_check_credenziale_bloccabile),
--   -02 (fn_blocca_credenziale chiama la check), -03 (fn_imposta_totp_obbligatorio).
--
-- ⭐ I soggetti si COSTRUISCONO: la credenziale di sistema e' l'operatore di
--   dbops.fn_pgtap_crea_emittente_operatore (un utente TECNICO, quindi categoria
--   SISTEMA); il SUPER_ADMIN e l'operatore senza privilegi sono umani
--   (dbops.fn_pgtap_crea_operatore_umano); la credenziale qualunque nasce in
--   django.auth_user senza vesti (categoria ALTRO).
--
-- Elenco test (plan 16):
--   La check (R-DB-A5)
--    1) credenziale di sistema -> un motivo, CREDENZIALE_DI_SISTEMA, con codice e chiave
--    2) credenziale qualunque -> '[]'
--    3) id non valido -> E_AUTH_CHIAMATA_NON_VALIDA
--    4) ⭐ la madre CHIAMA la check e non contiene il predicato (§12.5.2)
--   Il blocco (R-DB-A6)
--    5) chi non e' SUPER_ADMIN e' rifiutato per il permesso, prima della natura
--    6) SUPER_ADMIN blocca una credenziale di sistema -> E_CREDENZIALE_DI_SISTEMA
--    7) ...e la riga non porta nessun blocco
--    8) lo sblocco resta aperto (l'uscita): nessun rifiuto
--   Il secondo fattore (R-DB-A6, D-2)
--    9) accendere l'obbligo su una credenziale di sistema -> E_CREDENZIALE_DI_SISTEMA
--   10) ...e l'obbligo resta spento
--   11) spegnere l'obbligo passa (l'uscita)
--   12) su una credenziale qualunque accenderlo passa ancora
--   13) cancellare il device di una credenziale di sistema passa (il rimedio)
--   L'ultimo SUPER_ADMIN (cambia i binding: in fondo)
--   14) la check sull'ultimo SUPER_ADMIN -> ULTIMO_SUPER_ADMIN, chiave di sempre
--   15) la madre solleva quel motivo -> E_PROFILO_ULTIMO_SUPER_ADMIN
--   16) un'altra credenziale resta bloccabile: '[]'
--
-- ⚠️ Gira come l'APPLICAZIONE: i verbi sono DEFINER e leggono chi agisce dalla
--   GUC, come in esercizio. Il ramo della sessione del migratore (D-1) e' in
--   test-credenziale-di-sistema-migratore-v1.sql, col runner owner.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _sa  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-sistema', true);
CREATE TEMP TABLE _op  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP-sistema', false);
CREATE TEMP TABLE _tec AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                              first_name, last_name, email, date_joined)
VALUES ('_pgtap_qualunque_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now());
CREATE TEMP TABLE _t AS SELECT max(id) AS bersaglio FROM django.auth_user WHERE username LIKE '\_pgtap\_qualunque\_%';

-- Chi agisce: il contesto operatore su un utente dato.
CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

-- ============================================================
-- 1-4 La check
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s|%s', jsonb_array_length(m), m -> 0 ->> 'codice',
                   m -> 0 ->> 'reason', m -> 0 ->> 'reason_key')
       FROM (SELECT script.fn_check_credenziale_bloccabile((SELECT auth_user_id FROM _tec)) AS m) x),
    '1|E_CREDENZIALE_DI_SISTEMA|CREDENZIALE_DI_SISTEMA|amministrazione.accessi.blocca_reason.credenziale_di_sistema',
    '1) credenziale di sistema: un motivo, CREDENZIALE_DI_SISTEMA, con codice e chiave i18n');

SELECT is(
    script.fn_check_credenziale_bloccabile((SELECT bersaglio FROM _t)),
    '[]'::jsonb,
    '2) credenziale qualunque: nessun motivo');

SELECT throws_like(
    $$ SELECT script.fn_check_credenziale_bloccabile(0) $$,
    '%Chiamata non valida a%',
    '3) id non valido: E_AUTH_CHIAMATA_NON_VALIDA');

-- §12.5.2: non «gli esiti coincidono», ma «la madre non contiene il predicato».
SELECT is(
    (SELECT format('%s|%s|%s',
                   -- ::text: format('%s') su un boolean stampa t/f.
                   (s ~ 'fn_check_credenziale_bloccabile\s*\(')::text,
                   (s ~ 'fn_categoria_accesso')::text,
                   (s ~ 'fn_check_ultimo_super_admin_attivo')::text)
       FROM (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS s
               FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname = 'script' AND p.proname = 'fn_blocca_credenziale') x),
    'true|false|false',
    '4) fn_blocca_credenziale chiama la check e non riscrive le sue regole');

-- ============================================================
-- 5-8 Il blocco
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _op));
SELECT throws_like(
    $$ SELECT script.fn_blocca_credenziale((SELECT auth_user_id FROM _tec), 'prova') $$,
    '%Non hai i permessi per questa operazione%',
    '5) chi non e'' SUPER_ADMIN: E_PERMESSO_NEGATO, prima della natura della credenziale');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT throws_like(
    $$ SELECT script.fn_blocca_credenziale((SELECT auth_user_id FROM _tec), 'chiave sospetta') $$,
    '%Le credenziali di sistema non si modificano da qui%',
    '6) SUPER_ADMIN su una credenziale di sistema: E_CREDENZIALE_DI_SISTEMA');

SELECT is(
    (SELECT count(*)::int FROM config.credenziali c
      WHERE c.auth_user_id = (SELECT auth_user_id FROM _tec) AND c.bloccata_at IS NOT NULL),
    0,
    '7) ...e la credenziale non e'' bloccata');

SELECT lives_ok(
    $$ SELECT script.fn_sblocca_credenziale((SELECT auth_user_id FROM _tec)) $$,
    '8) lo sblocco di una credenziale di sistema resta aperto (l''uscita)');

-- ============================================================
-- 9-13 Il secondo fattore
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_imposta_totp_obbligatorio((SELECT auth_user_id FROM _tec), true) $$,
    '%Le credenziali di sistema non si modificano da qui%',
    '9) accendere l''obbligo su una credenziale di sistema: E_CREDENZIALE_DI_SISTEMA');

SELECT is(
    (SELECT COALESCE(bool_or(c.totp_obbligatorio), false) FROM config.credenziali c
      WHERE c.auth_user_id = (SELECT auth_user_id FROM _tec)),
    false,
    '10) ...e l''obbligo resta spento');

SELECT lives_ok(
    $$ SELECT script.fn_imposta_totp_obbligatorio((SELECT auth_user_id FROM _tec), false) $$,
    '11) spegnere l''obbligo su una credenziale di sistema passa (D-2: l''uscita)');

SELECT lives_ok(
    $$ SELECT script.fn_imposta_totp_obbligatorio((SELECT bersaglio FROM _t), true) $$,
    '12) su una credenziale qualunque accendere l''obbligo passa ancora');

-- Il device di una macchina esiste solo per errore: lo registra la credenziale
-- stessa (ramo «utente stesso»), poi il SUPER_ADMIN lo toglie.
SELECT pg_temp.agisci((SELECT auth_user_id FROM _tec));
SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _tec), 'segreto-S', '["s1"]'::jsonb);
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT script.fn_totp_disabilita_device((SELECT auth_user_id FROM _tec), 'device registrato per errore');
SELECT is(
    (SELECT stato FROM script.fn_get_totp_device((SELECT auth_user_id FROM _tec))),
    'ASSENTE',
    '13) cancellare il device di una credenziale di sistema passa (D-2: il rimedio)');

-- ============================================================
-- 14-16 L'ultimo SUPER_ADMIN (cambia i binding: in fondo)
-- ============================================================
-- Spegne tutti i binding SUPER_ADMIN tranne quello del SA del test.
UPDATE config.profili_accesso_bindings pab
   SET attivo = false
  FROM config.profili_accesso pa
 WHERE pa.id = pab.profilo_accesso_id
   AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
   AND pab.attivo = true
   AND pab.identita_digitale_id <> (SELECT identita_id FROM _sa);

SELECT is(
    (SELECT format('%s|%s|%s|%s', jsonb_array_length(m), m -> 0 ->> 'codice',
                   m -> 0 ->> 'reason', m -> 0 ->> 'reason_key')
       FROM (SELECT script.fn_check_credenziale_bloccabile((SELECT auth_user_id FROM _sa)) AS m) x),
    '1|E_PROFILO_ULTIMO_SUPER_ADMIN|ULTIMO_SUPER_ADMIN|amministrazione.accessi.blocca_reason.ultimo_super_admin',
    '14) l''ultimo SUPER_ADMIN: ULTIMO_SUPER_ADMIN, con la chiave che il backend usava gia''');

-- Il CODICE dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error). Si pinna il codice, non la frase del
-- catalogo: la frase si riscrive (rev 2026-10-07, giro 2 di
-- brief-db-veste-utilizzabile, «attivo e senza data di fine»), il codice no.
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

SELECT is(
    pg_temp.codice_errore(
        $$ SELECT script.fn_blocca_credenziale((SELECT auth_user_id FROM _sa), 'prova su me stesso') $$),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '15) la madre solleva il primo motivo: E_PROFILO_ULTIMO_SUPER_ADMIN');

SELECT is(
    script.fn_check_credenziale_bloccabile((SELECT auth_user_id FROM _op)),
    '[]'::jsonb,
    '16) un operatore qualunque resta bloccabile anche con un solo SUPER_ADMIN');

SELECT * FROM finish();
ROLLBACK;
