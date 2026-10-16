-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.processi, catalogo che a
--   runtime non scrive nessuno (lo popola il mirror CSV di 80_data) e su cui il
--   ruolo applicativo ha SELECT-only. Verificato cercando gli scrittori.
--
-- Test: il canale CODA_AUTOMATICA (R-E, strada B)
-- Brief: brief-db-processi-automatici-residui-be.md, sezione 1-quater
--
-- Elenco test (plan 6):
--  1) il CHECK ammette CODA_AUTOMATICA
--  2) e respinge un refuso vicino: il vocabolario resta chiuso
--  3) ⭐ vw_processi_dominio_senza_identita lo NOMINA (prima lo ignorava)
--  4) ⭐ vw_emittenti_non_serviti lo conta per ogni emittente attivo
--  5) ✅ la fabbrica lo SERVE
--  6) ⛔ il canale CODA «umano» resta rifiutato dalla fabbrica
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ COSA SI STA CORREGGENDO, ed e' un'assunzione nostra.
--
-- I presidi del cantiere davano per scontato che un processo su canale `CODA`
-- portasse con se' l'identita' di CHI LO HA ACCODATO — perche' chi accoda e'
-- una persona. Vale per i due giri di fatturazione. NON varra' per la chiusura
-- scadenze, che a metterla in coda sara' una sveglia: e una sveglia non ha un
-- nome da prestare.
--
-- ⭐ Si e' scartata la strada A (un processo «produttore» piu' uno
--   «esecutore»): avrebbe messo a catalogo DUE voci per UN lavoro solo, per far
--   quadrare un controllo scritto da noi. Il registro esiste per rispondere
--   «che cosa fa il sistema da solo»: spaccare la risposta in due sarebbe
--   adattare il modello al presidio.
--
-- ⭐ I test 3, 4 e 5 vanno letti INSIEME, ed e' il motivo per cui stanno in un
--   file solo: se i presidi nominassero un processo che la fabbrica si rifiuta
--   di servire, avremmo un presidio che chiede l'impossibile — peggio di un
--   presidio assente, perche' si impara a ignorarlo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ `SET CONSTRAINTS ALL IMMEDIATE` sta DOPO la fixture della fabbrica: quella
--   crea il soggetto in un'istruzione e il suo contatto in quella dopo, e il
--   guard sui contatti e' DIFFERITO. In testa scatterebbe a meta' strada.
--   ⛔ E LA FINESTRA SI DICHIARA: la riga di contesto qui sopra esce con i
--   vincoli IMMEDIATE quando COSTRUISCE il mondo (rev 20260921-18, come ogni
--   helper pgTAP) — cioe' sul database da zero. Li' questo file moriva nel
--   test 5 su «Il soggetto non ha contatti validi» (scratch `zeroerp_ci`,
--   2026-09-22: rosso che la CI non conosceva; provato in transazione
--   ritirata nei due modi — IMMEDIATE rifiutato, DEFERRED servito). Su dev un
--   operatore c'e' sempre, il ramo non si percorre e la finestra di DEFAULT
--   mascherava il difetto: terzo file con la forma di
--   anagrafiche/create-cliente e test-soggetti-split-payment-cliente-pa.
--   Contare sulla finestra di DEFAULT e' contare su cio' che nessuno ha
--   promesso: la si riapre, e il file dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(6);

-- ============================================================
-- 1..2. Il vocabolario
-- ============================================================
SELECT lives_ok(
    -- 20261016-20: CODA_AUTOMATICA ha una sveglia, quindi dichiara l'accensione.
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                  acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento)
      VALUES (9801, 'PGTAP-CODA-AUTO',
              'processo di dominio che passa dalla coda ma lo accoda una macchina',
              'DOMINIO', 'CODA_AUTOMATICA', true, true, true, 'PROGRAMMA')$$,
    '1. il CHECK ammette CODA_AUTOMATICA'
);

-- ⚠️ Non basta provare che il valore nuovo entri: un CHECK riscritto male —
--   per esempio sostituito da un `canale IS NOT NULL` — passerebbe il test 1 e
--   lascerebbe entrare qualunque stringa. Il vocabolario dev'essere CHIUSO.
SELECT throws_ok(
    -- ⚠️ 20261016-20: la riga dichiara l'accensione, altrimenti il 23514
    --   verrebbe da chk_processi_accensione e il test sarebbe verde per il
    --   vincolo sbagliato.
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                  acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento)
      VALUES (9802, 'PGTAP-CODA-REFUSO', 'un refuso vicino al valore buono',
              'DOMINIO', 'CODA_AUTOMATIC', true, true, true, 'PROGRAMMA')$$,
    '23514',
    NULL,
    '2. e respinge un refuso vicino: il vocabolario resta chiuso'
);

-- ============================================================
-- 3..4. I presidi smettono di ignorare la coda
-- ============================================================
-- ⭐ Prima di oggi questa riga NON compariva: il filtro guardava solo PGAGENT e
--   COMMAND, cioe' «la coda si arrangia».
SELECT is(
    (SELECT motivo FROM dbops.vw_processi_dominio_senza_identita
      WHERE processo_codice = 'PGTAP-CODA-AUTO'),
    'processo DOMINIO headless senza utente tecnico',
    '3. il presidio delle identita'' nomina un processo CODA_AUTOMATICA scoperto'
);

-- ⚠️ Il conteggio si confronta col numero di emittenti ATTIVI, non con una
--   costante: la vista risponde «per quali coppie manca un utente», e su un
--   database con tre aziende la risposta e' tre.
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_emittenti_non_serviti
      WHERE processo_codice = 'PGTAP-CODA-AUTO'),
    (SELECT count(*)::int FROM anagrafiche.emittenti_fiscali WHERE attivo),
    '4. e il presidio degli emittenti lo conta per ogni azienda attiva'
);

-- ============================================================
-- 5..6. La fabbrica, nei due versi
-- ============================================================
DO $fabbrica$
DECLARE
    v_ef anagrafiche.emittenti_fiscali.codice%TYPE;
BEGIN
    -- Ordine stabile: una fixture che pesca a caso non verifica, scommette.
    SELECT codice INTO v_ef FROM anagrafiche.emittenti_fiscali
     WHERE attivo ORDER BY id LIMIT 1;

    IF v_ef IS NULL THEN
        PERFORM set_config('pgtap.esito5', 'skip', true);
    ELSE
        BEGIN
            PERFORM script.fn_crea_utente_tecnico('PGTAP-CODA-AUTO', v_ef);
            PERFORM set_config('pgtap.esito5', 'servito', true);
        EXCEPTION WHEN OTHERS THEN
            PERFORM set_config('pgtap.esito5',
                               'rifiutato: ' || left(SQLERRM, 60), true);
        END;
    END IF;
END
$fabbrica$;

-- Unita' di lavoro completa: da qui i vincoli differiti devono scattare, o il
-- file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT CASE
    WHEN current_setting('pgtap.esito5', true) = 'skip'
        THEN skip('5. nessun emittente attivo su cui fabbricare l''utente', 1)
    ELSE is(
        current_setting('pgtap.esito5', true),
        'servito',
        '5. la fabbrica serve un processo CODA_AUTOMATICA'
    )
END;

-- ⛔ E il verso che protegge la decisione: il canale CODA «umano» resta fuori.
--   Li' l'identita' la porta l'operatore che preme il pulsante, e dargliene una
--   tecnica cancellerebbe il suo nome — cioe' la possibilita' di sapere chi ha
--   chiesto quel lavoro. Senza questo test, allargare il guard «per simmetria»
--   sembrerebbe una pulizia.
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM dbops.processi
                      WHERE canale = 'CODA' AND classe = 'DOMINIO' AND attivo)
        THEN skip('6. nessun processo CODA «umano» a catalogo su cui costruire il caso', 1)
    ELSE throws_ok(
        format($$SELECT script.fn_crea_utente_tecnico(%L, %L)$$,
               (SELECT codice FROM dbops.processi
                 WHERE canale = 'CODA' AND classe = 'DOMINIO' AND attivo
                 ORDER BY id LIMIT 1),
               (SELECT codice FROM anagrafiche.emittenti_fiscali
                 WHERE attivo ORDER BY id LIMIT 1)),
        'P0001',
        NULL,
        '6. il canale CODA «umano» resta rifiutato: l''identita'' la porta chi accoda'
    )
END;

SELECT * FROM finish();

ROLLBACK;
