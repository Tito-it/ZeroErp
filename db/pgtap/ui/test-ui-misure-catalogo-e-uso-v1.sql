-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto e' ui.misure_pagina, che a runtime non scrive nessuno (all'app solo
--   SELECT, 90_end/20260930-13; nessuna funzione DB, nessun servizio BE): la scrive solo il CSV del
--   seed. Il trigger differito del default, il ritiro dalle preferenze e il lucchetto della misura
--   difendono da quello scrittore, che l'applicazione non puo' impersonare.
-- pgTAP test per Zero ERP
--
-- Test: le MISURE (righe per pagina e tetto della home), giro 3.
--   Brief: brief-db-revisione-ui, giro 3 (U15-U18, U20, U21 sul preset; Q9-Q12,
--   Q31, Q44-Q46).
--   ChangeSet: 00_schema/ui/20261120-36, -37; 20_code/ui/20261120-38 … -41;
--   90_end/20261120-42; il lucchetto in 80_data/sql/dbops/automation_lock_columns.csv.
--
-- ⭐ Il mondo si COSTRUISCE: due liste (una PAGINA, una COMPATTA) con una colonna
--   e un preset che non dice la misura, una dashboard col suo pool e un preset
--   che non dice il tetto, una misura di prova, un operatore umano. I default del
--   catalogo si leggono con ui.fn_misura_pagina_default: nessun numero del seed
--   decide un'asserzione.
-- ⚠️ I casi 15-16 (il lucchetto) chiedono il trigger montato dal runner
--   (20261120-42): prima dell'apply, nella prova sull'estratto, non ci sono.
--
-- Elenco test (plan 18):
--   La struttura
--    1) l'uso della misura e' l'enum ui.uso_misura_pagina, sulle due colonne
--    2) lista_definizione.uso_misura e' NOT NULL
--    3) le due misure dei preset non hanno un default di colonna
--   U15: il preset che non dice la misura
--    4) un INSERT che non nomina pagina_dimensione scrive NULL
--   U20: la lista dichiara l'uso
--    5) lista PAGINA, nessuna misura: il default PAGINA, origine catalogo
--    6) ⭐ lista COMPATTA, nessuna misura: il default COMPATTA
--    7) ... e lo standard che il drawer mostra e' lo stesso
--   U21: il tetto della home sul preset
--    8) un preset a 0 e' rifiutato dal CHECK
--    9) ... e cosi' uno a 101
--   10) un preset senza tetto risponde un tetto ammesso, origine catalogo
--   U16: il ritiro di una misura
--   11) ⭐ la misura ritirata esce dalla preferenza che la cita, le colonne restano
--   12) ... la preferenza con un'altra misura non cambia
--   13) ... e la preferenza si salva di nuovo
--   U18: un default per ogni uso
--   14) ⭐ togliere il default PAGINA senza spostarlo e' rifiutato
--   U17: la misura non si riscrive
--   15) ⭐ riscrivere una misura che nessun preset cita e' rifiutato
--   16) ... riscriverla uguale passa
--   U18, lo spostamento
--   17) spostare il default PAGINA nella stessa transazione passa
--   18) ... e il resolver risponde il default nuovo
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert, uso_misura)
  SELECT '_pgtap.misure_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Lista test pgTAP misure ' || v.n, 'pgtap', NULL, TRUE, '_pgtap', v.uso::ui.uso_misura_pagina
    FROM (VALUES (1, 'PAGINA'), (2, 'COMPATTA')) AS v(n, uso)
  RETURNING id, codice, uso_misura
)
SELECT id AS lista_id, codice AS lista_codice, uso_misura,
       row_number() OVER (ORDER BY id) AS n FROM ins;

CREATE TEMP TABLE _c AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default, user_insert)
  SELECT l.lista_id, 'c_' || l.n, 'c_' || l.n, 'campo_' || l.n, 'string', 10, '_pgtap' FROM _l l
  RETURNING id, lista_id
)
SELECT ins.id AS colonna_id, ins.lista_id, l.n FROM ins JOIN _l l USING (lista_id);

-- Il preset non nomina pagina_dimensione: e' il caso di U15.
CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, attivo, user_insert)
  SELECT lista_id, 'P_MISURE', 'Preset test misure', 'sistema', TRUE, '_pgtap' FROM _l
  RETURNING id, lista_id, pagina_dimensione
)
SELECT ins.id AS preset_id, ins.lista_id, ins.pagina_dimensione, l.n FROM ins JOIN _l l USING (lista_id);

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT p.preset_id, c.colonna_id, 1, TRUE, FALSE FROM _p p JOIN _c c ON c.n = p.n;

CREATE TEMP TABLE _d AS
WITH ins AS (
  INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
  SELECT '_pgtap.dash_misure_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Dashboard test pgTAP misure', TRUE, '_pgtap'
  RETURNING id, codice
)
SELECT id AS dashboard_id, codice AS dashboard_codice FROM ins;

CREATE TEMP TABLE _w AS
WITH ins AS (
  INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
  SELECT 'w_misure_' || substr(md5(clock_timestamp()::text), 1, 6), 'w_misure', 'kpi', TRUE, '_pgtap'
  RETURNING id
)
SELECT ins.id AS widget_id, d.dashboard_id FROM ins CROSS JOIN _d d;
INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT dashboard_id, widget_id, 10 FROM _w;

-- Il preset non nomina dimensione_max.
CREATE TEMP TABLE _dp AS
WITH ins AS (
  INSERT INTO ui.dashboard_preset (dashboard_id, codice, descrizione, ambito, attivo, user_insert)
  SELECT dashboard_id, 'P_MISURE', 'Preset test misure', 'sistema', TRUE, '_pgtap' FROM _d
  RETURNING id, dashboard_id
)
SELECT ins.id AS preset_id, ins.dashboard_id FROM ins;
INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 1, TRUE FROM _dp p JOIN _w w USING (dashboard_id);

CREATE TEMP TABLE _u AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-misure', false);

-- Le misure di prova: numeri che il catalogo non ha, solo offerte, e che
--   nessun preset cita (n = 1 si ritira in U16, n = 2 si prova col lucchetto).
CREATE TEMP TABLE _m AS
WITH ins AS (
  INSERT INTO ui.misure_pagina (misura, uso_default, user_insert)
  SELECT (SELECT max(misura) FROM ui.misure_pagina) + v.n * 7, NULL, '_pgtap'
    FROM (VALUES (1), (2)) AS v(n)
  RETURNING id, misura
)
SELECT id AS misura_id, misura, row_number() OVER (ORDER BY misura) AS n FROM ins;

CREATE FUNCTION pg_temp.lista(p_n integer) RETURNS jsonb LANGUAGE sql AS $f$
  SELECT ui.fn_resolve_lista_config((SELECT lista_codice FROM _l WHERE n = p_n),
                                    (SELECT auth_user_id FROM _u), NULL)
$f$;

-- ============================================================
-- 1-3 La struttura
-- ============================================================
SELECT is(
    (SELECT string_agg(format('%s.%s=%s', a.attrelid::regclass, a.attname, format_type(a.atttypid, NULL)), ','
                       ORDER BY a.attrelid::regclass::text COLLATE "C")
       FROM pg_catalog.pg_attribute a
      WHERE (a.attrelid, a.attname) IN (('ui.misure_pagina'::regclass, 'uso_default'),
                                        ('ui.lista_definizione'::regclass, 'uso_misura'))),
    'ui.lista_definizione.uso_misura=ui.uso_misura_pagina,ui.misure_pagina.uso_default=ui.uso_misura_pagina',
    '1) l''uso della misura e'' l''enum ui.uso_misura_pagina, sulle due colonne');

SELECT col_not_null('ui', 'lista_definizione', 'uso_misura',
    '2) lista_definizione.uso_misura e'' NOT NULL');

SELECT is(
    (SELECT string_agg(format('%s.%s=%s', a.attrelid::regclass, a.attname, a.atthasdef::text), ','
                       ORDER BY a.attrelid::regclass::text COLLATE "C")
       FROM pg_catalog.pg_attribute a
      WHERE (a.attrelid, a.attname) IN (('ui.lista_preset'::regclass, 'pagina_dimensione'),
                                        ('ui.dashboard_preset'::regclass, 'dimensione_max'))),
    'ui.dashboard_preset.dimensione_max=false,ui.lista_preset.pagina_dimensione=false',
    '3) le due misure dei preset non hanno un default di colonna');

-- ============================================================
-- 4 U15
-- ============================================================
SELECT is((SELECT count(*) FROM _p WHERE pagina_dimensione IS NULL), 2::bigint,
          '4) un INSERT che non nomina pagina_dimensione scrive NULL');

-- ============================================================
-- 5-7 U20
-- ============================================================
SELECT is(format('%s|%s', pg_temp.lista(1) ->> 'pagina_dimensione', pg_temp.lista(1) #>> '{origine,pagina_dimensione}'),
          format('%s|catalogo', ui.fn_misura_pagina_default('PAGINA')),
          '5) lista PAGINA, nessuna misura: il default PAGINA, origine catalogo');

SELECT is((pg_temp.lista(2) ->> 'pagina_dimensione')::integer,
          ui.fn_misura_pagina_default('COMPATTA'),
          '6) lista COMPATTA, nessuna misura: il default COMPATTA');

SELECT is((pg_temp.lista(2) ->> 'pagina_dimensione_standard')::integer,
          ui.fn_misura_pagina_default('COMPATTA'),
          '7) ... e lo standard che il drawer mostra e'' lo stesso');

-- ============================================================
-- 8-10 U21
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.dashboard_preset SET dimensione_max = 0 WHERE id = (SELECT preset_id FROM _dp)$$),
          'chk_ui_dashboard_preset_dimensione_max',
          '8) un preset a 0 e'' rifiutato dal CHECK');

SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.dashboard_preset SET dimensione_max = 101 WHERE id = (SELECT preset_id FROM _dp)$$),
          'chk_ui_dashboard_preset_dimensione_max',
          '9) ... e cosi'' uno a 101');

SELECT is(
    (SELECT format('%s|%s', ui.fn_dimensione_max_ammessa((r ->> 'dimensione_max')::integer)::text,
                   r #>> '{origine,dimensione_max}')
       FROM (SELECT ui.fn_resolve_dashboard_config((SELECT dashboard_codice FROM _d),
                                                   (SELECT auth_user_id FROM _u), NULL) AS r) x),
    'true|catalogo',
    '10) un preset senza tetto risponde un tetto ammesso, origine catalogo');

-- ============================================================
-- 11-13 U16
-- ============================================================
INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, preset_base_id, configurazione)
SELECT (SELECT auth_user_id FROM _u), l.lista_id, p.preset_id,
       jsonb_build_object(
           'colonne', jsonb_build_array(jsonb_build_object('codice', 'c_' || l.n, 'ordine', 1)),
           'pagina_dimensione', CASE l.n WHEN 1 THEN (SELECT misura FROM _m WHERE n = 1)
                                         ELSE ui.fn_misura_pagina_default('PAGINA') END)
  FROM _l l JOIN _p p USING (lista_id);

DELETE FROM ui.misure_pagina WHERE id = (SELECT misura_id FROM _m WHERE n = 1);

SELECT is(
    (SELECT pu.configurazione FROM ui.lista_preferenza_utente pu
      WHERE pu.auth_user_id = (SELECT auth_user_id FROM _u) AND pu.lista_id = (SELECT lista_id FROM _l WHERE n = 1)),
    jsonb_build_object('colonne', jsonb_build_array(jsonb_build_object('codice', 'c_1', 'ordine', 1))),
    '11) la misura ritirata esce dalla preferenza che la cita, le colonne restano');

SELECT is(
    (SELECT (pu.configurazione ->> 'pagina_dimensione')::integer FROM ui.lista_preferenza_utente pu
      WHERE pu.auth_user_id = (SELECT auth_user_id FROM _u) AND pu.lista_id = (SELECT lista_id FROM _l WHERE n = 2)),
    ui.fn_misura_pagina_default('PAGINA'),
    '12) ... la preferenza con un''altra misura non cambia');

SELECT lives_ok($$
    UPDATE ui.lista_preferenza_utente
       SET configurazione = jsonb_build_object('colonne',
               jsonb_build_array(jsonb_build_object('codice', 'c_1', 'ordine', 2)))
     WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND lista_id = (SELECT lista_id FROM _l WHERE n = 1)$$,
    '13) ... e la preferenza si salva di nuovo');

-- ============================================================
-- 14 U18 (in IMMEDIATE il trigger differito scatta a fine istruzione)
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.misure_pagina SET uso_default = NULL WHERE uso_default = 'PAGINA'$$),
          'E_UI_MISURA_PAGINA_DEFAULT_MANCANTE',
          '14) togliere il default PAGINA senza spostarlo e'' rifiutato');

-- ============================================================
-- 15-16 U17 (il lucchetto lo monta il runner, 20261120-42)
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.misure_pagina SET misura = misura + 1 WHERE id = (SELECT misura_id FROM _m WHERE n = 2)$$),
          'E_UI_MISURA_PAGINA_IMMUTABILE',
          '15) riscrivere una misura che nessun preset cita e'' rifiutato');

SELECT lives_ok($$UPDATE ui.misure_pagina SET misura = misura$$,
                '16) ... riscriverla uguale passa');

-- ============================================================
-- 17-18 U18, lo spostamento: in DEFERRED si giudica a fine transazione
--   (qui: al ritorno in IMMEDIATE, che fa scattare gli eventi in sospeso)
-- ============================================================
CREATE TEMP TABLE _sposta AS
SELECT (SELECT id FROM ui.misure_pagina WHERE uso_default = 'PAGINA') AS da_id,
       (SELECT min(id) FROM ui.misure_pagina WHERE uso_default IS NULL) AS a_id;

SET CONSTRAINTS ui.trg_misure_pagina_a10_guard_default_per_uso_ins_upd_dlt DEFERRED;
UPDATE ui.misure_pagina SET uso_default = NULL     WHERE id = (SELECT da_id FROM _sposta);
UPDATE ui.misure_pagina SET uso_default = 'PAGINA' WHERE id = (SELECT a_id FROM _sposta);
SELECT lives_ok($$SET CONSTRAINTS ui.trg_misure_pagina_a10_guard_default_per_uso_ins_upd_dlt IMMEDIATE$$,
                '17) spostare il default PAGINA nella stessa transazione passa');

SELECT is((pg_temp.lista(1) ->> 'pagina_dimensione')::integer,
          (SELECT misura FROM ui.misure_pagina WHERE id = (SELECT a_id FROM _sposta)),
          '18) ... e il resolver risponde il default nuovo');

SELECT * FROM finish();
ROLLBACK;
