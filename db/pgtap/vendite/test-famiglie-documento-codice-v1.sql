-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c): le famiglie di prova nascono come sorgenti (dbops.fn_pgtap_crea_sorgente); niente schema_tabella/nome_tabella; la madre ha la firma nuova.
-- pgTAP test per Zero ERP
-- Test: la famiglia di documento ha un `codice` MODIFICABILE accanto al
--       codice_interno, e la lista delle famiglie cerca su quello.
--       vendite.famiglie_documento.codice                  (20260924-03)
--       vendite.trgfn_famiglie_documento_default_codice    (20260924-04)
--       backfill + NOT NULL / UNIQUE / CHECK               (20260924-05/-06)
--       vendite.vw_famiglie_documento_lista.codice         (20260924-07)
--       seed ui.lista_colonna (lista vendite.famiglie_documento)
--       Brief: brief-db-ricerca-full-colonne-da-accendere.md §3.5
-- ------------------------------------------------------------
-- Elenco test (plan 14):
--  1) La colonna c'e' ed e' NOT NULL
--  2) ⛔ UNIQUE sul codice (uq_famiglie_documento_codice)
--  3) ⛔ CHECK non vuoto (chk_famiglie_documento_codice_nonvuoto)
--  4) ⭐ Alla nascita senza codice, vale il codice_interno
--  5) ⭐ ...anche con la stringa vuota: un campo vuoto non sceglie un codice
--  6) ⭐ Il gemello: un codice passato resta quello
--  7) ⭐⭐ La MADRE (fn_crea_famiglia_documento) non conosce il codice, e la
--     famiglia nasce lo stesso col codice_interno — il percorso del CRUD
--  8) ⭐ Il codice si cambia (e il codice_interno resta)
--  9) ⛔ ...ma non a vuoto: in UPDATE il CHECK rifiuta, il default non ripara
-- 10) ⛔ ...ne' a NULL
-- 11) ⛔ Due famiglie non hanno lo stesso codice
-- 12) ⭐ La vista della lista porta il codice, uguale alla tabella
-- 13) ⛔ ...ed e' ancora security_invoker (si azzera a ogni REPLACE)
-- 14) ⭐⭐ Il catalogo della lista cerca sul `codice` e NON sul codice_interno
--
-- Scopo:
--   ⭐ Il 7 e' quello che conta: il vincolo NOT NULL e' nato insieme a un
--   default alla nascita proprio perche' la madre e il CRUD del backend non
--   passano il codice. Se il trigger sparisse, i test 4-6 fallirebbero per
--   costruzione; il 7 dice che il percorso reale non si e' rotto.
--   ⭐ Il 9 e' il gemello negativo del 5: il default vale SOLO alla nascita.
--   Un default che riparasse anche l'UPDATE nasconderebbe il valore
--   sbagliato invece di rifiutarlo.
--   ⭐ Il 14 legge il SEED del catalogo liste (ui.lista_colonna viene da
--   80_data e in CI c'e' identico): e' leggere il progetto, non misurare una
--   popolazione (AGENTS.md, regola zero).
--
-- ⚠️ Le famiglie della fixture nascono SPENTE e puntano a una tabella che
--   non esiste: una famiglia spenta puo' nominare riferimenti morti (guard
--   dei riferimenti, test 5 di test-famiglie-documento-crud-v1), e non
--   occupa lo slot «una famiglia attiva per tabella». Il codice non dipende
--   da niente di questo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- 1/2/3) La forma della colonna
-- ============================================================
SELECT col_not_null('vendite', 'famiglie_documento', 'codice',
    '1) vendite.famiglie_documento.codice c''e'' ed e'' NOT NULL');

SELECT is(
    (SELECT count(*)::int FROM pg_constraint
      WHERE conrelid = 'vendite.famiglie_documento'::regclass
        AND conname  = 'uq_famiglie_documento_codice'
        AND contype  = 'u'),
    1,
    '2) UNIQUE uq_famiglie_documento_codice');

SELECT is(
    (SELECT count(*)::int FROM pg_constraint
      WHERE conrelid = 'vendite.famiglie_documento'::regclass
        AND conname  = 'chk_famiglie_documento_codice_nonvuoto'
        AND contype  = 'c'),
    1,
    '3) CHECK chk_famiglie_documento_codice_nonvuoto');

-- ============================================================
-- 4/5/6) Il default alla nascita
-- ============================================================
-- ⭐ rev 2026-10-20 (2c, G-5): una famiglia E' una sorgente (FK
--   fk_famiglie_documento_sorgenti). Le famiglie di prova nascono prima come
--   sorgenti, senza tabella (il caso che prima era «una tabella che non esiste»).
DO $sorgenti$ BEGIN
    PERFORM dbops.fn_pgtap_crea_sorgente(c)
       FROM unnest(ARRAY['PGTAP-COD-A', 'PGTAP-COD-B', 'PGTAP-COD-C', 'PGTAP-COD-M']) c;
END $sorgenti$;

INSERT INTO vendite.famiglie_documento
    (codice_interno, descrizione, colonna_numero, attivo, user_insert)
VALUES ('PGTAP-COD-A', 'Famiglia pgTAP A', 'numero', FALSE, 'pgtap');

SELECT is(
    (SELECT codice FROM vendite.famiglie_documento WHERE codice_interno = 'PGTAP-COD-A'),
    'PGTAP-COD-A'::varchar,
    '4) Senza codice all''INSERT, il codice vale il codice_interno');

INSERT INTO vendite.famiglie_documento
    (codice_interno, codice, descrizione, colonna_numero, attivo, user_insert)
VALUES ('PGTAP-COD-B', '  ', 'Famiglia pgTAP B', 'numero', FALSE, 'pgtap');

SELECT is(
    (SELECT codice FROM vendite.famiglie_documento WHERE codice_interno = 'PGTAP-COD-B'),
    'PGTAP-COD-B'::varchar,
    '5) ...anche con un codice vuoto: il campo vuoto non sceglie un codice');

INSERT INTO vendite.famiglie_documento
    (codice_interno, codice, descrizione, colonna_numero, attivo, user_insert)
VALUES ('PGTAP-COD-C', 'PGT-SCELTO', 'Famiglia pgTAP C', 'numero', FALSE, 'pgtap');

SELECT is(
    (SELECT codice FROM vendite.famiglie_documento WHERE codice_interno = 'PGTAP-COD-C'),
    'PGT-SCELTO'::varchar,
    '6) Il gemello: un codice passato resta quello');

-- ============================================================
-- 7) ⭐⭐ Il percorso della madre
-- ============================================================
-- ⚠️ Spenta (p_attivo = FALSE): la madre non provisiona registri per una
--   famiglia spenta, e la tabella di prova non esiste.
-- ⛔ La madre in un'istruzione SUA, e la lettura in quella dopo: chiamarla
--   nel FROM di una SELECT che legge anche la tabella non vede la riga appena
--   inserita (stessa snapshot) — il test darebbe NULL e accuserebbe il
--   trigger di un difetto che non ha.
CREATE TEMP TABLE tmp_madre AS
SELECT m.famiglia_id
  FROM vendite.fn_crea_famiglia_documento(
           'PGTAP-COD-M', 'Famiglia pgTAP dalla madre', 'numero',
           p_attivo => FALSE) m;

SELECT is(
    (SELECT f.codice
       FROM vendite.famiglie_documento f
       JOIN tmp_madre m ON m.famiglia_id = f.id),
    'PGTAP-COD-M'::varchar,
    '7) La madre non passa il codice, e la famiglia nasce col codice_interno');

-- ============================================================
-- 8/9/10/11) Il codice si cambia, ma resta un codice
-- ============================================================
UPDATE vendite.famiglie_documento SET codice = 'PGT-RINOMINATA'
 WHERE codice_interno = 'PGTAP-COD-A';

SELECT is(
    (SELECT codice || '|' || codice_interno FROM vendite.famiglie_documento
      WHERE codice_interno = 'PGTAP-COD-A'),
    'PGT-RINOMINATA|PGTAP-COD-A',
    '8) Il codice si cambia, e il codice_interno resta');

PREPARE codice_vuoto AS
UPDATE vendite.famiglie_documento SET codice = '' WHERE codice_interno = 'PGTAP-COD-A';

SELECT throws_ok(
    'codice_vuoto', '23514',
    NULL,
    '9) In UPDATE un codice vuoto e'' rifiutato dal CHECK: il default vale solo alla nascita');

PREPARE codice_null AS
UPDATE vendite.famiglie_documento SET codice = NULL WHERE codice_interno = 'PGTAP-COD-A';

SELECT throws_ok(
    'codice_null', '23502',
    NULL,
    '10) ...e un codice NULL dal NOT NULL');

PREPARE codice_doppio AS
UPDATE vendite.famiglie_documento SET codice = 'PGT-SCELTO' WHERE codice_interno = 'PGTAP-COD-A';

SELECT throws_ok(
    'codice_doppio', '23505',
    NULL,
    '11) Due famiglie non hanno lo stesso codice');

-- ============================================================
-- 12/13) La vista della lista
-- ============================================================
SELECT is(
    (SELECT v.codice FROM vendite.vw_famiglie_documento_lista v
      WHERE v.codice_interno = 'PGTAP-COD-C'),
    'PGT-SCELTO'::varchar,
    '12) La vista della lista porta il codice della tabella');

SELECT ok(
    (SELECT c.reloptions @> ARRAY['security_invoker=on']
            OR c.reloptions @> ARRAY['security_invoker=true']
       FROM pg_class c
      WHERE c.oid = 'vendite.vw_famiglie_documento_lista'::regclass),
    '13) La vista e'' ancora security_invoker');

-- ============================================================
-- 14) ⭐⭐ Il catalogo della lista cerca sul codice
-- ============================================================
-- ⚠️ Una stringa sola, e non due asserzioni: «codice» acceso E
--   «codice_interno» spento. Con due test separati, un seed che accendesse
--   entrambi passerebbe il primo.
SELECT is(
    (SELECT string_agg(c.campo_sorgente, ',' ORDER BY c.campo_sorgente)
       FROM ui.lista_colonna c
       JOIN ui.lista_definizione d ON d.id = c.lista_id
      WHERE d.codice = 'vendite.famiglie_documento'
        AND c.attivo
        AND c.ricercabile_full
        AND c.campo_sorgente IN ('codice', 'codice_interno')),
    'codice',
    '14) La lista delle famiglie cerca sul codice, non sul codice_interno');

SELECT * FROM finish();

ROLLBACK;
