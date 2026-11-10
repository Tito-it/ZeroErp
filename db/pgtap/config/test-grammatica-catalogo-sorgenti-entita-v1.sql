-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Una grammatica sola per i tipi di documento — lotto 0: il catalogo.
--   config.sorgenti e' il catalogo dei tipi di documento (G-1), e
--   config.tipi_entita porta lo stesso codice per vincolo.
--   Brief: brief-db-grammatica-unica-documenti (G-1, G-2, G-7 di Tid,
--   2026-10-18). ChangeSet: 20261019-14 (scope CATALOGO), -15 (is_sorgente,
--   colonna generata e FK), i due CSV di 80_data.
--
-- Elenco test (plan 9):
--  1) ogni sorgente ha la sua entita', dichiarata is_sorgente: il verso che
--       una FK non sa dire (le entita' comprendono anche cio' che non e' una
--       sorgente). ⭐ E' il presidio contro il secondo nome dello stesso tipo
--  2) ogni entita' is_sorgente ha sorgente_codice_interno = codice
--  3) la FK fk_tipi_entita_sorgenti punta a config.sorgenti(codice_interno)
--  4) un'entita' che si dichiara sorgente senza esserlo: 23503
--  5) la colonna generata non si scrive: 428C9
--  6) le sette sorgenti nuove di G-2, con la loro tabella, DOCUMENTO e
--       scope CATALOGO
--  7) ogni sorgente nuova punta a una tabella che esiste (target_table e'
--       regclass: il seed la risolve, qui si rilegge dal catalogo)
--  8) le tre entita' di G-7 che non sono sorgenti: is_sorgente falso
--  9) le entita' dei documenti di prima (lotti, giro, flusso...) che non
--       sono sorgenti restano fuori: is_sorgente falso
--
-- ⭐ Legge il SEED, non una popolazione: le righe le portano i due CSV di
--   80_data, presenti anche sul database ricostruito da zero.
-- ⚠️ Test 6: la tabella si legge da pg_class/pg_namespace, mai con
--   target_table::text — un regclass si stampa SENZA schema quando lo schema
--   e' nel search_path di chi legge (come app: «email_outbox», come owner:
--   «config.email_outbox»). Rosso della prima corsa di Tid, 2026-10-19.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- 1) ogni sorgente ha la sua entita'
SELECT is_empty(
    $$SELECT s.codice_interno
        FROM config.sorgenti s
        LEFT JOIN config.tipi_entita te
               ON te.codice = s.codice_interno AND te.is_sorgente
       WHERE te.codice IS NULL
       ORDER BY 1$$,
    '1) ogni sorgente ha la sua entita'' con lo stesso codice, dichiarata is_sorgente');

-- 2) colonna generata = codice
SELECT is_empty(
    $$SELECT codice FROM config.tipi_entita
       WHERE is_sorgente AND sorgente_codice_interno IS DISTINCT FROM codice
      UNION ALL
      SELECT codice FROM config.tipi_entita
       WHERE NOT is_sorgente AND sorgente_codice_interno IS NOT NULL$$,
    '2) sorgente_codice_interno vale il codice solo per le entita'' is_sorgente');

-- 3) la FK
SELECT fk_ok('config', 'tipi_entita', 'sorgente_codice_interno',
             'config', 'sorgenti', 'codice_interno',
             '3) fk_tipi_entita_sorgenti: tipi_entita.sorgente_codice_interno -> sorgenti.codice_interno');

-- 4) un'entita' che non e' una sorgente non si dichiara tale
SAVEPOINT t4;
SELECT throws_ok(
    $$UPDATE config.tipi_entita SET is_sorgente = true WHERE codice = 'LOTTO'$$,
    '23503', NULL,
    '4) LOTTO dichiarato sorgente: la FK lo rifiuta');
ROLLBACK TO SAVEPOINT t4;

-- 5) la colonna generata non si scrive
SAVEPOINT t5;
SELECT throws_ok(
    $$UPDATE config.tipi_entita SET sorgente_codice_interno = 'DDT_VENDITA' WHERE codice = 'LOTTO'$$,
    '428C9', NULL,
    '5) sorgente_codice_interno e'' generata: non si scrive');
ROLLBACK TO SAVEPOINT t5;

-- 6) le sette sorgenti nuove
-- rev 2026-11-09 (brief-db-sorgente-documento-e-riga §7.3, G-2; 20261110-19): le sette
--   si scelgono per CODICE, non per scope. Lo scope CATALOGO non e' «le sorgenti di G-2»:
--   dice solo che nessun meccanismo legge il tipo per scope, e dal ritiro di MAGAZZINO ci
--   sta anche EVENTO_ASSET (categoria EVENTO). Col filtro sullo scope ogni tipo nuovo a
--   catalogo avrebbe fatto diventare rosso un test che parla d'altro.
SELECT results_eq(
    $$SELECT s.codice_interno::text, (n.nspname::text || '.' || c.relname::text) COLLATE "default",
             s.categoria::text, s.scope::text, s.key_selector
        FROM config.sorgenti s
        JOIN pg_class c     ON c.oid = s.target_table
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE s.codice_interno IN ('DDT_ACQUISTO', 'DISTINTA_INCASSO', 'EMAIL', 'INVENTARIO',
                                  'ORDINE_ACQUISTO', 'RETTIFICA', 'TRASFERIMENTO')
       ORDER BY s.codice_interno$$,
    $$VALUES ('DDT_ACQUISTO',     'acquisti.ddt',                'DOCUMENTO', 'CATALOGO', 'id'),
             ('DISTINTA_INCASSO', 'pagamenti.vendite_contabili', 'DOCUMENTO', 'CATALOGO', 'id'),
             ('EMAIL',            'config.email_outbox',         'DOCUMENTO', 'CATALOGO', 'id'),
             ('INVENTARIO',       'magazzino.inventari',         'DOCUMENTO', 'CATALOGO', 'id'),
             ('ORDINE_ACQUISTO',  'acquisti.ordini',             'DOCUMENTO', 'CATALOGO', 'id'),
             ('RETTIFICA',        'magazzino.rettifiche',        'DOCUMENTO', 'CATALOGO', 'id'),
             ('TRASFERIMENTO',    'magazzino.trasferimenti',     'DOCUMENTO', 'CATALOGO', 'id')$$,
    '6) le sorgenti di G-2: tabella, categoria DOCUMENTO, scope CATALOGO, chiave id');

-- 7) target_table risolta su una tabella vera
SELECT is_empty(
    $$SELECT s.codice_interno
        FROM config.sorgenti s
        LEFT JOIN pg_class c ON c.oid = s.target_table AND c.relkind IN ('r', 'p')
       WHERE s.scope = 'CATALOGO' AND c.oid IS NULL$$,
    '7) ogni sorgente CATALOGO punta a una tabella che esiste');

-- 8) G-7: entita' con note che non sono sorgenti
SELECT results_eq(
    $$SELECT codice, is_sorgente FROM config.tipi_entita
       WHERE codice IN ('ARTICOLO_COMPONENTE', 'ASSET', 'MOVIMENTO')
       ORDER BY codice$$,
    $$VALUES ('ARTICOLO_COMPONENTE', false), ('ASSET', false), ('MOVIMENTO', false)$$,
    '8) ARTICOLO_COMPONENTE, ASSET, MOVIMENTO: a catalogo, non sorgenti');

-- 9) cio' che non e' una sorgente resta fuori
SELECT is_empty(
    $$SELECT codice FROM config.tipi_entita
       WHERE is_sorgente
         AND codice IN ('LOTTO', 'TASK_RUN', 'FLUSSO', 'DEFINIZIONE_WORKFLOW',
                        'LISTINO_VERSIONE', 'ARTICOLO', 'PROMO_ARTICOLO')$$,
    '9) le entita'' che non sono documenti non si dichiarano sorgenti');

SELECT * FROM finish();
ROLLBACK;
