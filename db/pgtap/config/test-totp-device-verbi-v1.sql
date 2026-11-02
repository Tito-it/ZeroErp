-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il CICLO DI VITA del device del secondo fattore (TOTP) — i verbi,
--   chi puo' cosa, l'anti-replay sul passo, il monouso dei codici di recupero.
--   Brief: brief-db-secondo-fattore-totp, sezioni 3 e 4.
--   ChangeSet: 00_schema/config/20260929-07 (forma del device),
--   20_code/script/20260929-14 (fn_guard_utente_stesso), -15 (fn_get_totp_device),
--   -16 (fn_check_totp_recovery_hash), -17 → -22 (i verbi).
--
-- ⭐ Il permesso si COSTRUISCE: un operatore umano senza privilegi (l'utente
--   del device), un SUPER_ADMIN umano e un operatore tecnico (un «altro» senza
--   privilegi). Chi agisce e' la GUC, come in esercizio.
--
-- Elenco test (plan 29):
--   Registrazione
--    1) chi agisce non e' la credenziale -> E_PERMESSO_NEGATO
--    2) nessun utente in sessione -> E_PERMESSO_NEGATO (fail-closed)
--    3) mazzo di codici vuoto -> E_AUTH_CHIAMATA_NON_VALIDA
--    4) mazzo con doppioni -> E_AUTH_CHIAMATA_NON_VALIDA
--    5) registrato: DA_CONFERMARE, segreto, tre codici
--    6) registrare di nuovo sostituisce il setup a meta' (segreto e codici nuovi)
--    7) l'uso su un device non confermato -> E_TOTP_DEVICE_ASSENTE
--   Conferma
--    8) chi agisce non e' la credenziale -> E_PERMESSO_NEGATO
--    9) passo negativo -> E_AUTH_CHIAMATA_NON_VALIDA
--   10) confermato: ATTIVO, il passo del primo codice e' registrato
--   11) confermare di nuovo -> E_TOTP_DEVICE_GIA_ATTIVO
--   12) registrare sopra un device attivo -> E_TOTP_DEVICE_GIA_ATTIVO
--   Anti-replay sul passo
--   13) lo stesso passo -> E_TOTP_PASSO_GIA_USATO
--   14) un passo piu' vecchio -> E_TOTP_PASSO_GIA_USATO
--   15) il passo successivo passa, e diventa l'ultimo
--   Codici di recupero
--   16) un hash che non c'e' -> E_TOTP_RECOVERY_NON_VALIDO
--   17) un hash del mazzo: consumato, restituisce quanti ne restano
--   18) lo stesso hash una seconda volta -> E_TOTP_RECOVERY_NON_VALIDO (monouso)
--   19) rigenerare da un altro -> E_PERMESSO_NEGATO
--   20) rigenerato: tre codici nuovi
--   21) un codice del mazzo vecchio non vale piu'
--   Disabilitazione
--   22) un SUPER_ADMIN senza motivo -> E_TOTP_MOTIVO_OBBLIGATORIO
--   23) un SUPER_ADMIN con motivo: la riga sparisce (ASSENTE, zero codici)
--   23b) ...e il verbo non scrive la traccia: dall'applicazione e' del backend (D-T3)
--   24) disabilitare un device che non c'e' -> E_TOTP_DEVICE_ASSENTE
--   25) un altro senza privilegi -> E_PERMESSO_NEGATO (chi agisce si decide
--       prima di cercare il device)
--   26) l'utente stesso disabilita senza motivo
--   Lettura
--   27) credenziale senza device: ASSENTE, niente segreto, zero codici
--   28) id non valido -> E_AUTH_CHIAMATA_NON_VALIDA
--
-- ⚠️ Gira come l'APPLICAZIONE. Il 23b e il 25 sono ROSSI DA OWNER per costruzione: il
--   runner owner e' il migratore, e la sessione del migratore e' il terzo
--   attore ammesso a disabilitare (il suo verso positivo sta in
--   test-totp-disabilita-migratore-v1.sql, runner owner). Sta dopo la
--   disabilitazione, sul device gia' sparito: da owner resta rosso senza
--   trascinare i test che seguono.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(29);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _u   AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-TOTP-utente', false);
CREATE TEMP TABLE _sa  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-TOTP-SA', true);
CREATE TEMP TABLE _tec AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Chi agisce: il contesto operatore su un utente dato.
CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

CREATE OR REPLACE FUNCTION pg_temp.device(p_auth_user_id integer) RETURNS text
LANGUAGE sql AS $$
    SELECT format('%s|%s|%s|%s', g.stato, COALESCE(g.secret_encrypted, 'NULL'),
                  COALESCE(g.ultimo_passo_usato::text, 'NULL'), g.recovery_rimasti)
      FROM script.fn_get_totp_device(p_auth_user_id) g;
$$;

-- ============================================================
-- 1-7 Registrazione
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _tec));
SELECT throws_like(
    $$ SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-A', '["a1","a2","a3"]'::jsonb) $$,
    '%Non hai i permessi per questa operazione%',
    '1) registrare il device di un altro: E_PERMESSO_NEGATO');

SELECT set_config('app.current_user_id', '', true);
SELECT throws_like(
    $$ SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-A', '["a1","a2","a3"]'::jsonb) $$,
    '%Non hai i permessi per questa operazione%',
    '2) nessun utente in sessione: E_PERMESSO_NEGATO (fail-closed)');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _u));
SELECT throws_like(
    $$ SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-A', '[]'::jsonb) $$,
    '%Chiamata non valida a%',
    '3) mazzo di codici di recupero vuoto: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    $$ SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-A', '["a1","a1"]'::jsonb) $$,
    '%Chiamata non valida a%',
    '4) mazzo con doppioni: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-A', '["a1","a2","a3"]'::jsonb);
SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'DA_CONFERMARE|segreto-A|NULL|3',
    '5) registrato: DA_CONFERMARE, col segreto e tre codici, nessun passo');

SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-B', '["b1","b2"]'::jsonb);
SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'DA_CONFERMARE|segreto-B|NULL|2',
    '6) registrare di nuovo sostituisce il setup a meta'': segreto e codici nuovi');

SELECT throws_like(
    $$ SELECT script.fn_totp_registra_uso((SELECT auth_user_id FROM _u), 1000) $$,
    '%Il secondo fattore non e'' attivo%',
    '7) l''uso su un device non confermato: E_TOTP_DEVICE_ASSENTE');

-- ============================================================
-- 8-12 Conferma
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _tec));
SELECT throws_like(
    $$ SELECT script.fn_totp_conferma_device((SELECT auth_user_id FROM _u), 1000) $$,
    '%Non hai i permessi per questa operazione%',
    '8) confermare il device di un altro: E_PERMESSO_NEGATO');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _u));
SELECT throws_like(
    $$ SELECT script.fn_totp_conferma_device((SELECT auth_user_id FROM _u), -1) $$,
    '%Chiamata non valida a%',
    '9) passo negativo: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT script.fn_totp_conferma_device((SELECT auth_user_id FROM _u), 1000);
SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'ATTIVO|segreto-B|1000|2',
    '10) confermato: ATTIVO, e il passo del primo codice e'' registrato');

SELECT throws_like(
    $$ SELECT script.fn_totp_conferma_device((SELECT auth_user_id FROM _u), 1001) $$,
    '%Il secondo fattore e'' gia'' attivo%',
    '11) confermare un device gia'' confermato: E_TOTP_DEVICE_GIA_ATTIVO');

SELECT throws_like(
    $$ SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-C', '["c1"]'::jsonb) $$,
    '%Il secondo fattore e'' gia'' attivo%',
    '12) registrare sopra un device attivo: E_TOTP_DEVICE_GIA_ATTIVO');

-- ============================================================
-- 13-15 Anti-replay sul passo (i verbi senza chi agisce: prima del login)
-- ============================================================
SELECT set_config('app.current_user_id', '', true);
SELECT throws_like(
    $$ SELECT script.fn_totp_registra_uso((SELECT auth_user_id FROM _u), 1000) $$,
    '%Codice gia'' usato%',
    '13) lo stesso passo della conferma: E_TOTP_PASSO_GIA_USATO');

SELECT throws_like(
    $$ SELECT script.fn_totp_registra_uso((SELECT auth_user_id FROM _u), 999) $$,
    '%Codice gia'' usato%',
    '14) un passo piu'' vecchio: E_TOTP_PASSO_GIA_USATO');

SELECT script.fn_totp_registra_uso((SELECT auth_user_id FROM _u), 1001);
SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'ATTIVO|segreto-B|1001|2',
    '15) il passo successivo passa, e diventa l''ultimo usato');

-- ============================================================
-- 16-21 Codici di recupero
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_totp_consuma_recovery((SELECT auth_user_id FROM _u), 'zz') $$,
    '%Codice di recupero non valido%',
    '16) un hash che non e'' nel mazzo: E_TOTP_RECOVERY_NON_VALIDO');

SELECT is(script.fn_totp_consuma_recovery((SELECT auth_user_id FROM _u), 'b2'), 1,
    '17) un hash del mazzo: consumato, ne resta uno');

SELECT throws_like(
    $$ SELECT script.fn_totp_consuma_recovery((SELECT auth_user_id FROM _u), 'b2') $$,
    '%Codice di recupero non valido%',
    '18) lo stesso hash una seconda volta: monouso');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _tec));
SELECT throws_like(
    $$ SELECT script.fn_totp_rigenera_recovery((SELECT auth_user_id FROM _u), '["r1","r2","r3"]'::jsonb) $$,
    '%Non hai i permessi per questa operazione%',
    '19) rigenerare i codici di un altro: E_PERMESSO_NEGATO');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _u));
SELECT script.fn_totp_rigenera_recovery((SELECT auth_user_id FROM _u), '["r1","r2","r3"]'::jsonb);
SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'ATTIVO|segreto-B|1001|3',
    '20) rigenerato: tre codici nuovi, il resto non cambia');

SELECT throws_like(
    $$ SELECT script.fn_totp_consuma_recovery((SELECT auth_user_id FROM _u), 'b1') $$,
    '%Codice di recupero non valido%',
    '21) un codice del mazzo vecchio non vale piu''');

-- ============================================================
-- 22-26 Disabilitazione
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT throws_like(
    $$ SELECT script.fn_totp_disabilita_device((SELECT auth_user_id FROM _u), '   ') $$,
    '%Indicare il motivo della disattivazione%',
    '22) un SUPER_ADMIN senza motivo: E_TOTP_MOTIVO_OBBLIGATORIO');

SELECT script.fn_totp_disabilita_device((SELECT auth_user_id FROM _u), 'telefono perso');
SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'ASSENTE|NULL|NULL|0',
    '23) un SUPER_ADMIN con motivo: la riga sparisce, segreto e codici con lei');

SELECT is(
    (SELECT count(*)::int FROM dbops.sessioni_utente s
      WHERE s.auth_user_id = (SELECT auth_user_id FROM _u) AND s.evento = 'TOTP_DISABILITATO'),
    0,
    '23b) dall''applicazione il verbo non scrive la traccia: e'' del backend (D-T3). Rosso da owner: il migratore la scrive (D-T5)');

SELECT throws_like(
    $$ SELECT script.fn_totp_disabilita_device((SELECT auth_user_id FROM _u), 'ancora') $$,
    '%Il secondo fattore non e'' attivo%',
    '24) disabilitare un device che non c''e'': E_TOTP_DEVICE_ASSENTE');

-- Chi agisce si decide PRIMA di cercare il device: l'altro senza privilegi e'
-- rifiutato per quello che e', anche qui dove il device non c'e' piu' (e da
-- owner — il migratore — questo test resta rosso senza toccare niente).
SELECT pg_temp.agisci((SELECT auth_user_id FROM _tec));
SELECT throws_like(
    $$ SELECT script.fn_totp_disabilita_device((SELECT auth_user_id FROM _u), 'prova') $$,
    '%Non hai i permessi per questa operazione%',
    '25) un altro senza privilegi non disabilita (rosso da owner: il migratore passa)');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _u));
SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-D', '["d1"]'::jsonb);
SELECT script.fn_totp_conferma_device((SELECT auth_user_id FROM _u), 2000);
SELECT script.fn_totp_disabilita_device((SELECT auth_user_id FROM _u), NULL);
SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'ASSENTE|NULL|NULL|0',
    '26) l''utente stesso disabilita il proprio device senza motivo');

-- ============================================================
-- 27-28 Lettura
-- ============================================================
SELECT is(pg_temp.device((SELECT auth_user_id FROM _tec)), 'ASSENTE|NULL|NULL|0',
    '27) credenziale senza device: ASSENTE, niente segreto, zero codici');

SELECT throws_like(
    $$ SELECT * FROM script.fn_get_totp_device(0) $$,
    '%Chiamata non valida a%',
    '28) id non valido: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT * FROM finish();
ROLLBACK;
