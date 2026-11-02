-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la soglia della ricerca libera e' un fatto della lista
--       ui.lista_definizione.ricerca_min_caratteri   (20260925-75)
--       ui.fn_lista_da_codice                        (20260925-76, BB)
--       ui.fn_resolve_lista_config                   (20260925-77)
--       ui.fn_lista_colonne_ricerca_full             (20260925-78)
--       seed: colonna `ricerca_min_caratteri` di lista_definizione.csv
--       Piano: brief-db-be-fe-ricerca-soglia-per-lista, sezione 4
--
-- Elenco test (plan 16):
--   1) la colonna esiste, smallint
--   2) NOT NULL
--   3) default 3, la soglia di progetto
--   4) ⛔ il CHECK rifiuta 0
--   5) ⛔ e rifiuta un negativo
--   6) ui.fn_lista_da_codice(varchar) esiste ed e' STABLE
--   7) ⭐ lista costruita a 1: il BB risponde 1
--   8) ⭐ … e il risolutore porta 1 nel JSONB
--   9) ⭐ lista costruita senza dichiararla: il BB risponde 3
--  10) ⭐ … e il risolutore porta 3
--  11) la chiave del JSONB e' un NUMERO (il BE e il FE la leggono come intero)
--  12) BB, lista inesistente: E_UI_LISTA_NON_TROVATA
--  13) BB, lista spenta: E_UI_LISTA_NON_TROVATA
--  14) risolutore, lista inesistente: ancora E_UI_LISTA_NON_TROVATA (ora dal BB)
--  15) ricerca libera, lista inesistente: ancora E_UI_LISTA_NON_TROVATA (dal BB)
--  16) ⭐ il seed: le liste a 1 sono ESATTAMENTE le diciassette dichiarate (14 + 3 dal 2026-09-27)
--      (elenco, non conteggio)
--
-- Scopo:
--  - La soglia deve arrivare a DUE lettori dalla stessa fonte: la
--    configurazione della schermata (risolutore) e il BB di ricerca del BE
--    (SELECT ricerca_min_caratteri FROM ui.fn_lista_da_codice(...)). I test
--    7-10 chiedono lo stesso fatto a entrambi, su due liste COSTRUITE: una a
--    1 e una lasciata al default. Non si appoggiano al seed, che puo'
--    cambiare senza che la regola cambi.
--  - Il 16 e' il presidio del seed: se una lista di configurazione perde il
--    suo 1 (o una lista d'archivio lo prende) lo dice per nome.
--  - I test 12-15 sono la regressione del ritiro delle due copie inline
--    («lista dal codice o errore»): stesso codice, stessa frase.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: le liste di prova nascono e muoiono qui.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il risolutore legge utente e veste dalle GUC.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: ogni istruzione della fixture e' un'unita' completa.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture: tre liste di prova, codici con suffisso casuale.
--   uno     -> ricerca_min_caratteri = 1, dichiarata
--   default -> la colonna NON nominata: vale il default
--   spenta  -> attivo = false
-- ============================================================
CREATE TEMP TABLE _t_liste AS
WITH s AS (SELECT substr(md5(clock_timestamp()::text), 1, 8) AS suf),
ins_uno AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert,
                                    ricerca_min_caratteri)
  SELECT '_pgtap.soglia_uno_' || suf, 'Lista pgTAP: soglia 1', 'pgtap', NULL, TRUE, 'pgtap', 1 FROM s
  RETURNING codice
),
ins_def AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  SELECT '_pgtap.soglia_default_' || suf, 'Lista pgTAP: soglia di default', 'pgtap', NULL, TRUE, 'pgtap' FROM s
  RETURNING codice
),
ins_off AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert,
                                    ricerca_min_caratteri)
  SELECT '_pgtap.soglia_spenta_' || suf, 'Lista pgTAP: spenta', 'pgtap', NULL, FALSE, 'pgtap', 1 FROM s
  RETURNING codice
)
SELECT (SELECT codice FROM ins_uno) AS uno,
       (SELECT codice FROM ins_def) AS dflt,
       (SELECT codice FROM ins_off) AS spenta;

CREATE OR REPLACE FUNCTION pg_temp.cfg(p_codice text)
RETURNS jsonb AS $$
  SELECT ui.fn_resolve_lista_config(
           p_codice,
           NULLIF(current_setting('app.current_user_id', true), '')::integer,
           NULL);
$$ LANGUAGE sql;

-- ============================================================
-- 1-5) La colonna e il suo vincolo
-- ============================================================
SELECT col_type_is('ui', 'lista_definizione', 'ricerca_min_caratteri', 'smallint',
  '1) ui.lista_definizione.ricerca_min_caratteri esiste, smallint');

SELECT col_not_null('ui', 'lista_definizione', 'ricerca_min_caratteri',
  '2) NOT NULL: la risposta e'' una, gia'' risolta');

SELECT col_default_is('ui', 'lista_definizione', 'ricerca_min_caratteri', '3',
  '3) default 3, la soglia di progetto');

SELECT throws_ok(
  $$UPDATE ui.lista_definizione SET ricerca_min_caratteri = 0
     WHERE codice = (SELECT uno FROM _t_liste)$$,
  '23514', NULL,
  '4) ⛔ il CHECK rifiuta 0');

SELECT throws_ok(
  $$UPDATE ui.lista_definizione SET ricerca_min_caratteri = -1
     WHERE codice = (SELECT uno FROM _t_liste)$$,
  '23514', NULL,
  '5) ⛔ e rifiuta un negativo');

-- ============================================================
-- 6) Il building block
-- ============================================================
SELECT volatility_is('ui', 'fn_lista_da_codice', ARRAY['character varying'], 'stable',
  '6) ui.fn_lista_da_codice(varchar) esiste ed e'' STABLE');

-- ============================================================
-- 7-11) ⭐ Due lettori, una fonte, due liste costruite
-- ============================================================
SELECT is(
  (SELECT ricerca_min_caratteri::int FROM ui.fn_lista_da_codice((SELECT uno FROM _t_liste))),
  1,
  '7) ⭐ lista a 1: il BB di ricerca risponde 1');

SELECT is(
  (pg_temp.cfg((SELECT uno FROM _t_liste)) ->> 'ricerca_min_caratteri')::int,
  1,
  '8) ⭐ … e la configurazione della schermata porta 1');

SELECT is(
  (SELECT ricerca_min_caratteri::int FROM ui.fn_lista_da_codice((SELECT dflt FROM _t_liste))),
  3,
  '9) ⭐ lista al default: il BB risponde 3');

SELECT is(
  (pg_temp.cfg((SELECT dflt FROM _t_liste)) ->> 'ricerca_min_caratteri')::int,
  3,
  '10) ⭐ … e la configurazione della schermata porta 3');

SELECT is(
  jsonb_typeof(pg_temp.cfg((SELECT uno FROM _t_liste)) -> 'ricerca_min_caratteri'),
  'number',
  '11) la chiave e'' un numero, non una stringa');

-- ============================================================
-- 12-15) Lista assente o spenta: lo stesso errore da tutti i lettori
-- ============================================================
SELECT throws_like(
  $$SELECT * FROM ui.fn_lista_da_codice('zz.pgtap.lista_che_non_esiste')$$,
  '%non trovata o non attiva%',
  '12) BB, lista inesistente: E_UI_LISTA_NON_TROVATA');

SELECT throws_like(
  format('SELECT * FROM ui.fn_lista_da_codice(%L)', (SELECT spenta FROM _t_liste)),
  '%non trovata o non attiva%',
  '13) BB, lista spenta: E_UI_LISTA_NON_TROVATA');

SELECT throws_like(
  $$SELECT pg_temp.cfg('zz.pgtap.lista_che_non_esiste')$$,
  '%non trovata o non attiva%',
  '14) risolutore, lista inesistente: E_UI_LISTA_NON_TROVATA (dal BB)');

SELECT throws_like(
  $$SELECT * FROM ui.fn_lista_colonne_ricerca_full('zz.pgtap.lista_che_non_esiste')$$,
  '%non trovata o non attiva%',
  '15) ricerca libera, lista inesistente: E_UI_LISTA_NON_TROVATA (dal BB)');

-- ============================================================
-- 16) ⭐ Il seed: le liste di configurazione a codici corti cercano da 1.
--     Elenco dal brief, sezione 4.2 (decisione di Tid del 2026-09-23).
--     Le liste di prova sono escluse per prefisso.
-- ============================================================
SELECT set_eq(
  $$SELECT codice::text FROM ui.lista_definizione
     WHERE ricerca_min_caratteri = 1
       AND codice NOT LIKE '\_pgtap.%'$$,
  $$VALUES ('catalogo.uom_tipi'), ('catalogo.unita_misura'), ('catalogo.conversioni_uom'),
           ('config.tipi_ruolo_tipi_indirizzo'), ('config.utilities_tipi_ruolo'),
           ('config.email_account'), ('config.email_template'),
           ('anagrafiche.categorie_clienti'), ('anagrafiche.categorie_clienti_listini'),
           ('documenti.template_documenti'), ('documenti.template_asset'),
           ('vendite.registri_numerazione'), ('vendite.famiglie_documento'),
           ('amm.processi'),
           -- ⭐ 2026-09-27 (brief-db-liste-datatable-grezze, righe 5 e 9): si
           --   cerca anche su codici di due caratteri — la sigla della
           --   provincia, l'ISO2 dello stato, il codice del reparto.
           ('amm.reparti'), ('config.province'), ('config.stati'),
           -- ⭐ 2026-10-31 (brief-db-liste-datatable-grezze-secondo-giro §2,
           --   riga 4): le unita' di misura di un articolo si cercano sul
           --   codice dell'UoM («KG», «PZ»), come catalogo.unita_misura.
           ('catalogo.articolo_uom')$$,
  '16) ⭐ le liste a 1 sono esattamente le diciotto dichiarate (codici corti)');

SELECT * FROM finish();
ROLLBACK;
