-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.processi / processi_identita
--   (catalogo e registro che a runtime non scrive nessuno, SELECT-only per il
--   ruolo applicativo) e deve costruire un'identita' che si dichiara tecnica
--   senza esserlo — un mondo che l'applicazione non puo' creare, ed e'
--   esattamente cio' che il presidio deve intercettare.
--
-- Test: il flag anagrafiche.identita_digitali.tecnica e i due presidi
--       dbops.vw_processi_dominio_senza_identita, dbops.vw_emittenti_non_serviti
-- Brief: brief-db-processi-automatici-identita-e-perimetro §4.3, §6.4, §8
--
-- Elenco test (plan 8):
--  1) identita_digitali ha la colonna tecnica
--  2) il default e' false: il pregresso resta di persone
--  3) il tipo ruolo dei processi e' a catalogo
--  4) ⭐ il tipo ruolo dei processi NON vincola la natura — decisione dichiarata
--  5) un processo DOMINIO headless senza utente tecnico finisce nel presidio
--  6) un processo su canale CODA NON finisce nel presidio (ha gia' l'operatore)
--  7) un'identita' col flag che nessun processo rivendica finisce nel presidio
--  8) vw_emittenti_non_serviti nomina ogni emittente attivo rimasto scoperto
--
-- Scopo:
--  - fissare la decisione del test 4, che oggi e' un'ASSENZA: senza questo
--    test, aggiungere una riga di matrice sembrerebbe una svista da correggere
--    invece di una scelta gia' presa;
--  - fissare che il presidio guarda nei DUE sensi (5 e 7): «processo senza
--    identita'» da solo lascerebbe passare il residuo opposto, un utente
--    tecnico che nessun processo rivendica piu'. ⭐ L'altro abuso temuto —
--    marcare tecnica=true su una persona — non e' piu' costruibile: dal
--    changeSet -28 il guard di coerenza lo rifiuta (nota al test 7);
--  - fissare l'esclusione dei processi di coda (6), che e' la correzione di
--    perimetro trovata scrivendo la fase.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ `SET CONSTRAINTS ALL IMMEDIATE` NON sta qui, ed e' il caso che il template
--   descrive: «va DOVE L'UNITA' DI LAVORO E' COMPLETA». La fixture del test 7
--   chiama `script.fn_crea_utente_tecnico`, che crea il soggetto in
--   un'istruzione e il suo contatto in quella dopo; il guard sui contatti e'
--   DIFFERITO, quindi con IMMEDIATE in testa scatterebbe a meta' strada,
--   bocciando un soggetto che sta per ricevere il contatto due righe sotto.
--   ⇒ Sta subito dopo quel blocco. Il guardrail del preambolo controlla la
--     presenza, non la posizione.

SELECT plan(8);

-- ============================================================
-- 1..2. Il flag
-- ============================================================
SELECT has_column('anagrafiche', 'identita_digitali', 'tecnica',
                  'identita_digitali ha la colonna tecnica');

SELECT col_default_is('anagrafiche', 'identita_digitali', 'tecnica', 'false',
                      'tecnica ha default false: il pregresso resta di persone');

-- ============================================================
-- 3..4. Il tipo ruolo dei processi, e la decisione sulla natura
-- ============================================================
SELECT isnt_empty(
    $$SELECT 1 FROM config.tipi_ruoli
       WHERE codice_interno = 'PROC_AUTO'$$,
    'il tipo ruolo dei processi automatici e'' a catalogo'
);

-- ⭐ QUESTO TEST FISSA UN'ASSENZA, ed e' il motivo per cui esiste.
--   La matrice config.tipi_ruoli_nature_ammesse e' VUOTA per questo tipo
--   ruolo, e il guard trgfn_soggetti_ruoli_guard_natura_ammessa applica
--   «matrice assente = nature libere». E' una DECISIONE, non una svista:
--   le nature disponibili per una persona giuridica (SC, SP) impongono
--   partita IVA e codice fiscale, che un processo non ha — vincolarla
--   costringerebbe a inventare una categoria anagrafica per una cosa che
--   anagrafica non e'.
--   ⚠️ Senza questo test, la riga mancante sembrerebbe un buco da tappare.
SELECT is_empty(
    $$SELECT 1
        FROM config.tipi_ruoli_nature_ammesse m
        JOIN config.tipi_ruoli tr ON tr.id = m.tipo_ruolo_id
       WHERE tr.codice_interno = 'PROC_AUTO'$$,
    'il tipo ruolo dei processi non vincola la natura — decisione dichiarata'
);

-- ============================================================
-- Fixture: due processi DOMINIO, uno headless e uno di coda
-- ============================================================
DO $fixture$
DECLARE
    v_headless dbops.processi.id%TYPE := 9301;
    v_coda     dbops.processi.id%TYPE := 9302;
BEGIN
    -- 20261016-20: chi ha una sveglia dichiara l'accensione; un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento)
    VALUES (v_headless, 'PGTAP-DOMINIO-HEADLESS',
            'processo di dominio che parte da solo', 'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA'),
           (v_coda, 'PGTAP-DOMINIO-CODA',
            'processo di dominio accodato da un operatore', 'DOMINIO', 'CODA', NULL, NULL, NULL, 'PROGRAMMA');
END
$fixture$;

-- ============================================================
-- 5..6. Chi ha bisogno di un utente tecnico, e chi no
-- ============================================================
SELECT is(
    (SELECT v.motivo
       FROM dbops.vw_processi_dominio_senza_identita v
      WHERE v.processo_codice = 'PGTAP-DOMINIO-HEADLESS'),
    'processo DOMINIO headless senza utente tecnico',
    'un processo DOMINIO headless senza utente tecnico finisce nel presidio'
);

-- ⛔ La correzione di perimetro: un tipo della coda e' accodato da un
--   OPERATORE e gira con lo scope catturato all'enqueue. Dargli un utente
--   tecnico cancellerebbe il nome di chi ha chiesto il lavoro.
SELECT is_empty(
    $$SELECT 1 FROM dbops.vw_processi_dominio_senza_identita
       WHERE processo_codice = 'PGTAP-DOMINIO-CODA'$$,
    'un processo di CODA non chiede un utente tecnico: ha gia'' l''operatore'
);

-- ============================================================
-- 7. Il verso che protegge dal caso peggiore
-- ============================================================
-- Un'identita' che si dichiara processo senza che nessun processo la
-- rivendichi. Guardare solo il verso 5 la lascerebbe passare.
--
-- ⛔ 2026-09-04 — LA FIXTURE E' CAMBIATA, e il motivo vale piu' del test.
--   Prima costruiva il caso mettendo `tecnica = true` su una PERSONA, cioe'
--   sull'identita' di un operatore vero. Da quando il changeSet -28 ha diviso
--   `trgfn_identita_digitali_guard_coerenza` sul flag, quell'UPDATE non passa
--   piu': un'identita' tecnica pretende un soggetto_ruolo PROC_AUTO, e quello
--   di una persona e' RIS_UMANA.
--   ⭐ E' il DB che ha imparato a impedire proprio l'abuso che questo test
--     temeva. La fixture non si "ripara" allentando il guard: si costruisce il
--     caso che RESTA possibile — un utente tecnico vero il cui legame col
--     processo viene disattivato. L'utente resta in giro, col suo flag e col
--     suo perimetro, e nessun processo lo rivendica piu': e' il residuo di un
--     processo ritirato male, ed e' quello che il presidio deve vedere.
DO $falsa_tecnica$
DECLARE
    v_auth_user_id integer;   -- ⚠️ niente %TYPE su django.*
    v_emittente    anagrafiche.emittenti_fiscali.codice%TYPE;
BEGIN
    -- Ordine stabile: una fixture che pesca a caso non verifica, scommette.
    SELECT ef.codice INTO v_emittente
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.attivo
     ORDER BY ef.id
     LIMIT 1;

    IF v_emittente IS NULL THEN
        PERFORM set_config('pgtap.auth_user_id', '', true);
        RETURN;
    END IF;

    -- Si passa dalla fabbrica invece di montare l'utente a mano: se un giorno
    -- creare un utente tecnico richiedera' un pezzo in piu', questo test lo
    -- scopre insieme a tutti gli altri.
    v_auth_user_id := script.fn_crea_utente_tecnico(
                          'PGTAP-DOMINIO-HEADLESS', v_emittente);

    -- ⭐ Il passo che costruisce il caso: si spegne il LEGAME, non l'utente.
    UPDATE dbops.processi_identita
       SET attivo = false
     WHERE auth_user_id = v_auth_user_id;

    PERFORM set_config('pgtap.auth_user_id', v_auth_user_id::text, true);
END
$falsa_tecnica$;

-- Unita' di lavoro completa (utente + soggetto + contatto + ruolo + identita'):
-- da qui in poi i vincoli differiti devono scattare, o il file sarebbe verde
-- per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT CASE
    WHEN NULLIF(current_setting('pgtap.auth_user_id', true), '') IS NULL
        THEN skip('nessun emittente attivo su cui fabbricare l''utente '
                  'tecnico: il verso 3 del presidio resta non esercitato', 1)
    ELSE is(
        (SELECT v.motivo
           FROM dbops.vw_processi_dominio_senza_identita v
          WHERE v.auth_user_id =
                current_setting('pgtap.auth_user_id')::integer),
        'identita'' con flag tecnica non rivendicata da nessun processo',
        'un''identita'' col flag che nessun processo rivendica finisce nel presidio'
    )
END;

-- ============================================================
-- 8. Il presidio degli emittenti dice QUALE emittente e' scoperto
-- ============================================================
-- ⛔ 2026-09-04 — QUESTA ASSERZIONE DICEVA IL FALSO, e il file moriva prima di
--   arrivarci. Pretendeva che `vw_emittenti_non_serviti` NON nominasse un
--   processo ancora senza utente tecnico, per non «seppellire il segnale».
--   Il changeSet -38 ha cambiato la domanda della vista: non piu' «a questo
--   utente manca la riga per l'emittente X» ma «per la coppia (processo,
--   emittente) esiste un utente?». Per un processo con ZERO utenti la risposta
--   e' «no» su OGNI emittente, quindi comparire una volta per emittente non e'
--   rumore: e' la risposta giusta alla domanda nuova.
--   ⭐ Il test asserisce percio' cio' che serve davvero sapere — la vista dice
--     QUALE emittente e' scoperto, uno per emittente attivo — e non piu' una
--     non-sovrapposizione che il modello non promette.
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_emittenti_non_serviti
      WHERE processo_codice = 'PGTAP-DOMINIO-HEADLESS'),
    (SELECT count(*)::int FROM anagrafiche.emittenti_fiscali WHERE attivo),
    'vw_emittenti_non_serviti nomina ogni emittente attivo rimasto scoperto'
);

SELECT * FROM finish();

ROLLBACK;
