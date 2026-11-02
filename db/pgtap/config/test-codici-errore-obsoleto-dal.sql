-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.codici_errore.obsoleto_dal — il ritiro di un codice errore
-- NON tocca il runtime. Riferimento: 20260805-17 (nascita), 20260807-13 (trasloco).
-- Brief: docs/it/dev/work-done/brief-db-codice-errore-strutturato.md §15
--
-- ⚠️ LA COLONNA HA CAMBIATO CASA il 2026-08-07, e questo test con lei.
--   Nasceva su `config.messaggi_errore`, che pero' e' chiavata (codice, lingua):
--   il ritiro era **per lingua**, cioe' si poteva ritirare un codice in italiano
--   e lasciarlo vivo in inglese. Ora sta su `config.codici_errore` — una riga per
--   codice — e il difetto non e' piu' esprimibile.
--   Piano: docs/it/dev/work-done/piano-db-classe-codici-errore.md (D-6/D-8)
--
-- Contesto: un codice legacy spesso non si puo' cancellare, perche'
-- dbops.error_log ha una FK NOT NULL verso config.messaggi_errore(id) e 46
-- codici su 53 hanno righe di log. Si ritira quindi valorizzando `obsoleto_dal`.
--
-- ⚠️ COSA QUESTO TEST PRESIDIA, ed e' il punto dell'intera colonna:
-- `obsoleto_dal` e' un asse per il PRESIDIO, non un interruttore di runtime.
-- Un codice ritirato **continua a risolversi**: finche' un percorso non ancora
-- bonificato lo solleva, l'operatore deve leggere una frase e non
-- `[MESSAGGIO NON DEFINITO: ...]`. E' la differenza fra `obsoleto_dal` e
-- `attivo` — confonderle e' l'errore che la guida sulla deprecabilita' del
-- catalogo mette in guardia di non fare, perche' `attivo = false` romperebbe i
-- riferimenti esistenti.
--
-- Senza questo test, la prima persona che "ottimizza" mettendo un
-- `AND obsoleto_dal IS NULL` dentro fn_get_messaggio spegne i messaggi di 46
-- codici ancora vivi, e nulla diventa rosso.
--
-- L'altra meta' del contratto — che nessuno vivo sollevi un codice ritirato —
-- non e' asseribile qui: sta nel controllo (D) di
-- scripts/sql/guardrail_codice_errore_strutturato.sql.
-- ⚠️ E dal 2026-09-23 quel controllo guarda DUE superfici, non una: i letterali
--   nei corpi plpgsql E gli argomenti dei trigger (pg_trigger.tgargs). La
--   seconda mancava, e dietro c'erano 69 trigger che sollevavano
--   CODICE_NON_MODIFICABILE — ritirato il 2026-08-05 — con il guardrail verde:
--   script.trgfn_lock_columns e' una funzione GENERICA, il codice le arriva come
--   TG_ARGV e in pg_proc non c'e'. Bonifica: 90_end/20260923-02.
--   Brief: brief-db-codici-ritirati-negli-argomenti-dei-trigger.
--
-- Indice test (1..4):
--    1. La colonna esiste, e' DATE ed e' nullable (NULL = in servizio)
--    2. fn_get_messaggio risolve un codice RITIRATO (nessun placeholder)
--    3. fn_log_and_raise_error solleva col messaggio localizzato, e con
--       DETAIL/HINT e CONSTRAINT intatti
--    4. Un codice ritirato NON e' distinguibile a runtime da uno in servizio:
--       stesso messaggio a parita' di template
--
-- Fixture: 2 codici TEST_OBS_* (uno ritirato, uno in servizio) con lo stesso
-- template. BEGIN + ROLLBACK.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- =========================================================
-- Setup fixture
-- =========================================================
-- Id fissi range 9xxx: la sequenza di messaggi_errore e' disallineata rispetto
-- ai valori inseriti a mano dai seed. Il ROLLBACK ripulisce.
-- ⚠️ Prima il CODICE, poi la FRASE: la FK del 20260807-14 non ammette l'ordine
--   inverso. Il ritiro sta sul codice, non sul messaggio.
INSERT INTO config.codici_errore (codice, classe, obsoleto_dal)
VALUES
    ('TEST_OBS_RITIRATO',    'CONFLITTO_STATO', DATE '2026-01-01'),
    ('TEST_OBS_IN_SERVIZIO', 'CONFLITTO_STATO', NULL);

INSERT INTO config.messaggi_errore (id, codice, lingua, messaggio, causa, soluzione)
VALUES
    (9931, 'TEST_OBS_RITIRATO',   'it', 'Operazione non ammessa.',
     'La causa.', 'La soluzione.'),
    (9932, 'TEST_OBS_IN_SERVIZIO','it', 'Operazione non ammessa.',
     'La causa.', 'La soluzione.');

-- Helper: cattura messaggio e campi diagnostici di fn_log_and_raise_error.
CREATE FUNCTION pg_temp.capture_obs(p_codice text)
RETURNS TABLE(v_message text, v_detail text, v_hint text, v_constraint text)
LANGUAGE plpgsql
AS $fn$
BEGIN
    PERFORM set_config('myapp.user_language', 'it', true);
    BEGIN
        PERFORM script.fn_log_and_raise_error(
            'test', 'pgtap.capture_obs', p_codice,
            '{}'::jsonb, NULL::uuid, VARIADIC ARRAY[]::text[]
        );
        v_message := NULL; v_detail := NULL; v_hint := NULL; v_constraint := NULL;
        RETURN NEXT;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS
            v_message    = MESSAGE_TEXT,
            v_detail     = PG_EXCEPTION_DETAIL,
            v_hint       = PG_EXCEPTION_HINT,
            v_constraint = CONSTRAINT_NAME;
        RETURN NEXT;
    END;
END;
$fn$;

-- =========================================================
-- 1) La colonna e' come dichiarata
-- =========================================================
-- Nullable non e' un dettaglio: NULL significa «in servizio», e lo hanno 610
-- righe su 689. Un NOT NULL con default costringerebbe a inventare una data
-- per i codici vivi.
--
-- ⚠️ E l'asserzione dice DUE cose: che la colonna c'e' nella casa nuova E che
--   NON e' rimasta in quella vecchia. Un trasloco a meta' — colonna in
--   entrambe — sarebbe la peggiore delle tre situazioni: due sorgenti di
--   verita' che nessun vincolo tiene insieme.
SELECT is(
    (SELECT string_agg(table_name || ':' || data_type || '/' || is_nullable, ' + ' ORDER BY table_name)
       FROM information_schema.columns
      WHERE table_schema = 'config'
        AND table_name IN ('messaggi_errore', 'codici_errore')
        AND column_name = 'obsoleto_dal'),
    'codici_errore:date/YES',
    '1. obsoleto_dal e'' su codici_errore (DATE, nullable) e NON e'' piu'' su messaggi_errore'
);

-- =========================================================
-- 2) ⚠️ Un codice ritirato si risolve ancora
-- =========================================================
-- Se un giorno qualcuno filtrasse per obsoleto_dal dentro fn_get_messaggio,
-- qui tornerebbe '[MESSAGGIO NON DEFINITO: TEST_OBS_RITIRATO]'.
SELECT is(
    script.fn_get_messaggio('TEST_OBS_RITIRATO', NULL, 'it'),
    'Operazione non ammessa.',
    '2. fn_get_messaggio risolve un codice RITIRATO (nessun placeholder)'
);

-- =========================================================
-- 3) E anche il sollevamento resta intatto
-- =========================================================
-- Messaggio localizzato, causa, soluzione e il campo strutturato col codice:
-- un codice ritirato che scatta deve dire all'operatore *cosa* e' successo,
-- non degradare a errore tecnico.
SELECT is(
    (SELECT ROW(v_message, v_detail, v_hint, v_constraint)::text
       FROM pg_temp.capture_obs('TEST_OBS_RITIRATO')),
    ROW('Operazione non ammessa.', 'La causa.', 'La soluzione.', 'TEST_OBS_RITIRATO')::text,
    '3. fn_log_and_raise_error: messaggio, DETAIL/HINT e CONSTRAINT intatti su un codice ritirato'
);

-- =========================================================
-- 4) Ritirato e in servizio sono indistinguibili a runtime
-- =========================================================
-- E' il contratto detto in positivo: a parita' di template, il ritiro non
-- cambia NIENTE di cio' che l'utente vede. La colonna la legge solo la CI.
SELECT is(
    script.fn_get_messaggio('TEST_OBS_RITIRATO', NULL, 'it'),
    script.fn_get_messaggio('TEST_OBS_IN_SERVIZIO', NULL, 'it'),
    '4. a runtime un codice ritirato e uno in servizio si comportano identici'
);

SELECT * FROM finish();
ROLLBACK;
