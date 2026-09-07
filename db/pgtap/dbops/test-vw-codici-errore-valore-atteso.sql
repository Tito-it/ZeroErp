-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: i test 1..4 CREANO funzioni plpgsql di prova (in
--   transazione, poi annullata) perche' il classificatore legge `pg_proc.prosrc`
--   e non c'e' altro modo di costruire una forma. E' DDL: il ruolo applicativo
--   non ne fa e non ne deve fare.
--
-- Test: dbops.vw_codici_errore_forme_condizione — la famiglia VALORE_ATTESO
-- ChangeSet: 20260907-03
-- Brief: brief-db-sveglia-dei-processi §3.2 (segnalazione BE) e §8.4 (risposta)
--
-- Elenco test (plan 6):
--  1) ⭐ «il valore letto non e' quello ammesso» e' VALORE_ATTESO
--  2) ⛔ e una guardia che il classificatore NON sa leggere resta IGNOTO
--  3) ⚠️ l'ordine del CASE regge: un NOT IN resta ENUM
--  4) ⚠️ e una guardia su parametro nullo resta PARAMETRO
--  5) ✅ il caso segnalato dal backend e' chiuso: E_VALIDAZIONE affiora
--  6) ⚠️ la famiglia non e' una parola morta: qualcuno la porta davvero
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I TEST 1 E 2 VANNO LETTI INSIEME, ed e' la ragione per cui sono due.
--   Il test 1 da solo passerebbe su un classificatore che risponde SEMPRE
--   VALORE_ATTESO — cioe' su un asse che ha smesso di distinguere, che e' il
--   modo in cui questa misura diventerebbe rumore. Il 2 e' il verso che lo
--   impedisce: una guardia che nessuna regola sa leggere DEVE restare IGNOTO,
--   perche' IGNOTO non e' un difetto della misura, e' la misura che dichiara di
--   non sapere.
--
-- ⛔ I CASI SI COSTRUISCONO, non si cercano nel codice esistente. Un test che
--   frugasse fra le funzioni di oggi proverebbe soltanto i casi che questa
--   popolazione per caso contiene, e su un database ricostruito da zero
--   girerebbe identico solo per coincidenza. Qui le funzioni-testimone le
--   scrive il test.
--
-- ⚠️ IL TEST 5 E' L'ECCEZIONE, E VA SAPUTO: legge il codice vivo, perche' la
--   domanda del backend era su una funzione precisa. La vista aggrega per
--   CODICE e non espone la funzione, quindi «nella terza guardia di
--   config.fn_chiudi_email_sistema» non e' una domanda che le si possa fare: si
--   chiede l'effetto che quella guardia produce sul codice che solleva. Se
--   quella funzione un giorno cambia forma, questo test diventa rosso — ed e'
--   corretto, perche' quella funzione E' il soggetto.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Le funzioni-testimone: quattro forme, quattro risposte attese
-- ============================================================
-- ⚠️ Ogni corpo rispetta le condizioni che il classificatore pretende: una riga
--   di guardia, la chiamata a fn_log_and_raise_error entro sei righe, e il
--   codice nominato fuori dai commenti entro venticinque righe dalla guardia.

-- ⭐ La forma nuova: e' quella della terza guardia di
--   config.fn_chiudi_email_sistema — «qualcuno sta usando la porta di sistema
--   per l'email di un'azienda».
CREATE FUNCTION dbops.pgtap_forma_valore_atteso() RETURNS void
LANGUAGE plpgsql AS $f$
DECLARE
    v_ambito text := 'SISTEMA';
BEGIN
    IF v_ambito <> 'SISTEMA' THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'pgtap_forma_valore_atteso', 'E_PGTAP_FORMA_VALORE_ATTESO',
            '{}'::jsonb, NULL::uuid, 'testimone');
    END IF;
END
$f$;

-- ⛔ Una guardia che nessuna regola sa leggere: un confronto fra due variabili,
--   senza letterali, senza parametri, senza insiemi.
CREATE FUNCTION dbops.pgtap_forma_illeggibile() RETURNS void
LANGUAGE plpgsql AS $f$
DECLARE
    v_a integer := 1;
    v_b integer := 2;
BEGIN
    IF v_a > v_b THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'pgtap_forma_illeggibile', 'E_PGTAP_FORMA_ILLEGGIBILE',
            '{}'::jsonb, NULL::uuid, 'testimone');
    END IF;
END
$f$;

-- ⚠️ Un insieme resta un insieme: il ramo ENUM viene PRIMA di quello nuovo.
CREATE FUNCTION dbops.pgtap_forma_enum() RETURNS void
LANGUAGE plpgsql AS $f$
DECLARE
    v_stato text := 'SENT';
BEGIN
    IF v_stato NOT IN ('SENT', 'FAILED', 'RETRY') THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'pgtap_forma_enum', 'E_PGTAP_FORMA_ENUM',
            '{}'::jsonb, NULL::uuid, 'testimone');
    END IF;
END
$f$;

-- ⚠️ E una guardia su un parametro nullo resta PARAMETRO anche quando accanto
--   confronta un letterale: e' il caso che l'ordine del CASE deve proteggere.
CREATE FUNCTION dbops.pgtap_forma_parametro(p_tipo text) RETURNS void
LANGUAGE plpgsql AS $f$
BEGIN
    IF p_tipo IS NULL OR p_tipo <> 'SISTEMA' THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'pgtap_forma_parametro', 'E_PGTAP_FORMA_PARAMETRO',
            '{}'::jsonb, NULL::uuid, 'testimone');
    END IF;
END
$f$;

-- ============================================================
-- 1..4. Le quattro forme, lette dalla vista
-- ============================================================
SELECT is(
    (SELECT famiglie FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_PGTAP_FORMA_VALORE_ATTESO'),
    ARRAY['VALORE_ATTESO'],
    '1. «il valore letto non e'' quello ammesso» e'' VALORE_ATTESO, non IGNOTO'
);

-- ⛔ Senza questo, il test 1 passerebbe anche su un classificatore che dice
--   sempre VALORE_ATTESO — cioe' su un asse che ha smesso di distinguere.
SELECT is(
    (SELECT famiglie FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_PGTAP_FORMA_ILLEGGIBILE'),
    ARRAY['IGNOTO'],
    '2. una guardia che nessuna regola sa leggere resta IGNOTO: la misura dichiara di non sapere'
);

SELECT is(
    (SELECT famiglie FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_PGTAP_FORMA_ENUM'),
    ARRAY['ENUM'],
    '3. un NOT IN resta ENUM: il ramo nuovo viene DOPO, e non riscrive letture vecchie'
);

SELECT is(
    (SELECT famiglie FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_PGTAP_FORMA_PARAMETRO'),
    ARRAY['PARAMETRO'],
    '4. una guardia su parametro nullo resta PARAMETRO anche se confronta un letterale'
);

-- ============================================================
-- 5. ✅ Il caso che il backend ha segnalato
-- ============================================================
-- ⭐ Prima del 20260907-03, E_VALIDAZIONE leggeva famiglie {IGNOTO, PARAMETRO}
--   con n_famiglie_note = 1: NON compariva nella query (1) dei candidati, che
--   filtra > 1. La sua seconda forma era proprio la terza guardia di
--   config.fn_chiudi_email_sistema — il punto piu' pericoloso di quella
--   funzione, e l'unico momento in cui si nota che qualcuno usa la porta di
--   sistema per l'email di un'azienda.
-- ⚠️ Questo test legge il codice VIVO, ed e' dichiarato in testa al file: se
--   quella funzione cambia forma diventa rosso, ed e' corretto — e' il soggetto.
SELECT ok(
    (SELECT n_famiglie_note > 1 AND 'VALORE_ATTESO' = ANY(famiglie)
       FROM dbops.vw_codici_errore_forme_condizione
      WHERE codice = 'E_VALIDAZIONE'),
    '5. E_VALIDAZIONE porta VALORE_ATTESO e affiora fra i candidati della query (1)'
);

-- ============================================================
-- 6. ⚠️ La famiglia non e' una parola morta
-- ============================================================
-- ⛔ Un ramo di CASE che nel codice vero non aggancia mai sarebbe una regola
--   scritta e mai applicata: passerebbe i test 1..4 sui propri testimoni e non
--   servirebbe a niente. ⚠️ Si esclude il seminato di questo file, altrimenti il
--   test si risponderebbe da solo.
SELECT isnt_empty(
    $$SELECT codice FROM dbops.vw_codici_errore_forme_condizione
       WHERE 'VALORE_ATTESO' = ANY(famiglie)
         AND codice NOT LIKE 'E_PGTAP_FORMA_%'$$,
    '6. nel codice vero qualcuno porta davvero VALORE_ATTESO: il ramo non e'' scritto a vuoto'
);

-- ⛔ Si tolgono: la transazione le annullerebbe comunque, ma un file che
--   ripulisce cio' che semina si puo' rileggere senza chiedersi cosa resti.
DROP FUNCTION dbops.pgtap_forma_valore_atteso();
DROP FUNCTION dbops.pgtap_forma_illeggibile();
DROP FUNCTION dbops.pgtap_forma_enum();
DROP FUNCTION dbops.pgtap_forma_parametro(text);

SELECT * FROM finish();

ROLLBACK;
