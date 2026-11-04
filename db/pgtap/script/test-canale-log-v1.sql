-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: il canale di log fuori transazione — una regola sola, e mai un errore
--       script.fn_canale_log_stringa (il building block) e i suoi quattro
--       lettori: script.fn_ensure_logconn, dbops.fn_get_or_create_session_tx_id,
--       script.fn_log_error_only, maintenance.fn_job_run_log_failure.
--
-- ChangeSet: 20_code/script/20261104-46 (il building block), -47 … -50 (i lettori)
-- Brief: brief-db-revisione-dbops, D1 + D26 (giro 1, blocco 1b)
--
-- ⭐ LA REGOLA (decisione di Tid, 2026-11-04): il canale e' acceso se c'e' una
--   stringa di connessione non vuota E myapp.log_with_dblink non vale 'off';
--   l'interruttore assente vale acceso. myapp.logconn vince su
--   myapp.dblink_log_connection.
--
-- ⛔ I DUE DIFETTI CHE CHIUDE.
--   D1 — un canale irraggiungibile faceva fallire ogni scrittura tracciata:
--        fn_ensure_logconn lasciava risalire l'errore di connessione. I test
--        7-12 usano una stringa che non si connette (porta 1): deterministici.
--   D26 — l'interruttore 'off' era aggirato: con la stringa impostata il tx_id
--        si registrava lo stesso, e i due verbali scrivevano lo stesso. I test
--        13-15 hanno bisogno di un canale che FUNZIONA (sennò sarebbero verdi
--        anche prima): dove non c'e', si saltano. Il test 13 lo decide
--        guardando il risultato, non la configurazione.
--        ⚠️ Il gemello del 13 (canale acceso) registra un tx_id che sopravvive
--        al ROLLBACK, come lo scenario D di test-tx-id-coerenza-non-registrato.
--        I test 14-15 non scrivono niente se la correzione c'e'; senza, ognuno
--        lascia una riga: e' il rosso che si vede.
--
-- Elenco test (plan 16):
--   IL BUILDING BLOCK
--    1 : interruttore assente + stringa → acceso, con quella stringa
--    2 : 'off' → spento
--    3 : 'off' con maiuscole e spazi → spento
--    4 : un valore che non e' 'off' → acceso
--    5 : stringa vuota o di soli spazi → spento
--    6 : myapp.logconn vince su myapp.dblink_log_connection
--   D1 — CANALE IRRAGGIUNGIBILE
--    7 : fn_ensure_logconn non solleva
--    8 : fn_get_or_create_session_tx_id non solleva ...
--    9 : ... restituisce la sentinella e non pubblica la GUC
--   10 : un INSERT su una tabella tracciata riesce
--   11 : fn_log_error_only non solleva
--   12 : fn_job_run_log_failure non solleva (non-regressione)
--   D26 — 'off' CON UN CANALE CHE FUNZIONA (skip dove non c'e')
--   13 : il tx_id e' la sentinella, la GUC non e' pubblicata
--   14 : fn_log_error_only non scrive in dbops.error_log
--   15 : fn_job_run_log_failure non scrive in maintenance.job_run_log
--   IL PRESIDIO SUL TESTO
--   16 : ⛔ nessuna funzione legge da se' le GUC del canale: le legge il
--        building block (e fn_audit_log_once, fuori finche' Q9 non decide)
--
-- Tutto dentro BEGIN;/ROLLBACK;, salvo le righe scritte dal canale (sopra).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- Nessuna eredita' dalla macchina: myapp.logconn vince, quindi si azzera.
SET LOCAL myapp.logconn = '';

-- ============================================================
-- 1-6. Il building block
-- ============================================================
SET LOCAL myapp.dblink_log_connection = 'host=canale.pgtap dbname=log';

-- '' e' l'assente che si puo' costruire: un RESET riporterebbe il valore
-- della macchina.
SET LOCAL myapp.log_with_dblink = '';
SELECT is(script.fn_canale_log_stringa(), 'host=canale.pgtap dbname=log',
          '1. interruttore assente: il canale e'' acceso, con la stringa impostata');

SET LOCAL myapp.log_with_dblink = 'off';
SELECT is(script.fn_canale_log_stringa(), NULL,
          '2. interruttore ''off'': il canale e'' spento');

SET LOCAL myapp.log_with_dblink = ' Off ';
SELECT is(script.fn_canale_log_stringa(), NULL,
          '3. ''off'' con maiuscole e spazi: spento lo stesso');

SET LOCAL myapp.log_with_dblink = 'on';
SELECT is(script.fn_canale_log_stringa(), 'host=canale.pgtap dbname=log',
          '4. un valore che non e'' ''off'': acceso');

SET LOCAL myapp.log_with_dblink = '';
SET LOCAL myapp.dblink_log_connection = '   ';
SELECT is(script.fn_canale_log_stringa(), NULL,
          '5. stringa di soli spazi: non configurato, quindi spento');

SET LOCAL myapp.dblink_log_connection = 'host=perdente.pgtap';
SET LOCAL myapp.logconn = 'host=vincente.pgtap';
SELECT is(script.fn_canale_log_stringa(), 'host=vincente.pgtap',
          '6. myapp.logconn vince su myapp.dblink_log_connection');
SET LOCAL myapp.logconn = '';

-- ============================================================
-- 7-12. D1 — un canale irraggiungibile non blocca niente
-- ============================================================
-- La porta 1 rifiuta subito: nessuna attesa, nessuna dipendenza dalla rete.
-- logconn chiusa e tx_id vuoto: si parte da zero, qualunque cosa abbia fatto
-- il preambolo.
-- ⚠️ 'on' e non '': la fn_ensure_logconn di prima leggeva il vuoto come
--   spento (una terza lettura, D26), e il D1 non si sarebbe mai visto.
SET LOCAL myapp.dblink_log_connection = 'host=127.0.0.1 port=1 dbname=nessuno connect_timeout=2';
SET LOCAL myapp.log_with_dblink = 'on';
SELECT public.dblink_disconnect('logconn')
 WHERE 'logconn' = ANY (coalesce(public.dblink_get_connections(), ARRAY[]::text[]));
SET LOCAL dbops.tx_id = '';

SELECT lives_ok($$SELECT script.fn_ensure_logconn()$$,
                '7. fn_ensure_logconn con il canale irraggiungibile: un WARNING, non un errore');

SELECT lives_ok($$SELECT dbops.fn_get_or_create_session_tx_id()$$,
                '8. fn_get_or_create_session_tx_id con il canale irraggiungibile non solleva');

SELECT ok(dbops.fn_get_or_create_session_tx_id() = script.uuid_nil()
          AND coalesce(current_setting('dbops.tx_id', true), '') = '',
          '9. ... restituisce la sentinella e non pubblica la GUC');

SELECT lives_ok(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento)
      VALUES (9704, 'PGTAP_PROC_CANALE_LOG', 'processo di prova per test-canale-log',
              'MANUTENZIONE', 'CODA', 'PROGRAMMA')$$,
    '10. con il canale irraggiungibile, un INSERT su una tabella tracciata riesce');

SET LOCAL dbops.tx_id = '';
SELECT lives_ok(
    $$SELECT script.fn_log_error_only('pgtap', 'pgtap.canale_log.irraggiungibile',
                                      'E_VALIDAZIONE', '{}'::jsonb, NULL, VARIADIC ARRAY[]::text[])$$,
    '11. fn_log_error_only con il canale irraggiungibile non solleva');

SELECT lives_ok(
    $$SELECT maintenance.fn_job_run_log_failure(
          'pgtap.canale_log.irraggiungibile', 'pgtap', now(), gen_random_uuid(),
          'COMMAND', 'automations_attivo', NULL, 'prova', 'E_VALIDAZIONE', NULL, 'P0001')$$,
    '12. fn_job_run_log_failure con il canale irraggiungibile non solleva');

-- ============================================================
-- 13-15. D26 — 'off' vale anche con un canale che funziona
-- ============================================================
-- La stringa della macchina, e logconn chiusa (il D1 non l'ha aperta).
RESET myapp.dblink_log_connection;
SET LOCAL myapp.logconn = '';

-- Il gemello: il canale funziona davvero, qui? Lo dice il risultato.
SET LOCAL myapp.log_with_dblink = 'on';
SET LOCAL dbops.tx_id = '';
CREATE TEMP TABLE _canale ON COMMIT DROP AS
SELECT dbops.fn_get_or_create_session_tx_id() <> script.uuid_nil() AS operativo;

SET LOCAL myapp.log_with_dblink = 'off';
SET LOCAL dbops.tx_id = '';

CREATE TEMP TABLE _off ON COMMIT DROP AS
SELECT dbops.fn_get_or_create_session_tx_id() AS tx_id,
       coalesce(current_setting('dbops.tx_id', true), '') AS guc;

SELECT script.fn_log_error_only('pgtap', 'pgtap.canale_log.spento',
                                'E_VALIDAZIONE', '{}'::jsonb, script.uuid_nil(), VARIADIC ARRAY[]::text[]);

SELECT maintenance.fn_job_run_log_failure(
           'pgtap.canale_log.spento', 'pgtap', now(), gen_random_uuid(),
           'COMMAND', 'automations_attivo', NULL, 'prova', 'E_VALIDAZIONE', NULL, 'P0001');

SELECT CASE WHEN (SELECT operativo FROM _canale)
    THEN ok((SELECT tx_id = script.uuid_nil() AND guc = '' FROM _off),
            '13. ''off'' con un canale che funziona: sentinella, GUC non pubblicata (prima si registrava lo stesso)')
    ELSE skip('13. canale di log non operativo in questo ambiente', 1)
END;

-- Le righe scritte dal canale sono di un'altra transazione, gia' confermata:
-- in READ COMMITTED questa istruzione le vede.
SELECT CASE WHEN (SELECT operativo FROM _canale)
    THEN is((SELECT count(*) FROM dbops.error_log WHERE function_name = 'pgtap.canale_log.spento'),
            0::bigint,
            '14. ''off'': fn_log_error_only non scrive in dbops.error_log')
    ELSE skip('14. canale di log non operativo in questo ambiente', 1)
END;

SELECT CASE WHEN (SELECT operativo FROM _canale)
    THEN is((SELECT count(*) FROM maintenance.job_run_log WHERE jobname = 'pgtap.canale_log.spento'),
            0::bigint,
            '15. ''off'': fn_job_run_log_failure non scrive in maintenance.job_run_log')
    ELSE skip('15. canale di log non operativo in questo ambiente', 1)
END;

-- ============================================================
-- 16. Il presidio sul testo
-- ============================================================
-- ⛔ Una funzione che legge da se' l'interruttore o la stringa torna a una
--   regola sua. Si cerca la LETTURA (current_setting), non il nome: un
--   messaggio che nomina la GUC non e' una lettura. Corpo senza commenti; il
--   prefiltro su prosrc e' un sovrainsieme economico.
SELECT is_empty(
    $$SELECT p.oid::regprocedure::text
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
         AND p.prosrc LIKE '%myapp.%'
         AND dbops.fn_corpo_funzione(p.oid)
             ~ 'current_setting\s*\(\s*''myapp\.(log_with_dblink|logconn|dblink_log_connection)'''
         AND p.oid <> 'script.fn_canale_log_stringa()'::regprocedure
         AND NOT (n.nspname = 'dbops' AND p.proname = 'fn_audit_log_once')$$,
    '16. le GUC del canale le legge solo script.fn_canale_log_stringa (fn_audit_log_once a parte, Q9)');

SELECT * FROM finish();
ROLLBACK;
