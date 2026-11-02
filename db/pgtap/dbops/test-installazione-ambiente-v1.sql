-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il caso «ambiente non dichiarato» si COSTRUISCE
--   togliendo la riga di dbops.installazione, che il guard di immutabilita'
--   protegge anche dal proprietario: serve disattivare il trigger (DDL, solo
--   il proprietario), in transazione, annullato col ROLLBACK. E i passi dei
--   job stanno in pgagent.*, che l'applicazione non legge.
--
-- L'ambiente dell'installazione: la tabella, la porta, l'immutabilita', i due
-- lettori, il presidio, la sveglia senza ambiente, il cancello dei job.
--   Brief: brief-db-processi-accensione-per-ambiente (A-1, R-1, R-2, R-3, P-3)
--   changeSet 20261016-15 (tabella), -16/-17 (immutabile), -18/-19 (lettori),
--   -26 (sveglia), -29 (presidio), 85_pgagent/20261016-30 (cancello dei
--   passi), 90_end/20261016-32 (porta); loop 20260205-41 e fase post del
--   provisioning (le altre due sedi della porta).
--
-- Elenco test (plan 23):
--   forma e porta (R-3)
--    1) i due CHECK: una riga sola, due valori
--    2) l'app legge e non scrive (has_table_privilege): le tre sedi allineate
--    3) i due trigger del guard sono montati (riga e TRUNCATE), fase a05
--   l'ambiente dichiarato
--    4) c'e' una riga, con un valore del vocabolario (⚠️ rosso su un database
--       non ancora dichiarato: e' proprio cio' che deve dire)
--    5) il lettore che decide non solleva, e i due lettori dicono la stessa cosa
--    6) il presidio e' vuoto
--   ⛔ immutabile (decisione di Tid del 2026-10-16)
--    7) UPDATE, anche allo stesso valore -> E_AMBIENTE_IMMUTABILE
--    8) DELETE -> E_AMBIENTE_IMMUTABILE
--    9) TRUNCATE -> E_AMBIENTE_IMMUTABILE
--   10) una seconda riga -> rifiutata (chiave unica sull'id 1)
--   11) un valore fuori vocabolario -> chk_installazione_ambiente
--   ⭐ l'ambiente non dichiarato, costruito (trigger disattivato in transazione)
--   12) fn_ambiente_dichiarato() -> NULL
--   13) fn_ambiente_installazione() -> E_CONFIG_MANCANTE (R-1: niente ripiego)
--   14) il presidio ha una riga, col nome del database
--   15) la sveglia di uno spegnibile senza scelta -> E_CONFIG_MANCANTE
--   16) la sveglia di un non spegnibile -> true (R-1: non legge l'ambiente)
--   17) la sveglia con una scelta a mano -> la scelta (decidibile senza ambiente)
--   18) il panorama non solleva, e `acceso` e' NULL dove non si sa
--   19) il presidio sparisce quando l'ambiente torna
--   il cancello dei job (85_pgagent/20261016-30; skip dove pgAgent non c'e')
--   20) ogni passo SQL di un job di un processo con sveglia chiede alla sveglia
--   21) ... col proprio codice di processo
--   22) nessun passo e' avvolto due volte
--   23) ⭐ il passo di un processo SPENTO, eseguito, non lancia il lavoro:
--       nessuna corsa nel giornale (analyze_statistiche spento a mano)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(23);

-- Il CODICE dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error): si pinna il codice, non la frase.
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

-- ============================================================
-- Forma e porta
-- ============================================================
SELECT is(
    (SELECT string_agg(c.conname, ',' ORDER BY c.conname)
       FROM pg_constraint c
      WHERE c.conrelid = 'dbops.installazione'::regclass AND c.contype = 'c'),
    'chk_installazione_ambiente,chk_installazione_riga_unica',
    '1. i due CHECK: una riga sola, due valori');

SELECT is(
    format('%s|%s|%s|%s',
           has_table_privilege('zeroerp_app', 'dbops.installazione', 'SELECT'),
           has_table_privilege('zeroerp_app', 'dbops.installazione', 'INSERT'),
           has_table_privilege('zeroerp_app', 'dbops.installazione', 'UPDATE'),
           has_table_privilege('zeroerp_app', 'dbops.installazione', 'DELETE')),
    't|f|f|f',
    '2. l''app legge l''ambiente e non lo scrive (forward, loop dei grant, provisioning)');

SELECT is(
    (SELECT string_agg(t.tgname, ',' ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgrelid = 'dbops.installazione'::regclass AND NOT t.tgisinternal),
    'trg_installazione_a05_guard_immutabile_trn,trg_installazione_a05_guard_immutabile_upd_dlt',
    '3. i due trigger del guard sono montati: di riga e di TRUNCATE');

-- ============================================================
-- L'ambiente dichiarato
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', count(*), bool_and(i.ambiente IN ('SVILUPPO', 'PRODUZIONE')))
       FROM dbops.installazione i),
    '1|t',
    '4. l''ambiente e'' dichiarato: una riga, un valore del vocabolario');

-- ⚠️ Il lettore che decide si chiama dentro pg_temp.codice_errore: su un
--   database non dichiarato solleva, e una eccezione nuda fermerebbe il file
--   (gli altri test non girerebbero). Lo stato «non dichiarato» lo dice il 4.
SELECT is(
    format('%s|%s',
           COALESCE(pg_temp.codice_errore($$SELECT script.fn_ambiente_installazione()$$), 'nessun errore'),
           (SELECT script.fn_ambiente_installazione()
             WHERE script.fn_ambiente_dichiarato() IS NOT NULL)
               IS NOT DISTINCT FROM script.fn_ambiente_dichiarato()),
    'nessun errore|t',
    '5. il lettore che decide non solleva, e dice la stessa cosa dell''altro');

SELECT is_empty($$SELECT * FROM dbops.vw_ambiente_non_dichiarato$$,
                '6. il presidio dell''ambiente non dichiarato e'' vuoto');

-- ============================================================
-- ⛔ Immutabile
-- ============================================================
SELECT is(pg_temp.codice_errore($$UPDATE dbops.installazione SET ambiente = ambiente$$),
          'E_AMBIENTE_IMMUTABILE', '7. UPDATE, anche allo stesso valore: E_AMBIENTE_IMMUTABILE');

SELECT is(pg_temp.codice_errore($$DELETE FROM dbops.installazione$$),
          'E_AMBIENTE_IMMUTABILE', '8. DELETE: E_AMBIENTE_IMMUTABILE');

SELECT is(pg_temp.codice_errore($$TRUNCATE dbops.installazione$$),
          'E_AMBIENTE_IMMUTABILE', '9. TRUNCATE: E_AMBIENTE_IMMUTABILE');

SELECT throws_ok(
    $$INSERT INTO dbops.installazione (ambiente) VALUES ('SVILUPPO')$$,
    '23505', NULL,
    '10. una seconda riga: rifiutata dalla chiave (l''id e'' sempre 1)');

SELECT throws_like(
    $$INSERT INTO dbops.installazione (id, ambiente) VALUES (1, 'COLLAUDO')$$,
    '%chk_installazione_ambiente%',
    '11. un valore fuori vocabolario: chk_installazione_ambiente');

-- ============================================================
-- ⭐ L'ambiente non dichiarato, COSTRUITO
--   Il guard protegge anche il proprietario: lo si disattiva per togliere la
--   riga, e si riattiva subito. Tutto si annulla col ROLLBACK.
--   ⚠️ L'ALTER TABLE tiene un lock esclusivo su dbops.installazione fino al
--   ROLLBACK: un altro test che legge l'ambiente nello stesso momento aspetta.
-- ============================================================
CREATE TEMP TABLE _ambiente_di_prima AS
SELECT i.ambiente FROM dbops.installazione i;

ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
DELETE FROM dbops.installazione;
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

-- Una scelta a mano gia' presente su questa macchina falserebbe 15 e 17.
DELETE FROM dbops.processi_accensione a
 USING dbops.processi p
 WHERE p.id = a.processo_id AND p.codice IN ('smoke_notturno', 'analyze_statistiche');

SELECT is(script.fn_ambiente_dichiarato(), NULL::text,
          '12. fn_ambiente_dichiarato(): NULL, non dichiarato');

SELECT is(pg_temp.codice_errore($$SELECT script.fn_ambiente_installazione()$$),
          'E_CONFIG_MANCANTE', '13. fn_ambiente_installazione(): E_CONFIG_MANCANTE, nessun ripiego (R-1)');

SELECT is((SELECT v.database_nome FROM dbops.vw_ambiente_non_dichiarato v), current_database()::text,
          '14. il presidio ha una riga, col nome del database');

SELECT is(pg_temp.codice_errore($$SELECT maintenance.fn_sveglia_accesa('smoke_notturno')$$),
          'E_CONFIG_MANCANTE', '15. la sveglia di uno spegnibile senza scelta: E_CONFIG_MANCANTE');

SELECT is(maintenance.fn_sveglia_accesa('listen_permessi'), true,
          '16. la sveglia di un non spegnibile: accesa, senza leggere l''ambiente (R-1)');

INSERT INTO dbops.processi_accensione (processo_id, acceso, motivo)
SELECT p.id, false, 'pgTAP: scelta senza ambiente'
  FROM dbops.processi p WHERE p.codice = 'analyze_statistiche';

SELECT is(maintenance.fn_sveglia_accesa('analyze_statistiche'), false,
          '17. con una scelta a mano la sveglia decide anche senza ambiente');

SELECT is(
    (SELECT format('%s|%s', v.acceso IS NULL, v.stato <> 'SPENTO')
       FROM dbops.vw_processi_programmazione v
      WHERE v.processo_codice = 'smoke_notturno'),
    't|t',
    '18. il panorama non solleva: acceso NULL e nessuno SPENTO inventato');

INSERT INTO dbops.installazione (ambiente) SELECT ambiente FROM _ambiente_di_prima;

SELECT is_empty($$SELECT * FROM dbops.vw_ambiente_non_dichiarato$$,
                '19. dichiarato di nuovo: il presidio torna vuoto');

-- ============================================================
-- Il cancello dei job (85_pgagent/20261016-30)
--   ⚠️ In CI pgAgent non c'e' (85_pgagent e' MARK_RAN): si DICHIARA con skip.
--   La decisione si prova sulle funzioni (dbops/test-processi-accensione-v1).
-- ============================================================
CREATE TEMP TABLE _passi (processo text, jstcode text);

DO $passi$
BEGIN
    IF to_regclass('pgagent.pga_jobstep') IS NOT NULL THEN
        EXECUTE $q$
            INSERT INTO _passi (processo, jstcode)
            SELECT p.codice, s.jstcode
              FROM pgagent.pga_jobstep s
              JOIN pgagent.pga_job j ON j.jobid = s.jstjobid
              JOIN dbops.processi p ON p.jobname_pgagent = j.jobname
             WHERE s.jstkind = 's'
               AND p.obsoleto_dal IS NULL
               AND p.canale <> 'CODA'
        $q$;
    END IF;
END
$passi$;

SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM _passi)
    THEN skip('20. pgAgent non c''e'' o non ha job di processo: si prova dove c''e''', 1)
    ELSE is((SELECT string_agg(processo, ',' ORDER BY processo) FROM _passi
              WHERE jstcode NOT LIKE '%maintenance.fn_sveglia_accesa(%'),
            NULL,
            '20. ogni passo di un job di processo chiede alla sveglia')
END;

SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM _passi)
    THEN skip('21. pgAgent non c''e'' o non ha job di processo: si prova dove c''e''', 1)
    ELSE is((SELECT string_agg(processo, ',' ORDER BY processo) FROM _passi
              WHERE jstcode NOT LIKE '%maintenance.fn_sveglia_accesa(' || quote_literal(processo) || ')%'),
            NULL,
            '21. ... e chiede col proprio codice di processo')
END;

SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM _passi)
    THEN skip('22. pgAgent non c''e'' o non ha job di processo: si prova dove c''e''', 1)
    ELSE is((SELECT string_agg(processo, ',' ORDER BY processo) FROM _passi
              WHERE jstcode ~ 'fn_sveglia_accesa\(.*fn_sveglia_accesa\('),
            NULL,
            '22. nessun passo e'' avvolto due volte')
END;

-- ⭐ Il cancello si prova eseguendo il passo VERO, come farebbe pgAgent, su un
--   processo spento a mano: il lavoro non deve partire, e il giornale non deve
--   avere nessuna corsa nuova. (Il verso «acceso» farebbe girare ANALYZE
--   davvero: lo prova la corsa notturna, non questo test.)
CREATE TEMP TABLE _t0 AS SELECT clock_timestamp() AS t0;

SELECT dbops.fn_imposta_accensione_processo('analyze_statistiche', false, 'pgTAP: prova del cancello');

DO $passo$
DECLARE
    v_codice text;
BEGIN
    SELECT p.jstcode INTO v_codice FROM _passi p WHERE p.processo = 'analyze_statistiche';
    IF v_codice IS NOT NULL THEN
        EXECUTE v_codice;
    END IF;
END
$passo$;

SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM _passi WHERE processo = 'analyze_statistiche')
    THEN skip('23. pgAgent non c''e'' o non ha il job di analyze_statistiche: si prova dove c''e''', 1)
    ELSE is((SELECT count(*)::int FROM maintenance.job_run_log l
              WHERE (l.processo_codice = 'analyze_statistiche' OR l.jobname = 'analyze_statistiche')
                AND l.started_at >= (SELECT t0 FROM _t0)),
            0,
            '23. il passo di un processo spento non lancia il lavoro: nessuna corsa nel giornale')
END;

SELECT * FROM finish();

ROLLBACK;
