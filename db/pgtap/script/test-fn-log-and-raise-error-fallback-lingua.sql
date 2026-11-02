-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_log_and_raise_error - fallback lingua IT su
-- causa/soluzione. Riferimento: migration 20260423-02-02.
--
-- Contesto: la fn solleva RAISE EXCEPTION con DETAIL e HINT recuperati
-- da config.messaggi_errore. Post 23-04-2026 il lookup applica
-- fallback su lingua='it' se la lingua richiesta non ha riga.
-- Il recupero del messaggio testuale e' delegato a fn_get_messaggio
-- (gia' context-aware).
--
-- Indice test (1..3):
--    1. Codice con EN completo (causa + soluzione) -> RAISE con
--       message/DETAIL/HINT in EN
--    2. Codice solo in IT + GUC myapp.user_language='en' -> RAISE con
--       fallback completo IT (message + DETAIL + HINT)
--    3. Codice in EN con causa=NULL -> mantiene riga EN intera
--       (DETAIL vuoto, NO mix con IT)
--
-- pgTAP throws_ok puo' verificare il messaggio (RAISE), ma DETAIL/HINT
-- richiedono cattura del SQLSTATE/MESSAGE/DETAIL/HINT tramite
-- GET DIAGNOSTICS in un BEGIN/EXCEPTION block. Implemento tramite
-- helper temp fn che cattura e ritorna (message, detail, hint).
--
-- Fixture: 2 codici TEST_LR_* inseriti nella tabella messaggi_errore.
-- BEGIN + ROLLBACK isolamento completo.
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

SELECT plan(3);
-- ⚠️ Dal 2026-08-07 `messaggi_errore.codice` ha una FK verso
--   `config.codici_errore`: la FRASE non puo' esistere senza il CODICE. I
--   codici di fixture vanno creati PRIMA, con la loro classe — `classe` e'
--   NOT NULL e senza default, di proposito.
--   Piano: docs/it/dev/work-done/piano-db-classe-codici-errore.md (D-7/D-8)
INSERT INTO config.codici_errore (codice, classe) VALUES
    ('TEST_LR_BOTH', 'DATO_ERRATO'),
    ('TEST_LR_ONLYIT', 'DATO_ERRATO'),
    ('TEST_LR_PARTIAL', 'DATO_ERRATO');


-- =========================================================
-- Setup fixture
-- =========================================================
-- Uso id fissi range 9xxx per evitare collisioni con sequenza
-- autoincrement disallineata su messaggi_errore (ROLLBACK ripulisce).
INSERT INTO config.messaggi_errore (id, codice, lingua, messaggio, causa, soluzione)
VALUES
    (9911, 'TEST_LR_BOTH',    'it', 'Messaggio IT',          'Causa IT',      'Soluzione IT'),
    (9912, 'TEST_LR_BOTH',    'en', 'Message EN',            'Cause EN',      'Solution EN'),
    (9913, 'TEST_LR_ONLYIT',  'it', 'Solo IT',               'Causa IT solo', 'Soluzione IT solo'),
    -- Riga EN "parziale": causa NULL, il resto tradotto. Test 3 verifica
    -- che si mantenga la riga EN intera (no mix con IT).
    (9914, 'TEST_LR_PARTIAL', 'it', 'Messaggio IT parziale', 'Causa IT',      'Soluzione IT'),
    (9915, 'TEST_LR_PARTIAL', 'en', 'Message EN partial',    NULL,            'Solution EN');

-- =========================================================
-- Helper: cattura message/detail/hint di un RAISE EXCEPTION
-- =========================================================
CREATE FUNCTION pg_temp.capture_raise(p_codice text, p_lingua text)
RETURNS TABLE(v_message text, v_detail text, v_hint text)
LANGUAGE plpgsql
AS $fn$
BEGIN
    -- Impone la lingua via GUC; fn_log_and_raise_error la legge.
    PERFORM set_config('myapp.user_language', p_lingua, true);

    BEGIN
        PERFORM script.fn_log_and_raise_error(
            'test',
            'pgtap.capture_raise',
            p_codice,
            '{}'::jsonb,
            NULL::uuid,
            VARIADIC ARRAY[]::text[]
        );
        -- Non dovrebbe mai arrivare qui.
        v_message := NULL; v_detail := NULL; v_hint := NULL;
        RETURN NEXT;
    EXCEPTION
        WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS
                v_message = MESSAGE_TEXT,
                v_detail  = PG_EXCEPTION_DETAIL,
                v_hint    = PG_EXCEPTION_HINT;
            RETURN NEXT;
    END;
END;
$fn$;

-- =========================================================
-- 1) Codice con EN completo -> RAISE in EN (message + DETAIL + HINT)
-- =========================================================
SELECT is(
    (SELECT ROW(v_message, v_detail, v_hint)::text FROM pg_temp.capture_raise('TEST_LR_BOTH', 'en')),
    ROW('Message EN', 'Cause EN', 'Solution EN')::text,
    '1. Codice con EN completo -> RAISE message/DETAIL/HINT in EN'
);

-- =========================================================
-- 2) Codice solo in IT + lingua=en -> fallback IT su tutti i campi
-- =========================================================
SELECT is(
    (SELECT ROW(v_message, v_detail, v_hint)::text FROM pg_temp.capture_raise('TEST_LR_ONLYIT', 'en')),
    ROW('Solo IT', 'Causa IT solo', 'Soluzione IT solo')::text,
    '2. Codice solo in IT + lingua=en -> fallback completo IT'
);

-- =========================================================
-- 3) Codice con EN ma causa=NULL -> mantieni riga EN intera
-- DETAIL vuoto (coalesce(NULL, '') = ''), HINT = Solution EN.
-- Il messaggio resta Message EN partial (non Messaggio IT parziale).
-- =========================================================
SELECT is(
    (SELECT ROW(v_message, v_detail, v_hint)::text FROM pg_temp.capture_raise('TEST_LR_PARTIAL', 'en')),
    ROW('Message EN partial', '', 'Solution EN')::text,
    '3. Codice EN con causa=NULL -> riga EN intera (DETAIL vuoto, no mix con IT)'
);

SELECT * FROM finish();
ROLLBACK;
