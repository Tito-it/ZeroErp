-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il BLOCCO DELL'ADMIN — un atto autorizzato (D-1 riletta, D-B1, D-B3) —
--   e l'anti-lockout che lo sorveglia.
--   Brief: brief-db-blocco-login-per-credenziale, sezione 3.3.
--   ChangeSet: 20260925-06 (fn_guard_super_admin), -12/-13 (i predicati),
--   -14/-15 (i verbi), -18 (il guard su config.credenziali).
--
-- ⭐ Il permesso si COSTRUISCE: un SUPER_ADMIN umano
--   (dbops.fn_pgtap_crea_operatore_umano(…, true)) e un operatore tecnico senza
--   privilegi (dbops.fn_pgtap_crea_emittente_operatore). Il caso «ultimo
--   SUPER_ADMIN» si costruisce spegnendo gli ALTRI binding, come
--   config/test-profili-accesso-guard-ultimo-super-admin.sql.
--
-- Elenco test (plan 16):
--   Il permesso (D-B1)
--    1) chi agisce non e' SUPER_ADMIN -> E_PERMESSO_NEGATO
--    2) nessun utente in sessione -> E_PERMESSO_NEGATO (fail-closed)
--    3) SUPER_ADMIN ma in veste CLIENTE_PORTALE -> E_PERMESSO_NEGATO (gate della regola)
--   Validazione
--    4) motivo vuoto -> E_CREDENZIALE_MOTIVO_OBBLIGATORIO
--    5) credenziale inesistente -> E_CREDENZIALE_NON_TROVATA
--   Il blocco
--    6) SUPER_ADMIN blocca: la riga porta chi, quando e perche'
--    7) il login e' rifiutato da una provenienza qualunque -> E_CREDENZIALE_BLOCCATA
--    8) ...e da un'altra (vale su tutte le porte e le macchine)
--    9) l'azzeramento dei tentativi (il reset) NON toglie il blocco (D-B3)
--   Lo sblocco
--   10) chi non e' SUPER_ADMIN non sblocca -> E_PERMESSO_NEGATO
--   11) SUPER_ADMIN sblocca: il login passa
--   12) sbloccare di nuovo e' idempotente
--   Anti-lockout
--   13) bloccare l'ultimo SUPER_ADMIN raggiungibile (se stesso) -> E_PROFILO_ULTIMO_SUPER_ADMIN
--   14) con un secondo SUPER_ADMIN, bloccarlo e' ammesso
--   15) ...e il bloccato non conta: fn_check_ultimo_super_admin_attivo(primo) = true
--   16) ...fn_check_almeno_un_super_admin_attivo resta true (il primo c'e')
--
-- ⚠️ Gira come l'APPLICAZIONE: i verbi sono DEFINER e leggono chi agisce dalla
--   GUC, come in esercizio. I test 13-16 cambiano lo stato dei binding: stanno
--   in fondo, il ROLLBACK li annulla.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _sa   AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-blocco', true);
CREATE TEMP TABLE _tec  AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                              first_name, last_name, email, date_joined)
VALUES ('_pgtap_bersaglio_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now());
CREATE TEMP TABLE _t AS SELECT max(id) AS bersaglio FROM django.auth_user WHERE username LIKE '\_pgtap\_bersaglio\_%';

-- Chi agisce: il contesto operatore su un utente dato.
CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

-- ============================================================
-- 1-3 Il permesso
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _tec));
SELECT throws_like(
    $$ SELECT script.fn_blocca_credenziale((SELECT bersaglio FROM _t), 'prova') $$,
    '%Non hai i permessi per questa operazione%',
    '1) chi agisce non e'' SUPER_ADMIN: E_PERMESSO_NEGATO');

SELECT set_config('app.current_user_id', '', true);
SELECT throws_like(
    $$ SELECT script.fn_blocca_credenziale((SELECT bersaglio FROM _t), 'prova') $$,
    '%Non hai i permessi per questa operazione%',
    '2) nessun utente in sessione: E_PERMESSO_NEGATO (fail-closed)');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
SELECT throws_like(
    $$ SELECT script.fn_blocca_credenziale((SELECT bersaglio FROM _t), 'prova') $$,
    '%Non hai i permessi per questa operazione%',
    '3) SUPER_ADMIN in veste CLIENTE_PORTALE: negato (il gate di contesto e'' di fn_is_super_admin)');
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));

-- ============================================================
-- 4-5 Validazione
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_blocca_credenziale((SELECT bersaglio FROM _t), '   ') $$,
    '%Indicare il motivo del blocco%',
    '4) motivo vuoto: E_CREDENZIALE_MOTIVO_OBBLIGATORIO');

SELECT throws_like(
    $$ SELECT script.fn_blocca_credenziale((SELECT max(id) + 1000 FROM django.auth_user), 'prova') $$,
    '%Credenziale non trovata%',
    '5) credenziale inesistente: E_CREDENZIALE_NON_TROVATA');

-- ============================================================
-- 6-9 Il blocco
-- ============================================================
SELECT script.fn_blocca_credenziale((SELECT bersaglio FROM _t), '  accesso sospetto  ');

SELECT is(
    (SELECT format('%s|%s|%s', (c.bloccata_at IS NOT NULL)::text, (c.bloccata_da = (SELECT auth_user_id FROM _sa))::text, c.motivo_blocco)
       FROM config.credenziali c WHERE c.auth_user_id = (SELECT bersaglio FROM _t)),
    'true|true|accesso sospetto',
    '6) SUPER_ADMIN blocca: la riga porta quando, chi (dalla GUC) e perche'' (ripulito)');

SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login((SELECT bersaglio FROM _t), sha256('pgtap-nome'::bytea), '203.0.113.10'::inet) $$,
    '%Accesso bloccato dall''amministratore%',
    '7) il login e'' rifiutato: E_CREDENZIALE_BLOCCATA');

SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login((SELECT bersaglio FROM _t), sha256('pgtap-nome'::bytea), '2001:db8::1'::inet) $$,
    '%Accesso bloccato dall''amministratore%',
    '8) ...da qualunque provenienza: il blocco e'' della credenziale');

SELECT script.fn_azzera_tentativi_credenziale((SELECT bersaglio FROM _t));
SELECT throws_like(
    $$ SELECT script.fn_check_blocco_login((SELECT bersaglio FROM _t), sha256('pgtap-nome'::bytea), '203.0.113.10'::inet) $$,
    '%Accesso bloccato dall''amministratore%',
    '9) l''azzeramento dei tentativi (il reset) non toglie il blocco dell''admin (D-B3)');

-- ============================================================
-- 10-12 Lo sblocco
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _tec));
SELECT throws_like(
    $$ SELECT script.fn_sblocca_credenziale((SELECT bersaglio FROM _t)) $$,
    '%Non hai i permessi per questa operazione%',
    '10) chi non e'' SUPER_ADMIN non sblocca');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT script.fn_sblocca_credenziale((SELECT bersaglio FROM _t));
SELECT lives_ok(
    $$ SELECT script.fn_check_blocco_login((SELECT bersaglio FROM _t), sha256('pgtap-nome'::bytea), '203.0.113.10'::inet) $$,
    '11) SUPER_ADMIN sblocca: il login passa');

SELECT lives_ok(
    $$ SELECT script.fn_sblocca_credenziale((SELECT bersaglio FROM _t)) $$,
    '12) sbloccare una credenziale gia'' sbloccata non fa niente');

-- ============================================================
-- 13-16 Anti-lockout (cambia i binding: in fondo)
-- ============================================================
-- Spegne tutti i binding SUPER_ADMIN tranne quello del SA del test.
UPDATE config.profili_accesso_bindings pab
   SET attivo = false
  FROM config.profili_accesso pa
 WHERE pa.id = pab.profilo_accesso_id
   AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
   AND pab.attivo = true
   AND pab.identita_digitale_id <> (SELECT identita_id FROM _sa);

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
    '13) bloccare l''ultimo SUPER_ADMIN raggiungibile (se stesso): E_PROFILO_ULTIMO_SUPER_ADMIN');

CREATE TEMP TABLE _sa2 AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-blocco-2', true);

SELECT lives_ok(
    $$ SELECT script.fn_blocca_credenziale((SELECT auth_user_id FROM _sa2), 'prova sul secondo') $$,
    '14) con un secondo SUPER_ADMIN, bloccarlo e'' ammesso (il primo resta)');

SELECT is(
    script.fn_check_ultimo_super_admin_attivo((SELECT auth_user_id FROM _sa)),
    true,
    '15) il SUPER_ADMIN bloccato non conta: il primo risulta l''ultimo raggiungibile');

SELECT is(
    script.fn_check_almeno_un_super_admin_attivo(),
    true,
    '16) fn_check_almeno_un_super_admin_attivo resta true: il primo c''e''');

SELECT * FROM finish();
ROLLBACK;
