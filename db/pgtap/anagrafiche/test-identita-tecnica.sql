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
--  8) vw_emittenti_non_serviti non elenca processi ancora senza utente tecnico
--
-- Scopo:
--  - fissare la decisione del test 4, che oggi e' un'ASSENZA: senza questo
--    test, aggiungere una riga di matrice sembrerebbe una svista da correggere
--    invece di una scelta gia' presa;
--  - fissare che il presidio guarda nei DUE sensi (5 e 7), perche' guardare
--    solo «processo senza identita'» lascerebbe passare il caso peggiore:
--    marcare tecnica=true su una persona per farla sparire dai conteggi;
--  - fissare l'esclusione dei processi di coda (6), che e' la correzione di
--    perimetro trovata scrivendo la fase.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

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
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
    VALUES (v_headless, 'PGTAP-DOMINIO-HEADLESS',
            'processo di dominio che parte da solo', 'DOMINIO', 'COMMAND'),
           (v_coda, 'PGTAP-DOMINIO-CODA',
            'processo di dominio accodato da un operatore', 'DOMINIO', 'CODA');
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
-- rivendichi: e' la forma in cui il flag verrebbe usato per far sparire una
-- PERSONA dai conteggi. Guardare solo il verso 5 la lascerebbe passare.
DO $falsa_tecnica$
DECLARE
    v_identita_id anagrafiche.identita_digitali.id%TYPE;
BEGIN
    SELECT idg.id INTO v_identita_id
      FROM anagrafiche.identita_digitali idg
     WHERE idg.attivo
       AND NOT idg.tecnica
       AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
     ORDER BY idg.id
     LIMIT 1;

    IF v_identita_id IS NOT NULL THEN
        UPDATE anagrafiche.identita_digitali
           SET tecnica = true
         WHERE id = v_identita_id;
        PERFORM set_config('pgtap.identita_id', v_identita_id::text, true);
    ELSE
        PERFORM set_config('pgtap.identita_id', '', true);
    END IF;
END
$falsa_tecnica$;

SELECT CASE
    WHEN NULLIF(current_setting('pgtap.identita_id', true), '') IS NULL
        THEN skip('nessuna identita'' OPERATORE non-tecnica su cui costruire '
                  'il caso: il verso 3 del presidio resta non esercitato', 1)
    ELSE isnt_empty(
        format($$SELECT 1 FROM dbops.vw_processi_dominio_senza_identita
                  WHERE auth_user_id = (SELECT auth_user_id
                                          FROM anagrafiche.identita_digitali
                                         WHERE id = %s)
                    AND motivo LIKE 'identita%%non rivendicata%%'$$,
               current_setting('pgtap.identita_id')),
        'un''identita'' col flag che nessun processo rivendica finisce nel presidio'
    )
END;

-- ============================================================
-- 8. I due presidi non si sovrappongono
-- ============================================================
-- Un processo ancora SENZA utente tecnico non deve comparire una volta per
-- emittente in vw_emittenti_non_serviti: seppellirebbe il segnale. Quel caso
-- e' affare di vw_processi_dominio_senza_identita (test 5).
SELECT is_empty(
    $$SELECT 1 FROM dbops.vw_emittenti_non_serviti
       WHERE processo_codice = 'PGTAP-DOMINIO-HEADLESS'$$,
    'vw_emittenti_non_serviti non elenca processi ancora senza utente tecnico'
);

SELECT * FROM finish();

ROLLBACK;
