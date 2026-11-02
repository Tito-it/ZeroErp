-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture deve RETRODATARE righe di config.email_log
--   (data_insert, prossimo_tentativo) e cambiarne lo stato a mano — scritture
--   che l'applicazione non fa e che la policy di ambito SISTEMA non ammette a
--   un operatore. E le righe di sistema si RILEGGONO solo da owner: e' la
--   stessa situazione di db/pgtap/config/test-fn-email-sistema.sql. ⭐ Che
--   l'operatore NON le veda e' provato dove va provato
--   (db/pgtap/rls/test-rls-email-log-ambito.sql); che il digest le CONTI
--   lo stesso e' il test 8, da proprietario, com'e' il conteggio vero.
--
-- Test: dbops.vw_email_da_guardare — le email che restano in coda, e
--       config.vw_email_in_coda — la definizione unica di «in coda»
-- ChangeSet: 20260911-10 / -11
-- Brief: brief-db-quattro-processi-senza-presidio §5 · §10.1 (D3)
--
-- Elenco test (plan 8):
--  1) ⛔ PENDING da oltre un'ora compare: il cron NON sta girando
--  2) ⛔ FAILED ripescabile, dovuto da oltre un'ora, compare — e il motivo lo dice
--  3) ✅ RETRY con il prossimo tentativo nel FUTURO non compare: il backoff e'
--     legittimo, e non e' nemmeno «in coda»
--  4) ✅ FAILED TERMINALE (tentativi esauriti) non compare, e non e' in coda
--  5) ✅ PENDING appena accodata non compare, MA e' in coda: la soglia esiste
--  6) ✅ SENT e SIMULATA non sono in coda
--  7) ⭐ `dovuta_dal` misura da quando la riga era DOVUTA, non da quando e' nata
--  8) ⭐ fn_conta_presidio la conta da proprietario: il digest non e' cieco
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 2 E' LA RAGIONE PER CUI LA DEFINIZIONE STA NEL DATABASE.
--   Il brief chiedeva PENDING e RETRY. Ma send_pending_emails ripesca anche i
--   FAILED con tentativi residui — e' il recupero — e un presidio che non li
--   vede tace proprio sulla mail che il cron avrebbe potuto salvare. Scritta
--   una volta in config.vw_email_in_coda, la definizione la leggono in due.
--
-- ⚠️ Le date si scrivono a mano, indietro nel tempo: la soglia e' una regola
--   sul dato, e si prova sul dato. config.email_log non ha un audit trigger
--   su data_insert, quindi l'UPDATE da owner basta.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Fixture: sei righe di sistema, una per caso, riconoscibili dall'oggetto
-- ============================================================
-- ⭐ Si passa dalla porta di sistema (fn_accoda_email_sistema): non servono
--   anagrafiche ne' emittenti, quindi la fixture si costruisce anche su un
--   database ricostruito da zero.
DO $fixture$
DECLARE
    v_id config.email_log.id%TYPE;
BEGIN
    -- 1) mai presa in mano: il cron non gira
    v_id := config.fn_accoda_email_sistema('a@example.invalid', 'pgtap:pending_vecchia', '<p/>');
    UPDATE config.email_log SET data_insert = now() - interval '2 hours' WHERE id = v_id;

    -- 2) fallita, ha tentativi residui, il ritentativo era dovuto due ore fa
    v_id := config.fn_accoda_email_sistema('b@example.invalid', 'pgtap:failed_ripescabile', '<p/>');
    UPDATE config.email_log
       SET stato = 'FAILED', tentativi = 1, max_tentativi = 3,
           prossimo_tentativo = now() - interval '2 hours',
           data_insert = now() - interval '3 hours'
     WHERE id = v_id;

    -- 3) in RETRY, ma il prossimo tentativo e' fra dieci minuti: backoff
    v_id := config.fn_accoda_email_sistema('c@example.invalid', 'pgtap:retry_non_dovuto', '<p/>');
    UPDATE config.email_log
       SET stato = 'RETRY', tentativi = 1, max_tentativi = 3,
           prossimo_tentativo = now() + interval '10 minutes',
           data_insert = now() - interval '3 hours'
     WHERE id = v_id;

    -- 4) fallita per sempre: tentativi esauriti
    v_id := config.fn_accoda_email_sistema('d@example.invalid', 'pgtap:failed_terminale', '<p/>');
    UPDATE config.email_log
       SET stato = 'FAILED', tentativi = 3, max_tentativi = 3,
           prossimo_tentativo = now() - interval '2 hours',
           data_insert = now() - interval '3 hours'
     WHERE id = v_id;

    -- 5) appena accodata: e' normale
    PERFORM config.fn_accoda_email_sistema('e@example.invalid', 'pgtap:pending_fresca', '<p/>');

    -- 6) consegnata, e simulata: chiuse
    v_id := config.fn_accoda_email_sistema('f@example.invalid', 'pgtap:sent', '<p/>');
    PERFORM config.fn_chiudi_email_sistema(v_id, 'SENT', NULL, now());
    UPDATE config.email_log SET data_insert = now() - interval '3 hours' WHERE id = v_id;
    v_id := config.fn_accoda_email_sistema('g@example.invalid', 'pgtap:simulata', '<p/>');
    PERFORM config.fn_chiudi_email_sistema(v_id, 'SIMULATA');
    UPDATE config.email_log SET data_insert = now() - interval '3 hours' WHERE id = v_id;
END
$fixture$;

-- ============================================================
-- 1..2. ⛔ I due guasti, e i due motivi
-- ============================================================
-- ⭐ Il caso che conta di piu' e si vede di meno: un cron spento non produce
--   errori, produce ASSENZA.
SELECT is(
    (SELECT motivo FROM dbops.vw_email_da_guardare
      WHERE oggetto = 'pgtap:pending_vecchia'),
    'mai presa in mano: send_pending_emails non sta girando',
    '1. PENDING da oltre un''ora compare: il cron non sta girando'
);

-- ⭐ La riga che il brief non avrebbe visto.
SELECT is(
    (SELECT motivo FROM dbops.vw_email_da_guardare
      WHERE oggetto = 'pgtap:failed_ripescabile'),
    'ritentativo dovuto e mai eseguito',
    '2. FAILED con tentativi residui, dovuta da oltre un''ora, compare — e'' il recupero che nessuno fa'
);

-- ============================================================
-- 3..6. ✅ Cio' che NON deve comparire — e cio' che non e' in coda
-- ============================================================
-- ⚠️ Due asserzioni in una: NON nel presidio, e NON in coda. Il backoff non e'
--   un ritardo, e la riga non e' nemmeno dovuta.
SELECT is(
    (SELECT count(*) FROM (
        SELECT id FROM dbops.vw_email_da_guardare WHERE oggetto = 'pgtap:retry_non_dovuto'
        UNION ALL
        SELECT id FROM config.vw_email_in_coda WHERE oggetto = 'pgtap:retry_non_dovuto') q),
    0::bigint,
    '3. RETRY col prossimo tentativo nel futuro: ne'' in coda ne'' nel presidio'
);

SELECT is(
    (SELECT count(*) FROM (
        SELECT id FROM dbops.vw_email_da_guardare WHERE oggetto = 'pgtap:failed_terminale'
        UNION ALL
        SELECT id FROM config.vw_email_in_coda WHERE oggetto = 'pgtap:failed_terminale') q),
    0::bigint,
    '4. FAILED con i tentativi esauriti: e'' terminale, non e'' in coda e non e'' nel presidio'
);

-- ⭐ In coda SI', nel presidio NO: e' la prova che la soglia esiste davvero
--   e che le due viste dicono due cose diverse.
SELECT is(
    (SELECT (EXISTS (SELECT 1 FROM config.vw_email_in_coda WHERE oggetto = 'pgtap:pending_fresca'))::text
         || '/' ||
            (EXISTS (SELECT 1 FROM dbops.vw_email_da_guardare WHERE oggetto = 'pgtap:pending_fresca'))::text),
    'true/false',
    '5. PENDING appena accodata: in coda si'', da guardare no — la soglia esiste'
);

SELECT is_empty(
    $$SELECT id FROM config.vw_email_in_coda
       WHERE oggetto IN ('pgtap:sent', 'pgtap:simulata')$$,
    '6. SENT e SIMULATA non sono in coda: sono chiuse'
);

-- ============================================================
-- 7. ⭐ dovuta_dal: da quando la riga era DOVUTA
-- ============================================================
-- Per PENDING e' data_insert; per FAILED/RETRY e' prossimo_tentativo. Senza,
-- un RETRY appena schedulato con backoff di un giorno risulterebbe «in ritardo
-- da un giorno» il minuto dopo.
SELECT is(
    (SELECT (c.dovuta_dal = l.prossimo_tentativo)::text
       FROM config.vw_email_in_coda c
       JOIN config.email_log l ON l.id = c.id
      WHERE c.oggetto = 'pgtap:failed_ripescabile'),
    'true',
    '7. su una riga FAILED dovuta_dal e'' il prossimo tentativo, non la nascita'
);

-- ============================================================
-- 8. ⭐ Il digest non e' cieco
-- ============================================================
-- ⛔ La vista e' security_invoker su una tabella in RLS: un command senza veste
--   vedrebbe ZERO. fn_conta_presidio conta da proprietario, ed e' il percorso
--   che il digest usa. Qui il test gira da owner, quindi conta almeno le DUE
--   righe della fixture (piu' quelle vere, se ci sono).
SELECT cmp_ok(
    dbops.fn_conta_presidio('dbops.vw_email_da_guardare'), '>=', 2::bigint,
    '8. fn_conta_presidio conta le email da guardare: almeno le due della fixture'
);

SELECT * FROM finish();

ROLLBACK;
