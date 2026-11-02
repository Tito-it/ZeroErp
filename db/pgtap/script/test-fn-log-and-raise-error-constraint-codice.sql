-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_log_and_raise_error — il CODICE di dominio esce nel campo
-- strutturato CONSTRAINT dell'eccezione. Riferimento: migration 20260805-05.
-- Brief: docs/it/dev/work-done/brief-db-codice-errore-strutturato.md
--
-- Contesto: prima del 05-08-2026 il codice non partiva in nessun campo
-- dell'eccezione. Arrivava lo stesso al backend nel 91% dei casi, ma perche'
-- il driver allega al testo anche lo STATEMENT CHIAMANTE, dove il codice e'
-- scritto a mano: il backend lo pescava dal sorgente della chiamata, non dal
-- dato. Funzionava finche' il codice era un letterale; per le nove guard che
-- lo passano da espressione (`v_motivi -> 0 ->> 'codice'`) non funzionava, e
-- l'operatore non leggeva perche' la sua transizione fosse vietata.
--
-- CONTRATTO ASSERITO QUI:
--   «SQLSTATE P0001 + CONSTRAINT valorizzato = errore di dominio, e il
--    contenuto di CONSTRAINT e' il codice di config.messaggi_errore»
-- L'altra meta' del contratto — che nessun ALTRO RAISE scriva quel campo —
-- non e' asseribile qui: sta in scripts/sql/guardrail_codice_errore_strutturato.sql.
--
-- Indice test (1..5):
--    1. CONSTRAINT = codice passato, e SQLSTATE = P0001
--    2. Nessuna regressione: DETAIL/HINT restano causa/soluzione
--    3. ⚠️ Contratto NEGATIVO: il codice NON compare nel messaggio
--    4. Il campo sopravvive annidato + a un `EXCEPTION ... RAISE;`
--    5. Codice NON a seed: il messaggio degrada a placeholder, il CONSTRAINT
--       porta il codice lo stesso (i due canali sono indipendenti)
--
-- ⚠️ I test 1..4 girano su un codice PRESENTE a seed (fixture). Su un codice
-- mancante scatterebbe il placeholder di fn_get_messaggio, che il codice ce lo
-- mette nel testo: il test passerebbe per il motivo sbagliato — lo stesso
-- inganno di test-fn-crea-auth-user (brief BE §4). Il caso "assente" e'
-- isolato apposta nel test 5, dove e' il soggetto e non lo sfondo.
--
-- ⚠️ Nota di copertura: `pg_temp.capture_*` passa il codice come PARAMETRO,
-- non come letterale nella chiamata. E' voluto: e' la forma del gruppo C, cioe'
-- quella che il vecchio meccanismo non copriva. Un test scritto col letterale
-- passerebbe anche senza la modifica, pescandolo dal testo dello statement.
--
-- Fixture: 1 codice TEST_CN_* inserito in messaggi_errore. BEGIN + ROLLBACK.
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

SELECT plan(5);
-- ⚠️ Dal 2026-08-07 `messaggi_errore.codice` ha una FK verso
--   `config.codici_errore`: la FRASE non puo' esistere senza il CODICE. I
--   codici di fixture vanno creati PRIMA, con la loro classe — `classe` e'
--   NOT NULL e senza default, di proposito.
--   Piano: docs/it/dev/work-done/piano-db-classe-codici-errore.md (D-7/D-8)
INSERT INTO config.codici_errore (codice, classe) VALUES
    ('TEST_CN_SEEDED', 'DATO_ERRATO');


-- =========================================================
-- Setup fixture
-- =========================================================
-- Id fissi range 9xxx: la sequenza di messaggi_errore e' disallineata rispetto
-- ai valori inseriti a mano dai seed (stessa scelta di
-- test-fn-log-and-raise-error-fallback-lingua.sql). Il ROLLBACK ripulisce.
--
-- Il messaggio NON contiene il codice: e' esattamente cio' che il test 3
-- verifica lato eccezione, e una fixture che lo contenesse renderebbe quel
-- test cieco.
INSERT INTO config.messaggi_errore (id, codice, lingua, messaggio, causa, soluzione)
VALUES (9921, 'TEST_CN_SEEDED', 'it',
        'Operazione non ammessa nello stato corrente.',
        'La transizione richiesta non e'' prevista.',
        'Riportare il documento in uno stato compatibile.');

-- =========================================================
-- Helper: cattura i campi diagnostici di un RAISE EXCEPTION
-- =========================================================
-- Rispetto all'helper di test-fn-log-and-raise-error-fallback-lingua.sql qui
-- servono anche RETURNED_SQLSTATE e CONSTRAINT_NAME, che sono i due campi su
-- cui poggia il contratto.
CREATE FUNCTION pg_temp.capture_diag(p_codice text)
RETURNS TABLE(v_sqlstate text, v_constraint text, v_message text, v_detail text, v_hint text)
LANGUAGE plpgsql
AS $fn$
BEGIN
    PERFORM set_config('myapp.user_language', 'it', true);

    BEGIN
        PERFORM script.fn_log_and_raise_error(
            'test',
            'pgtap.capture_diag',
            p_codice,
            '{}'::jsonb,
            NULL::uuid,
            VARIADIC ARRAY[]::text[]
        );
        -- Non dovrebbe mai arrivare qui: la funzione solleva sempre.
        v_sqlstate := NULL; v_constraint := NULL;
        v_message  := NULL; v_detail := NULL; v_hint := NULL;
        RETURN NEXT;
    EXCEPTION
        WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS
                v_sqlstate   = RETURNED_SQLSTATE,
                v_constraint = CONSTRAINT_NAME,
                v_message    = MESSAGE_TEXT,
                v_detail     = PG_EXCEPTION_DETAIL,
                v_hint       = PG_EXCEPTION_HINT;
            RETURN NEXT;
    END;
END;
$fn$;

-- Helper per il test 4: due livelli PL/pgSQL, con quello interno che cattura e
-- RI-SOLLEVA con `RAISE;` nudo. E' il percorso reale — trigger -> guard ->
-- helper — non una condizione di laboratorio.
CREATE FUNCTION pg_temp.capture_diag_annidato(p_codice text)
RETURNS TABLE(v_sqlstate text, v_constraint text)
LANGUAGE plpgsql
AS $fn$
BEGIN
    PERFORM set_config('myapp.user_language', 'it', true);

    BEGIN
        BEGIN
            PERFORM script.fn_log_and_raise_error(
                'test', 'pgtap.capture_diag_annidato', p_codice,
                '{}'::jsonb, NULL::uuid, VARIADIC ARRAY[]::text[]
            );
        EXCEPTION WHEN OTHERS THEN
            -- Ri-sollevamento nudo: il campo deve attraversarlo intatto.
            RAISE;
        END;
        v_sqlstate := NULL; v_constraint := NULL;
        RETURN NEXT;
    EXCEPTION
        WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS
                v_sqlstate   = RETURNED_SQLSTATE,
                v_constraint = CONSTRAINT_NAME;
            RETURN NEXT;
    END;
END;
$fn$;

-- =========================================================
-- 1) CONSTRAINT porta il codice, SQLSTATE resta P0001
-- =========================================================
-- Le due meta' del contratto vanno asserite INSIEME: il backend si fida del
-- campo solo su P0001, perche' su una violazione di vincolo vera (classe 23xxx)
-- `constraint_name` contiene il nome del vincolo DB (`uq_...`, `fk_...`).
-- Asserire il solo CONSTRAINT lascerebbe passare un cambio di ERRCODE che
-- renderebbe il campo illeggibile lato Python.
SELECT is(
    (SELECT ROW(v_sqlstate, v_constraint)::text FROM pg_temp.capture_diag('TEST_CN_SEEDED')),
    ROW('P0001', 'TEST_CN_SEEDED')::text,
    '1. CONSTRAINT = codice di dominio e SQLSTATE = P0001'
);

-- =========================================================
-- 2) Nessuna regressione su DETAIL/HINT
-- =========================================================
-- Il campo nuovo si aggiunge, non sostituisce: causa e soluzione continuano a
-- viaggiare dove viaggiavano.
SELECT is(
    (SELECT ROW(v_detail, v_hint)::text FROM pg_temp.capture_diag('TEST_CN_SEEDED')),
    ROW('La transizione richiesta non e'' prevista.',
        'Riportare il documento in uno stato compatibile.')::text,
    '2. DETAIL/HINT restano causa/soluzione (nessuna regressione)'
);

-- =========================================================
-- 3) ⚠️ Contratto NEGATIVO: il codice non sta nel messaggio
-- =========================================================
-- Il messaggio e' per l'operatore, il codice e' per il backend: sono due
-- destinatari diversi e viaggiano su due canali diversi. Senza questa
-- asserzione, fra sei mesi qualcuno "aiuta" mettendo il codice nel testo per
-- farlo trovare piu' facilmente, e la scelta si perde senza che nulla diventi
-- rosso — che e' il modo in cui le decisioni di progetto muoiono.
SELECT ok(
    (SELECT v_message NOT LIKE '%TEST_CN_SEEDED%' FROM pg_temp.capture_diag('TEST_CN_SEEDED')),
    '3. Il codice NON compare nel messaggio: il messaggio e'' per l''utente'
);

-- =========================================================
-- 4) Il campo sopravvive all'annidamento e al ri-sollevamento
-- =========================================================
-- E' la condizione che rende utile tutta la slice: in produzione la funzione
-- non viene mai chiamata dal livello piu' esterno, ma da un trigger dentro una
-- guard. Se il campo si perdesse per strada, il backend continuerebbe a
-- ricevere il nulla e nessuno se ne accorgerebbe dai test 1..3.
SELECT is(
    (SELECT ROW(v_sqlstate, v_constraint)::text FROM pg_temp.capture_diag_annidato('TEST_CN_SEEDED')),
    ROW('P0001', 'TEST_CN_SEEDED')::text,
    '4. CONSTRAINT intatto attraverso due livelli PL/pgSQL e un RAISE; nudo'
);

-- =========================================================
-- 5) Codice non a seed: i due canali sono indipendenti
-- =========================================================
-- Qui il messaggio degrada al placeholder di fn_get_messaggio — che il codice
-- ce lo mette dentro, ed e' il vecchio meccanismo. Il punto del test e' che il
-- CONSTRAINT lo porti COMUNQUE: il trasporto del codice non deve dipendere
-- dalla presenza della riga a seed, altrimenti il caso peggiore (codice
-- sconosciuto) resterebbe l'unico servito dal parsing del testo.
SELECT is(
    (SELECT v_constraint FROM pg_temp.capture_diag('TEST_CN_ASSENTE')),
    'TEST_CN_ASSENTE',
    '5. Codice non a seed: messaggio placeholder, ma CONSTRAINT valorizzato lo stesso'
);

SELECT * FROM finish();
ROLLBACK;
