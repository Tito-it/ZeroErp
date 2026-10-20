-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c): le famiglie di prova nascono come sorgenti (dbops.fn_pgtap_crea_sorgente), la tabella e' quella della sorgente; il test 7 legge config.fn_sorgente_tabella.
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture SCRIVE in vendite.famiglie_documento, che e'
--   un catalogo di configurazione — le sue righe le mette una migrazione, non
--   un operatore, e il ruolo applicativo non ci scrive. E' la stessa ragione
--   per cui il codice errore di questo guard e' TECNICO.
-- pgtap-contesto: escluso — discende dal marcatore qui sopra: il soggetto del
--   test e' un catalogo senza RLS e senza perimetro di emittente, e un
--   contesto operatore non cambierebbe nessuna delle risposte.
-- pgTAP test per Zero ERP
-- Test: C2-18 — il catalogo delle famiglie di documento si presidia da se'
--       vendite.trgfn_famiglie_documento_guard_riferimenti  (20260831-18)
--       Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-18
-- ------------------------------------------------------------
-- Elenco test (plan 9):
-- 1) La funzione guard esiste
-- 2) Il trigger e' montato BEFORE, su INSERT e su UPDATE
-- 3) ⛔ Famiglia ATTIVA che nomina una tabella inesistente: respinta (P0001)
-- 4) ⛔ Famiglia ATTIVA che nomina una COLONNA inesistente: respinta (P0001)
-- 5) ⭐ Famiglia RITIRATA che nomina una tabella inesistente: PASSA
-- 6) ⛔ ... ma RIACCENDERLA e' respinto
-- 7) ⭐ Il catalogo VIVO e' coerente: ogni riga attiva punta a oggetti reali
-- 8) ⭐ rev 2026-09-14 (P-9): una famiglia ATTIVA SENZA billing account PASSA — il
--    vuoto e' una dichiarazione, come per la serie (l'ordine di acquisto)
-- 9) ⛔ ...ma senza billing account il NUMERO resta verificato: il salto e' SOLO sul BA
--
-- Scopo:
--   Dal 2026-08-31 il presidio sul cambio emittente di un billing account non
--   elenca piu' le tabelle dei documenti: le LEGGE da vendite.famiglie_documento
--   e le compone in SQL dinamico con `%I`. E' il modo giusto — toglie di mezzo
--   l'elenco parallelo che resta indietro — ma sposta un rischio: una riga di
--   catalogo che nomina una tabella o una colonna inesistente non da' fastidio
--   a nessuno finche' qualcuno non prova a spostare un billing account, e li'
--   uscirebbe come `undefined_table` NUDO, dentro un guard, in un movimento che
--   con le famiglie di documento non c'entra niente.
--
--   ⭐ IL TEST 5 SERVE QUANTO IL 3 e il 4, e non e' clemenza: una famiglia
--   ritirata puo' legittimamente nominare una tabella che non c'e' piu' —
--   e' storia, non configurazione — e un guard che la rifiutasse costringerebbe
--   a CANCELLARE la riga, cioe' a perdere il fatto che quella famiglia e'
--   esistita. Senza questo test, un guard che rifiuta tutto passerebbe il 3 e
--   il 4 esattamente come quello giusto.
--
--   ⭐ IL TEST 6 E' LA META' CHE SI DIMENTICA. Se `attivo` non stesse fra le
--   colonne di `UPDATE OF`, riaccendere una famiglia ritirata male rimetterebbe
--   in circolo una riga rotta senza che nessuno dica niente — e il difetto
--   ricomparirebbe al primo spostamento di un billing account, cioe' dove non
--   si guarda.
--
--   ⚠️ IL TEST 7 GUARDA I DATI, non il codice, ed e' l'unico di questo file a
--   farlo: e' la prova che le cinque righe seedate attraversano il guard che
--   e' stato scritto DOPO di loro. ⛔ Ed e' scritto come «nessuna riga rotta»
--   PIU' «le righe attive esistono»: un test che conta solo i cattivi diventa
--   muto il giorno in cui il catalogo si svuota.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- 1) La funzione guard esiste
-- ============================================================
SELECT has_function(
    'vendite', 'trgfn_famiglie_documento_guard_riferimenti', ARRAY[]::text[],
    '1) vendite.trgfn_famiglie_documento_guard_riferimenti esiste');

-- ============================================================
-- 2) Il trigger e' montato BEFORE, su INSERT e su UPDATE
-- ============================================================
-- ⚠️ Presidio strutturale: un guard scritto e non montato e' un guard che non
--   c'e', e la differenza non si vede da nessuna altra parte.
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND n.nspname = 'vendite'
        AND c.relname = 'famiglie_documento'
        AND t.tgname  = 'trg_famiglie_documento_a10_guard_riferimenti_ins_upd'
        -- 2 = BEFORE, 4 = INSERT, 16 = UPDATE  (pg_trigger.tgtype)
        AND (t.tgtype & 2)  = 2
        AND (t.tgtype & 4)  = 4
        AND (t.tgtype & 16) = 16),
    1,
    '2) Il guard e'' montato BEFORE su INSERT e UPDATE');

-- ============================================================
-- Fixture — rev 2026-10-20 (2c, G-5): una famiglia E' una sorgente (FK) e la sua
--   tabella e' la target_table della sorgente. Ogni famiglia di prova nasce prima
--   come sorgente, con la tabella del suo caso; «la tabella che non esiste» e' la
--   sorgente che non ne dichiara una.
-- ============================================================
DO $sorgenti$ BEGIN
    PERFORM dbops.fn_pgtap_crea_sorgente('TSTNOTAB');
    PERFORM dbops.fn_pgtap_crea_sorgente('TSTNOCOL', 'vendite.ddt'::regclass);
    PERFORM dbops.fn_pgtap_crea_sorgente('TSTRITIR');
    PERFORM dbops.fn_pgtap_crea_sorgente('TSTNOBA', 'acquisti.ordini'::regclass);
    PERFORM dbops.fn_pgtap_crea_sorgente('TSTNOBA2', 'acquisti.ddt'::regclass);
END $sorgenti$;

-- ============================================================
-- 3) ⛔ Famiglia ATTIVA con una TABELLA che non esiste
-- ============================================================
PREPARE fdgr_tabella_assente AS
INSERT INTO vendite.famiglie_documento (
    codice_interno, descrizione,
    colonna_numero, colonna_billing_account, attivo, presidia_data_documento)
VALUES ('TSTNOTAB', 'Famiglia di test senza tabella',
        'numero', 'billing_account_id', true, false);

SELECT throws_ok(
    'EXECUTE fdgr_tabella_assente',
    'P0001',
    NULL,
    '3) Una famiglia attiva che nomina una tabella inesistente e'' respinta');

-- ============================================================
-- 4) ⛔ Famiglia ATTIVA con una COLONNA che non esiste
-- ============================================================
-- ⚠️ La tabella qui c'e': si sta provando il SECONDO controllo, non di nuovo
--   il primo. Senza questa riga, un guard che verificasse la sola tabella
--   passerebbe il 3) e lascerebbe passare il refuso piu' probabile — il nome
--   della colonna, che non e' lo stesso ovunque (`numero` per quattro,
--   `codice` per la commessa).
PREPARE fdgr_colonna_assente AS
INSERT INTO vendite.famiglie_documento (
    codice_interno, descrizione,
    colonna_numero, colonna_billing_account, attivo, presidia_data_documento)
VALUES ('TSTNOCOL', 'Famiglia di test senza colonna',
        'colonna_che_non_esiste_pgtap', 'billing_account_id', true, false);

SELECT throws_ok(
    'EXECUTE fdgr_colonna_assente',
    'P0001',
    NULL,
    '4) Una famiglia attiva che nomina una colonna inesistente e'' respinta');

-- ============================================================
-- 5) ⭐ Famiglia RITIRATA: la stessa riga passa
-- ============================================================
-- E' la prova che il guard distingue «configurazione» da «storia». Senza,
-- ritirare una famiglia obbligherebbe a cancellarne la riga.
SELECT lives_ok(
    $q$INSERT INTO vendite.famiglie_documento (
           codice_interno, descrizione,
           colonna_numero, colonna_billing_account, attivo, presidia_data_documento)
       VALUES ('TSTRITIR', 'Famiglia di test ritirata',
               'numero', 'billing_account_id',
               false, false)$q$,
    '5) Una famiglia RITIRATA puo'' nominare una tabella che non c''e'' piu''');

-- ============================================================
-- 6) ⛔ ... ma riaccenderla no
-- ============================================================
-- ⚠️ E' la ragione per cui `attivo` sta fra le colonne di UPDATE OF: senza,
--   questa riga tornerebbe in circolo rotta e in silenzio.
PREPARE fdgr_riaccensione AS
UPDATE vendite.famiglie_documento
   SET attivo = true
 WHERE codice_interno = 'TSTRITIR';

SELECT throws_ok(
    'EXECUTE fdgr_riaccensione',
    'P0001',
    NULL,
    '6) Riaccendere una famiglia con riferimenti rotti e'' respinto');

-- ============================================================
-- 7) ⭐ Il catalogo VIVO attraversa il guard scritto dopo di lui
-- ============================================================
-- ⛔ Due condizioni in una: «nessuna riga attiva e' rotta» E «le righe attive
--   esistono». Un test che conta i soli cattivi diventa MUTO il giorno in cui
--   il catalogo si svuota — e un catalogo vuoto e' un difetto peggiore di una
--   riga sbagliata, perche' il presidio sul cambio emittente del billing
--   account smetterebbe di bloccare qualunque cosa, senza dire niente.
-- ⚠️ Le righe di test appena inserite si escludono: qui si guarda il SEED.
SELECT ok(
    (SELECT count(*) FROM vendite.famiglie_documento fd
      WHERE fd.attivo AND fd.codice_interno NOT LIKE 'TST%') > 0
    AND NOT EXISTS (
        SELECT 1
          FROM vendite.famiglie_documento fd
          -- rev 2026-10-20 (2c): la tabella dalla sorgente, col BB del guard
          LEFT JOIN LATERAL config.fn_sorgente_tabella(fd.codice_interno) st ON true
          LEFT JOIN pg_class c ON c.oid = st.relid
         WHERE fd.attivo
           AND fd.codice_interno NOT LIKE 'TST%'
           AND (c.oid IS NULL
                OR NOT EXISTS (SELECT 1 FROM pg_attribute a
                                WHERE a.attrelid = c.oid
                                  AND a.attname = fd.colonna_numero
                                  AND a.attnum > 0 AND NOT a.attisdropped)
                -- rev 2026-09-14: il billing account e' opzionale — si verifica
                -- solo se dichiarato, come fa il guard
                OR (COALESCE(btrim(fd.colonna_billing_account), '') <> ''
                    AND NOT EXISTS (SELECT 1 FROM pg_attribute a
                                     WHERE a.attrelid = c.oid
                                       AND a.attname = fd.colonna_billing_account
                                       AND a.attnum > 0 AND NOT a.attisdropped)))),
    '7) Il catalogo vivo non e'' vuoto e ogni sua riga attiva punta a oggetti reali');

-- ============================================================
-- 8) ⭐ Famiglia ATTIVA SENZA billing account: passa (P-9, 20260914-07/-08)
-- ============================================================
-- La controparte di un ordine di acquisto e' un soggetto_ruolo, non un
-- billing account: la colonna resta NULL, e il guard non la cerca. E' la
-- stessa forma di colonna_serie. La tabella e' quella vera del caso d'uso,
-- e non ha ancora una famiglia attiva (uq_famiglie_documento_tabella_attiva).
SELECT lives_ok(
    $q$INSERT INTO vendite.famiglie_documento (
           codice_interno, descrizione,
           colonna_numero, colonna_billing_account, attivo, presidia_data_documento)
       VALUES ('TSTNOBA', 'Famiglia di test senza billing account',
               'numero', NULL, true, false)$q$,
    '8) Una famiglia ATTIVA senza billing account passa: il vuoto e'' una dichiarazione (l''ordine di acquisto)');

-- ============================================================
-- 9) ⛔ ...ma il numero resta verificato anche senza billing account
-- ============================================================
-- E' il gemello che distingue «salta il BA» da «salta tutto»: un guard che
-- uscisse presto su NULL lascerebbe passare anche il refuso sul numero.
PREPARE fdgr_noba_numero_assente AS
INSERT INTO vendite.famiglie_documento (
    codice_interno, descrizione,
    colonna_numero, colonna_billing_account, attivo, presidia_data_documento)
VALUES ('TSTNOBA2', 'Famiglia senza BA con numero rotto',
        'colonna_che_non_esiste_pgtap', NULL, true, false);

SELECT throws_ok(
    'EXECUTE fdgr_noba_numero_assente',
    'P0001',
    NULL,
    '9) Senza billing account la colonna del numero resta verificata: il salto e'' solo sul BA');

SELECT * FROM finish();
ROLLBACK;
