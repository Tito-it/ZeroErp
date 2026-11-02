-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il segreto TOTP segue la ROTAZIONE DELLE CHIAVI —
--   script.fn_totp_ricifra_segreto, confronta e sostituisci.
--   Brief: brief-db-totp-ricifra-segreto, sezioni 2 e 3.
--   ChangeSet: 20_code/script/20261001-35 (il verbo). La porta (l'app esegue
--   il verbo e resta senza UPDATE sulla tabella) sta in test-totp-porta-v1.sql.
--
-- ⭐ Nessuno agisce: le chiamate al verbo girano con app.current_user_id
--   vuoto, come il comando di manutenzione che lo usa. I device li fabbricano
--   i verbi del ciclo di vita, come in esercizio.
--
-- Elenco test (plan 12):
--   Sostituzione
--    1) il valore atteso combacia: true
--    2) ...e il segreto e' quello nuovo, il device resta ATTIVO
--    3) ...e non tocca confermato, passo, codici di recupero, ultimo_uso_at, meta
--   Il segreto cambiato nel frattempo
--    4) atteso che non combacia piu': false
--    5) ...e il segreto non cambia
--    6) credenziale senza device: false
--   Qualunque stato
--    7) un device DA_CONFERMARE: true
--    8) ...e resta DA_CONFERMARE, col segreto nuovo
--   Parametri rotti -> E_AUTH_CHIAMATA_NON_VALIDA
--    9) id non valido
--   10) segreto atteso NULL
--   11) segreto nuovo vuoto
--   12) atteso = nuovo
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- Fixture: un device ATTIVO e usato, uno DA_CONFERMARE, una credenziale senza
-- ============================================================
CREATE TEMP TABLE _u   AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-RICIFRA-attivo', false);
CREATE TEMP TABLE _v   AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-RICIFRA-setup', false);
CREATE TEMP TABLE _tec AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

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

-- Tutto cio' che il verbo NON deve toccare, in una riga confrontabile.
CREATE OR REPLACE FUNCTION pg_temp.resto(p_auth_user_id integer) RETURNS text
LANGUAGE sql AS $$
    SELECT ROW(d.confermato, d.ultimo_passo_usato, d.recovery_codes_hash,
               d.ultimo_uso_at, d.meta)::text
      FROM config.auth_totp_device d
     WHERE d.auth_user_id = p_auth_user_id;
$$;

SELECT pg_temp.agisci((SELECT auth_user_id FROM _u));
SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _u), 'segreto-A', '["a1","a2","a3"]'::jsonb);
SELECT script.fn_totp_conferma_device((SELECT auth_user_id FROM _u), 1000);

SELECT pg_temp.agisci((SELECT auth_user_id FROM _v));
SELECT script.fn_totp_registra_device((SELECT auth_user_id FROM _v), 'segreto-V', '["v1"]'::jsonb);

-- Da qui nessuno agisce: e' il comando di manutenzione.
SELECT set_config('app.current_user_id', '', true);
-- Un uso e un codice consumato: passo, ultimo_uso_at e mazzo valorizzati.
SELECT script.fn_totp_registra_uso((SELECT auth_user_id FROM _u), 1001);
SELECT script.fn_totp_consuma_recovery((SELECT auth_user_id FROM _u), 'a3');

CREATE TEMP TABLE _prima AS SELECT pg_temp.resto((SELECT auth_user_id FROM _u)) AS resto;

-- ============================================================
-- 1-3 Sostituzione
-- ============================================================
SELECT is(script.fn_totp_ricifra_segreto((SELECT auth_user_id FROM _u), 'segreto-A', 'segreto-A2'), true,
    '1) il valore atteso combacia: il verbo scrive e restituisce true');

SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'ATTIVO|segreto-A2|1001|2',
    '2) il segreto e'' quello nuovo, il device resta ATTIVO');

SELECT is(pg_temp.resto((SELECT auth_user_id FROM _u)), (SELECT resto FROM _prima),
    '3) non tocca confermato, passo, codici di recupero, ultimo_uso_at, meta');

-- ============================================================
-- 4-6 Il segreto cambiato nel frattempo
-- ============================================================
SELECT is(script.fn_totp_ricifra_segreto((SELECT auth_user_id FROM _u), 'segreto-A', 'segreto-A3'), false,
    '4) il segreto non e'' piu'' quello letto: false, non un errore');

SELECT is(pg_temp.device((SELECT auth_user_id FROM _u)), 'ATTIVO|segreto-A2|1001|2',
    '5) ...e il segreto resta quello scritto da chi e'' arrivato prima');

SELECT is(script.fn_totp_ricifra_segreto((SELECT auth_user_id FROM _tec), 'segreto-X', 'segreto-Y'), false,
    '6) credenziale senza device (disabilitato nel frattempo): false');

-- ============================================================
-- 7-8 Qualunque stato
-- ============================================================
SELECT is(script.fn_totp_ricifra_segreto((SELECT auth_user_id FROM _v), 'segreto-V', 'segreto-V2'), true,
    '7) un device DA_CONFERMARE si ricifra anche lui');

SELECT is(pg_temp.device((SELECT auth_user_id FROM _v)), 'DA_CONFERMARE|segreto-V2|NULL|1',
    '8) ...e resta DA_CONFERMARE, col segreto nuovo');

-- ============================================================
-- 9-12 Parametri rotti: il chiamante e' rotto
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_totp_ricifra_segreto(0, 'segreto-A2', 'segreto-A4') $$,
    '%Chiamata non valida a%',
    '9) id non valido: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    $$ SELECT script.fn_totp_ricifra_segreto((SELECT auth_user_id FROM _u), NULL, 'segreto-A4') $$,
    '%Chiamata non valida a%',
    '10) segreto atteso NULL: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    $$ SELECT script.fn_totp_ricifra_segreto((SELECT auth_user_id FROM _u), 'segreto-A2', '   ') $$,
    '%Chiamata non valida a%',
    '11) segreto nuovo vuoto: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    $$ SELECT script.fn_totp_ricifra_segreto((SELECT auth_user_id FROM _u), 'segreto-A2', 'segreto-A2') $$,
    '%Chiamata non valida a%',
    '12) atteso = nuovo: E_AUTH_CHIAMATA_NON_VALIDA');

SELECT * FROM finish();
ROLLBACK;
