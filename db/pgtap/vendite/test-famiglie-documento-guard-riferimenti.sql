-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
-- Elenco test (plan 7):
-- 1) La funzione guard esiste
-- 2) Il trigger e' montato BEFORE, su INSERT e su UPDATE
-- 3) ⛔ Famiglia ATTIVA che nomina una tabella inesistente: respinta (P0001)
-- 4) ⛔ Famiglia ATTIVA che nomina una COLONNA inesistente: respinta (P0001)
-- 5) ⭐ Famiglia RITIRATA che nomina una tabella inesistente: PASSA
-- 6) ⛔ ... ma RIACCENDERLA e' respinto
-- 7) ⭐ Il catalogo VIVO e' coerente: ogni riga attiva punta a oggetti reali
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

SELECT plan(7);

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
-- 3) ⛔ Famiglia ATTIVA con una TABELLA che non esiste
-- ============================================================
PREPARE fdgr_tabella_assente AS
INSERT INTO vendite.famiglie_documento (
    codice_interno, descrizione, schema_tabella, nome_tabella,
    colonna_numero, colonna_billing_account, attivo, presidia_data_documento)
VALUES ('TSTNOTAB', 'Famiglia di test senza tabella', 'vendite',
        'tabella_che_non_esiste_pgtap', 'numero', 'billing_account_id', true, false);

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
    codice_interno, descrizione, schema_tabella, nome_tabella,
    colonna_numero, colonna_billing_account, attivo, presidia_data_documento)
VALUES ('TSTNOCOL', 'Famiglia di test senza colonna', 'vendite',
        'ddt', 'colonna_che_non_esiste_pgtap', 'billing_account_id', true, false);

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
           codice_interno, descrizione, schema_tabella, nome_tabella,
           colonna_numero, colonna_billing_account, attivo, presidia_data_documento)
       VALUES ('TSTRITIR', 'Famiglia di test ritirata', 'vendite',
               'tabella_che_non_esiste_pgtap', 'numero', 'billing_account_id',
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
          LEFT JOIN pg_class c
                 ON c.relname = fd.nome_tabella
                AND c.relnamespace = (SELECT n.oid FROM pg_namespace n
                                       WHERE n.nspname = fd.schema_tabella)
         WHERE fd.attivo
           AND fd.codice_interno NOT LIKE 'TST%'
           AND (c.oid IS NULL
                OR NOT EXISTS (SELECT 1 FROM pg_attribute a
                                WHERE a.attrelid = c.oid
                                  AND a.attname = fd.colonna_numero
                                  AND a.attnum > 0 AND NOT a.attisdropped)
                OR NOT EXISTS (SELECT 1 FROM pg_attribute a
                                WHERE a.attrelid = c.oid
                                  AND a.attname = fd.colonna_billing_account
                                  AND a.attnum > 0 AND NOT a.attisdropped))),
    '7) Il catalogo vivo non e'' vuoto e ogni sua riga attiva punta a oggetti reali');

SELECT * FROM finish();
ROLLBACK;
