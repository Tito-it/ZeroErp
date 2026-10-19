-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce modelli STANDARD, che solo il proprietario della tabella scrive (seed e changeSet, D-2): l'applicazione non puo' allestirli, ed e' proprio cio' che il guard le vieta. Il rifiuto all'app ha il suo file, test-documenti-template-standard-app-v1.sql
-- pgTAP test per Zero ERP
-- Test: il modello di documento STANDARD (brief-db-modelli-documento-standard §4.1)
-- ------------------------------------------------------------
-- Elenco test (plan 30):
--  Struttura (Q-1)
--   1) template_documenti.standard NOT NULL
--   2) CHECK standard = (emittente NULL) presente, con quella definizione
--   3) i tre unici sono NULLS NOT DISTINCT (la clausola, non solo il nome)
--   4) il default dell'emittente salta lo standard (WHEN sul trigger)
--   5) il lock di colonna copre `standard`
--  Nascita (Q-1)
--   6) il seed: uno standard senza sessione e senza emittente nasce
--   7) uno standard CON emittente -> 23514 (CHECK)
--   8) una riga d'operatore senza emittente lo riceve dalla sessione e non e' standard
--   9) un secondo standard predefinito per la stessa coppia -> 23505
--  10) `standard` non cambia dopo l'INSERT -> lock
--  Risoluzione, strada B (Q-2)
--  11) emittente senza modelli suoi -> lo standard, livello STANDARD
--  12) emittente col suo predefinito attivo -> il suo, livello EMITTENTE
--  13) modello suo attivo ma non predefinito -> SENZA_PREDEFINITO, NON lo standard
--  14) spenti i suoi modelli -> torna lo standard
--  15) tipo non indicato, un tipo solo fra i candidati -> dedotto
--  16) tipo non indicato, due tipi fra i candidati -> AMBIGUO
--  17) nessun modello, neanche standard -> NON_RISOLTO
--  18) argomenti rotti -> INPUT_INVALIDO
--  Coerenza del documento generato (Q-3)
--  19) un documento di E1 reso con lo standard passa
--  20) un documento di E1 reso col modello di E2 -> E_DOCUMENTI_GENERATO_COERENZA
--  Derivazione (Q-5)
--  21) una copia che deriva da una versione standard della stessa coppia passa
--  22) derivare da una versione NON standard -> DERIVAZIONE_INVALIDA
--  23) derivare dallo standard di un altro tipo -> DERIVAZIONE_INVALIDA
--  24) cambiare l'origine di una versione pubblicata -> PUBBLICATA_IMMUTABILE
--  25) cambiare l'origine in bozza e' ammesso
--  Vista dello scarto (Q-5)
--  26) ALLINEATA
--  27) STANDARD_AVANTI
--  28) CONTESTO_SUPERATO (precede l'origine)
--  29) ORIGINE_NON_DICHIARATA
--  30) l'origine si eredita dalla versione precedente che la dichiara -> ALLINEATA
--
-- Scopo:
--  - provare sui casi COSTRUITI (non sulle righe di dbdev) il modello standard:
--    forma, nascita, risoluzione a due livelli, coerenza, derivazione, scarto.
--  - ⚠️ Gli standard del seed (quando ci saranno) restano attivi: la fixture
--    toglie loro solo il flag predefinito, dentro la transazione, perche' la
--    coppia del test non collida col seed. Gli emittenti sono NUOVI (helper):
--    nessun modello loro preesiste.
-- ------------------------------------------------------------

BEGIN;

-- Tre aziende nuove, senza modelli: E1 usa lo standard, E2 ha i suoi, E3 le copie.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT 'E1'::text AS lato, m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _e SELECT 'E2', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _e SELECT 'E3', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- Contesto: l'operatore di E1 (il default dell'emittente del test 8 lo legge).
DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e WHERE lato = 'E1'));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(30);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                     AS sorg,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO')      AS tipo,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'CONTRATTO')       AS tipo2,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'DDT_VENDITA')     AS tipo3,
  (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT')   AS render,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E1')                                        AS e1,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E2')                                        AS e2,
  (SELECT emittente_fiscale_id FROM _e WHERE lato = 'E3')                                        AS e3;

-- Gli standard gia' presenti (il seed) non devono collidere col predefinito
-- del test: perdono il flag, dentro la transazione.
UPDATE documenti.template_documenti SET is_default = false WHERE standard AND is_default;

-- ============================================================
-- Struttura
-- ============================================================
SELECT col_not_null('documenti', 'template_documenti', 'standard',
  '1) template_documenti.standard NOT NULL');

SELECT is(
  (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
    WHERE c.conrelid = 'documenti.template_documenti'::regclass
      AND c.conname = 'chk_template_documenti_standard_senza_emittente'),
  'CHECK ((standard = (emittente_fiscale_id IS NULL)))',
  '2) CHECK: lo standard e solo lo standard non ha emittente');

SELECT is(
  (SELECT count(*)::int FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
    WHERE i.indrelid = 'documenti.template_documenti'::regclass
      AND i.indnullsnotdistinct
      AND c.relname IN ('uq_template_documenti_emittente_sorgente_codice',
                        'uq_template_documenti_emittente_sorgente_codice_interno',
                        'uq_template_documenti_default_attivo')),
  3,
  '3) i tre unici sono NULLS NOT DISTINCT');

SELECT ok(
  (SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t
    WHERE t.tgrelid = 'documenti.template_documenti'::regclass
      AND t.tgname = 'trg_template_documenti_a10_default_emittente_ins')
  LIKE '%WHEN ((new.standard IS NOT TRUE))%',
  '4) il default dell''emittente salta lo standard');

SELECT ok(
  (SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t
    WHERE t.tgrelid = 'documenti.template_documenti'::regclass
      AND t.tgname = 'trg_template_documenti_a10_lock_columns_upd')
  LIKE '%''standard'', ''E_COLONNA_NON_MODIFICABILE''%',
  '5) il lock di colonna copre standard');

-- ============================================================
-- Nascita
-- ============================================================
-- 6) Il seed gira senza sessione: nessuno da cui dedurre un emittente.
SELECT set_config('app.current_user_id', '', true);
SELECT lives_ok(
  $$INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, standard, is_default, attivo)
    SELECT tipo, 'PGTAP-STD-1', 'pgtap-std-1', 'Standard di prova', sorg,
           'PREVENTIVO', true, true, true
      FROM _k$$,
  '6) il seed: uno standard nasce senza sessione e senza emittente');
DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e WHERE lato = 'E1'));
END $ctx$;

CREATE TEMP TABLE _s ON COMMIT DROP AS
SELECT id AS s1 FROM documenti.template_documenti WHERE codice_interno = 'pgtap-std-1';

SELECT throws_ok(
  $$INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id, standard, is_default, attivo)
    SELECT tipo, 'PGTAP-STD-X', 'pgtap-std-x', 'Standard con emittente', sorg,
           'PREVENTIVO', e1, true, false, true
      FROM _k$$,
  '23514', NULL,
  '7) uno standard con emittente -> CHECK');

-- 8) Una riga d'operatore senza emittente: lo prende dalla sessione (E1).
--    Spenta: non deve contare nella risoluzione di E1.
INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, is_default, attivo)
SELECT tipo2, 'PGTAP-OPE-1', 'pgtap-ope-1', 'Modello d''operatore', sorg,
       'CONTRATTO', false, false
  FROM _k;
SELECT is(
  (SELECT row(t.emittente_fiscale_id, t.standard)::text
     FROM documenti.template_documenti t WHERE t.codice_interno = 'pgtap-ope-1'),
  (SELECT row(e1, false)::text FROM _k),
  '8) una riga d''operatore senza emittente lo riceve dalla sessione, e non e'' standard');

SELECT throws_ok(
  $$INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, standard, is_default, attivo)
    SELECT tipo, 'PGTAP-STD-2', 'pgtap-std-2', 'Secondo standard predefinito', sorg,
           'PREVENTIVO', true, true, true
      FROM _k$$,
  '23505', NULL,
  '9) un secondo standard predefinito per la stessa coppia -> 23505');

SELECT throws_like(
  $$UPDATE documenti.template_documenti SET standard = false, emittente_fiscale_id = (SELECT e1 FROM _k)
     WHERE id = (SELECT s1 FROM _s)$$,
  '%Colonna non modificabile%',
  '10) standard non cambia dopo l''INSERT (lock)');

-- ============================================================
-- Risoluzione (strada B)
-- ============================================================
SELECT is(
  (SELECT row(r.template_documento_id, r.livello)::text
     FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e1, _k.tipo) r),
  (SELECT row(s1, 'STANDARD')::text FROM _s),
  '11) senza modelli suoi l''emittente usa lo standard');

-- E2: un modello suo, predefinito e attivo (senza versioni: la risoluzione
-- sceglie il modello, la versione la sceglie chi stampa).
INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id, is_default, attivo)
SELECT tipo, 'PGTAP-E2-1', 'pgtap-e2-1', 'Modello di E2', sorg, 'PREVENTIVO', e2, true, true
  FROM _k;

SELECT is(
  (SELECT row(r.template_documento_id, r.livello)::text
     FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e2, _k.tipo) r),
  (SELECT row(t.id, 'EMITTENTE')::text FROM documenti.template_documenti t WHERE t.codice_interno = 'pgtap-e2-1'),
  '12) col suo predefinito attivo l''emittente usa il suo');

UPDATE documenti.template_documenti SET is_default = false WHERE codice_interno = 'pgtap-e2-1';
SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e2, _k.tipo)$$,
  '%ha modelli di stampa suoi, ma nessuno è segnato come predefinito%',
  '13) modello suo attivo ma non predefinito: errore, lo standard NON entra');

UPDATE documenti.template_documenti SET attivo = false WHERE codice_interno = 'pgtap-e2-1';
SELECT is(
  (SELECT row(r.template_documento_id, r.livello)::text
     FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e2, _k.tipo) r),
  (SELECT row(s1, 'STANDARD')::text FROM _s),
  '14) spenti i suoi modelli, l''emittente torna allo standard');

SELECT is(
  (SELECT r.template_documento_id
     FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e1) r),
  (SELECT s1 FROM _s),
  '15) tipo non indicato, un solo tipo fra i candidati: dedotto');

-- Un secondo standard della stessa sorgente, di un altro tipo.
INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, standard, is_default, attivo)
SELECT tipo2, 'PGTAP-STD-3', 'pgtap-std-3', 'Standard di un altro tipo', sorg,
       'CONTRATTO', true, true, true
  FROM _k;

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e1)$$,
  '%produce più tipi di documento%',
  '16) tipo non indicato, due tipi fra i candidati: ambiguo');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e1, _k.tipo3)$$,
  '%Nessun modello di stampa per il documento%',
  '17) nessun modello, neanche lo standard: non risolto');

SELECT throws_like(
  $$SELECT * FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, NULL, _k.tipo)$$,
  '%Parametro non valido per la scelta del modello di stampa%',
  '18) argomenti rotti: input invalido');

-- ============================================================
-- Coerenza del documento generato
-- ============================================================
-- Le versioni dello standard: v1 superata (forma 1), v2 in uso (forma 2).
INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
SELECT s1, 1, 'OBSOLETA', 'std v1', '<html>std v1</html>', (SELECT render FROM _k),
       DATE '2026-01-01', DATE '2026-06-30', 1
  FROM _s;
INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
SELECT s1, 2, 'PUBBLICATA', 'std v2', '<html>std v2</html>', (SELECT render FROM _k),
       DATE '2026-07-01', NULL, 2
  FROM _s;
CREATE TEMP TABLE _sv ON COMMIT DROP AS
SELECT max(v.id) FILTER (WHERE v.versione = 1) AS v1,
       max(v.id) FILTER (WHERE v.versione = 2) AS v2
  FROM documenti.template_documenti_versioni v
 WHERE v.template_documento_id = (SELECT s1 FROM _s);

SELECT lives_ok(
  $$INSERT INTO documenti.documenti_generati (
        tipo_documento_output_id, template_documento_id, template_versione_id,
        sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
        titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
        emittente_fiscale_id)
    SELECT k.tipo, s.s1, sv.v2, k.sorg, 'PGTAP-STD-DOC-1', NULL, 1,
           'Doc std', 'doc-std.pdf', '{"_meta": {"context_version": 2}}'::jsonb,
           repeat('1', 64), repeat('2', 64), repeat('3', 64), k.e1
      FROM _k k, _s s, _sv sv$$,
  '19) un documento di E1 reso con lo standard passa la coerenza');

-- Un modello di E2 con la sua versione: E1 non lo puo' usare.
INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id, is_default, attivo)
SELECT tipo, 'PGTAP-E2-2', 'pgtap-e2-2', 'Altro modello di E2', sorg, 'PREVENTIVO', e2, false, true
  FROM _k;
INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
SELECT t.id, 1, 'PUBBLICATA', 'e2 v1', '<html>e2</html>', (SELECT render FROM _k),
       DATE '2026-01-01', NULL, 2
  FROM documenti.template_documenti t WHERE t.codice_interno = 'pgtap-e2-2';

SELECT throws_like(
  $$INSERT INTO documenti.documenti_generati (
        tipo_documento_output_id, template_documento_id, template_versione_id,
        sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
        titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
        emittente_fiscale_id)
    SELECT k.tipo, t.id, v.id, k.sorg, 'PGTAP-STD-DOC-2', NULL, 1,
           'Doc e2', 'doc-e2.pdf', '{"_meta": {"context_version": 2}}'::jsonb,
           repeat('1', 64), repeat('2', 64), repeat('3', 64), k.e1
      FROM _k k
      JOIN documenti.template_documenti t ON t.codice_interno = 'pgtap-e2-2'
      JOIN documenti.template_documenti_versioni v ON v.template_documento_id = t.id$$,
  '%Incoerenza referenziale nel documento generato%',
  '20) un documento di E1 col modello di E2 resta rifiutato');

-- ============================================================
-- Derivazione
-- ============================================================
-- Le copie di E3, tutte sulla coppia (PREVENTIVO, PREVENTIVO), non predefinite.
CREATE TEMP TABLE _c (codice text, vc int, deriva text) ON COMMIT DROP;
INSERT INTO _c VALUES
  ('pgtap-c-allineata',  2, 'v2'),
  ('pgtap-c-avanti',     2, 'v1'),
  ('pgtap-c-superato',   1, 'v1'),
  ('pgtap-c-nondich',    2, NULL),
  ('pgtap-c-ereditata',  2, NULL);

INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id, is_default, attivo)
SELECT k.tipo, upper(c.codice), c.codice, 'Copia ' || c.codice, k.sorg, 'PREVENTIVO', k.e3, false, true
  FROM _k k, _c c;

SELECT lives_ok(
  $$INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template,
        render_engine_id, valido_dal, valido_al, versione_contesto, derivata_da_versione_id)
    SELECT t.id, 1, 'PUBBLICATA', c.codice, '<html>copia</html>', (SELECT render FROM _k),
           DATE '2026-01-01', NULL, c.vc,
           CASE c.deriva WHEN 'v1' THEN sv.v1 WHEN 'v2' THEN sv.v2 END
      FROM _c c
      JOIN documenti.template_documenti t ON t.codice_interno = c.codice
     CROSS JOIN _sv sv
     WHERE c.codice <> 'pgtap-c-ereditata'$$,
  '21) una copia deriva da una versione standard della stessa coppia');

SELECT throws_like(
  $$INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template,
        render_engine_id, versione_contesto, derivata_da_versione_id)
    SELECT t.id, 2, 'BOZZA', 'deriva da e2', '<html>x</html>', (SELECT render FROM _k), 2, v.id
      FROM documenti.template_documenti t
      JOIN documenti.template_documenti e ON e.codice_interno = 'pgtap-e2-2'
      JOIN documenti.template_documenti_versioni v ON v.template_documento_id = e.id
     WHERE t.codice_interno = 'pgtap-c-nondich'$$,
  '%non è una versione del modello standard dello stesso documento%',
  '22) derivare da una versione non standard -> rifiutato');

INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
SELECT t.id, 1, 'PUBBLICATA', 'std3 v1', '<html>std3</html>', (SELECT render FROM _k),
       DATE '2026-01-01', NULL, 2
  FROM documenti.template_documenti t WHERE t.codice_interno = 'pgtap-std-3';

SELECT throws_like(
  $$INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template,
        render_engine_id, versione_contesto, derivata_da_versione_id)
    SELECT t.id, 2, 'BOZZA', 'deriva da std3', '<html>x</html>', (SELECT render FROM _k), 2, v.id
      FROM documenti.template_documenti t
      JOIN documenti.template_documenti s ON s.codice_interno = 'pgtap-std-3'
      JOIN documenti.template_documenti_versioni v ON v.template_documento_id = s.id
     WHERE t.codice_interno = 'pgtap-c-nondich'$$,
  '%non è una versione del modello standard dello stesso documento%',
  '23) derivare dallo standard di un altro tipo -> rifiutato');

SELECT throws_like(
  $$UPDATE documenti.template_documenti_versioni v
       SET derivata_da_versione_id = (SELECT v1 FROM _sv)
      FROM documenti.template_documenti t
     WHERE t.id = v.template_documento_id AND t.codice_interno = 'pgtap-c-allineata'$$,
  '%Una versione pubblicata di un template documentale non puo%',
  '24) l''origine di una versione pubblicata non cambia');

-- La copia «ereditata»: la v1 riprende lo standard v2 (bozza, poi superata), la
-- v2 in uso non ridichiara l'origine.
INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, versione_contesto, derivata_da_versione_id)
SELECT t.id, 1, 'BOZZA', 'ereditata v1', '<html>e v1</html>', (SELECT render FROM _k), 2, (SELECT v1 FROM _sv)
  FROM documenti.template_documenti t WHERE t.codice_interno = 'pgtap-c-ereditata';

SELECT lives_ok(
  $$UPDATE documenti.template_documenti_versioni v
       SET derivata_da_versione_id = (SELECT v2 FROM _sv)
      FROM documenti.template_documenti t
     WHERE t.id = v.template_documento_id AND t.codice_interno = 'pgtap-c-ereditata'$$,
  '25) in bozza l''origine si cambia');

UPDATE documenti.template_documenti_versioni v
   SET stato = 'OBSOLETA', valido_dal = DATE '2026-01-01', valido_al = DATE '2026-06-30'
  FROM documenti.template_documenti t
 WHERE t.id = v.template_documento_id AND t.codice_interno = 'pgtap-c-ereditata';
INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto)
SELECT t.id, 2, 'PUBBLICATA', 'ereditata v2', '<html>e v2</html>', (SELECT render FROM _k),
       DATE '2026-07-01', NULL, 2
  FROM documenti.template_documenti t WHERE t.codice_interno = 'pgtap-c-ereditata';

-- ============================================================
-- Vista dello scarto
-- ============================================================
CREATE TEMP TABLE _scarto ON COMMIT DROP AS
SELECT t.codice_interno, s.stato
  FROM documenti.vw_template_personalizzati_scarto s
  JOIN documenti.template_documenti t ON t.id = s.template_documento_id
 WHERE s.emittente_fiscale_id = (SELECT e3 FROM _k);

SELECT is((SELECT stato FROM _scarto WHERE codice_interno = 'pgtap-c-allineata'),
  'ALLINEATA', '26) deriva dall''ultima versione standard: ALLINEATA');
SELECT is((SELECT stato FROM _scarto WHERE codice_interno = 'pgtap-c-avanti'),
  'STANDARD_AVANTI', '27) deriva da una versione standard precedente: STANDARD_AVANTI');
SELECT is((SELECT stato FROM _scarto WHERE codice_interno = 'pgtap-c-superato'),
  'CONTESTO_SUPERATO', '28) legge una forma dei dati superata: CONTESTO_SUPERATO, prima dell''origine');
SELECT is((SELECT stato FROM _scarto WHERE codice_interno = 'pgtap-c-nondich'),
  'ORIGINE_NON_DICHIARATA', '29) nessuna origine dichiarata: ORIGINE_NON_DICHIARATA');
SELECT is((SELECT stato FROM _scarto WHERE codice_interno = 'pgtap-c-ereditata'),
  'ALLINEATA', '30) l''origine si eredita dalla versione che la dichiara: ALLINEATA');

SELECT * FROM finish();
ROLLBACK;
