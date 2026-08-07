-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.messaggi_errore.obsoleto_dal — il ritiro di un codice errore
-- NON tocca il runtime. Riferimento: migration 20260805-17.
-- Brief: docs/it/dev/work-done/brief-db-codice-errore-strutturato.md §15
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
-- L'altra meta' del contratto — che nessuna funzione viva sollevi un codice
-- ritirato — non e' asseribile qui: sta nel controllo (D) di
-- scripts/sql/guardrail_codice_errore_strutturato.sql.
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
INSERT INTO config.messaggi_errore (id, codice, lingua, messaggio, causa, soluzione, obsoleto_dal)
VALUES
    (9931, 'TEST_OBS_RITIRATO',   'it', 'Operazione non ammessa.',
     'La causa.', 'La soluzione.', DATE '2026-01-01'),
    (9932, 'TEST_OBS_IN_SERVIZIO','it', 'Operazione non ammessa.',
     'La causa.', 'La soluzione.', NULL);

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
-- Nullable non e' un dettaglio: NULL e' il valore che significa «in servizio»,
-- e lo hanno 631 righe su 632. Un NOT NULL con default costringerebbe a
-- inventare una data per i codici vivi.
SELECT is(
    (SELECT data_type || '/' || is_nullable
       FROM information_schema.columns
      WHERE table_schema = 'config' AND table_name = 'messaggi_errore'
        AND column_name = 'obsoleto_dal'),
    'date/YES',
    '1. obsoleto_dal esiste, e'' DATE ed e'' nullable'
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
