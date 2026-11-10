-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test scrive una credenziale in django.auth_user e la cancella, come fa la
--   porta script.fn_elimina_credenziale (DEFINER del proprietario), per provare la cascata.
-- pgTAP test per Zero ERP
--
-- L'etichetta di una credenziale di prova va via con la credenziale (Q14 ⑩).
-- Brief: brief-db-revisione-dbops, giro 11 (§30).
--
-- I due mondi (la FK sta nel ponte di 90_end, MARK_RAN senza django): il test 1 asserisce il ramo
-- del mondo in cui gira; gli altri hanno bisogno della FK e, senza, dicono perche' non provano.
--
-- Elenco test (plan 6):
--  1) la FK fk_credenziali_di_prova_auth_user c'e', ON DELETE CASCADE, dove c'e' django.auth_user
--  2) ⭐ il DELETE diretto dell'etichetta, con la credenziale viva, resta rifiutato
--  3) la regola di eliminabilita' non conta l'etichetta come storia (la FK e' CASCADE)
--  4) l'UPDATE dell'etichetta resta rifiutato
--  5) ⭐ cancellare la credenziale toglie l'etichetta (la cascata, ammessa dal guard)
--  6) il guard non lascia cancellare l'etichetta di un soggetto vivo
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- Il codice del rifiuto: fn_log_and_raise_error lo mette in CONSTRAINT_NAME (come in
--   dbops/test-etichette-di-prova-v1); ogni altro errore torna col suo SQLSTATE.
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION
    WHEN SQLSTATE 'P0001' THEN
        GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
        RETURN v_c;
    WHEN OTHERS THEN
        RETURN SQLSTATE;
END $$;

-- ⚠️ L'ambiente si dichiara SVILUPPO a trigger spento, perche' il file non dipenda dalla macchina
--   (come dbops/test-etichette-di-prova-v1).
ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
DELETE FROM dbops.installazione;
INSERT INTO dbops.installazione (ambiente) VALUES ('SVILUPPO');
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

-- ============================================================
-- 1) I due mondi
-- ============================================================
SELECT is(
    (SELECT CASE WHEN to_regclass('django.auth_user') IS NULL THEN 'senza django'
                 ELSE COALESCE((SELECT 'FK ' || c.confdeltype::text
                                  FROM pg_constraint c
                                 WHERE c.conrelid = 'dbops.credenziali_di_prova'::regclass
                                   AND c.conname = 'fk_credenziali_di_prova_auth_user'
                                   AND c.contype = 'f'), 'manca')
            END),
    CASE WHEN to_regclass('django.auth_user') IS NULL THEN 'senza django' ELSE 'FK c' END,
    '1) dove c''e'' django.auth_user la FK c''e'', ON DELETE CASCADE; senza django non puo'' nascere');

-- ============================================================
-- Fixture: una credenziale nuda, senza vesti, e la sua etichetta
-- ============================================================
CREATE TEMP TABLE t_cred (auth_user_id integer) ON COMMIT DROP;
WITH u AS (
    INSERT INTO django.auth_user (password, is_superuser, username, first_name, last_name, email,
                                  is_staff, is_active, date_joined)
    VALUES ('!', false, 'pgtap.etichetta.fk', '', '', '', false, true, now())
    RETURNING id)
INSERT INTO t_cred SELECT u.id FROM u;
INSERT INTO dbops.credenziali_di_prova (auth_user_id, chiave)
SELECT auth_user_id, 'pgtap.etichetta.fk' FROM t_cred;

-- ============================================================
-- 2-5) La credenziale e la sua etichetta
-- ============================================================
SELECT is(
    pg_temp.codice_errore($$DELETE FROM dbops.credenziali_di_prova WHERE chiave = 'pgtap.etichetta.fk'$$),
    'E_ETICHETTA_DI_PROVA_IMMUTABILE',
    '2) il DELETE diretto dell''etichetta, con la credenziale viva: E_ETICHETTA_DI_PROVA_IMMUTABILE');

SELECT is(
    (SELECT count(*)::int
       FROM jsonb_array_elements(script.fn_check_credenziale_eliminabile((SELECT auth_user_id FROM t_cred))) m
      WHERE m->>'reason' = 'CON_STORIA'),
    0,
    '3) la regola di eliminabilita'' non conta l''etichetta come storia: la FK e'' CASCADE');

SELECT is(
    pg_temp.codice_errore($$UPDATE dbops.credenziali_di_prova SET chiave = 'pgtap.altra' WHERE chiave = 'pgtap.etichetta.fk'$$),
    'E_ETICHETTA_DI_PROVA_IMMUTABILE',
    '4) l''UPDATE dell''etichetta resta rifiutato');

-- ⚠️ La cancellazione in un'istruzione a se': un conteggio nella stessa istruzione vedrebbe la
--   fotografia di prima.
CREATE TEMP TABLE t_esito ON COMMIT DROP AS
SELECT EXISTS (SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_credenziali_di_prova_auth_user'
                  AND conrelid = 'dbops.credenziali_di_prova'::regclass) AS con_fk,
       NULL::text AS esito;

UPDATE t_esito
   SET esito = COALESCE((SELECT pg_temp.codice_errore(
                                    format('DELETE FROM django.auth_user WHERE id = %s', auth_user_id)) FROM t_cred),
                        'ok')
 WHERE con_fk;

SELECT CASE
         WHEN (SELECT con_fk FROM t_esito)
         THEN is((SELECT esito FROM t_esito) || ' / ' ||
                 (SELECT count(*)::text FROM dbops.credenziali_di_prova WHERE chiave = 'pgtap.etichetta.fk'),
                 'ok / 0',
                 '5) cancellare la credenziale toglie l''etichetta: la cascata, che il guard ammette')
         ELSE skip('5) senza la FK (il mondo senza django al migrate) la cascata non c''e''', 1)
       END;

-- ============================================================
-- 6) La gemella: il soggetto vivo trattiene la sua etichetta
-- ============================================================
CREATE TEMP TABLE t_sog ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Etichetta FK pgTAP') AS soggetto_id;
INSERT INTO dbops.soggetti_di_prova (soggetto_id, chiave)
SELECT soggetto_id, 'PGTAP-ETICHETTA-FK' FROM t_sog;

SELECT is(
    pg_temp.codice_errore($$DELETE FROM dbops.soggetti_di_prova WHERE chiave = 'PGTAP-ETICHETTA-FK'$$),
    'E_ETICHETTA_DI_PROVA_IMMUTABILE',
    '6) l''etichetta di un soggetto vivo non si cancella');

SELECT * FROM finish();
ROLLBACK;
