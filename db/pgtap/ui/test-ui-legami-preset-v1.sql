-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture fabbrica una dashboard col suo pool e i suoi preset, e il catalogo
--   delle dashboard l'applicazione non lo scrive: lo scrive solo il migratore, dal CSV (U31, la porta
--   di 90_end/20261120-60). Nessun caso del test dipende dall'identita' di chi scrive: i guard che
--   prova (legami, lucchetti, snapshot, scelta del preset) non esentano il proprietario. Il
--   preset di lista che la fixture scrive nasce dal seed: il caso 11 lo cancella dalla porta.
-- pgTAP test per Zero ERP
--
-- Test: i LEGAMI fra preset, composizioni, pool e preferenze (U14).
--   Brief: brief-db-revisione-ui, giro 2b (U14 con Q8 e Q41 (a)).
--   ChangeSet: 00_schema/ui/20261120-32, 20_code/ui/20261120-33, -34,
--   90_end/20261120-35; i lucchetti in 80_data/sql/dbops/automation_lock_columns.csv.
--
-- ⭐ Il mondo si COSTRUISCE: due liste con una colonna ciascuna, un preset per
--   lista, due dashboard col loro pool e un preset ciascuna, un operatore umano.
--   Nessun dato esistente decide un'asserzione.
--
-- Elenco test (plan 14):
--   La composizione delle liste
--    1) la lista della riga la scrive il DB, dal preset
--    2) ... e un valore passato e' sostituito
--    3) ⭐ una colonna di un'altra lista e' rifiutata
--    4) la lista di una colonna che un preset nomina non cambia
--   La composizione delle dashboard
--    5) la dashboard della riga la scrive il DB, dal preset
--    6) ⭐ un widget fuori dal pool e' rifiutato
--    7) ⭐ Q8: togliere dal pool un widget proposto e' rifiutato, col nome del preset
--    8) ... e tolto dal preset, esce dal pool
--   Le preferenze
--    9) ⭐ il preset di base di un'altra lista e' rifiutato
--   10) ... e cosi' quello di un'altra dashboard
--   11) cancellato il preset, la preferenza resta senza base
--   La testata del preset
--   12) cambiare la lista di un preset e' rifiutato
--   13) ... e cosi' l'ambito di un preset di dashboard
--   14) riscrivere il posto uguale passa
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  SELECT '_pgtap.legami_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Lista test pgTAP legami ' || v.n, 'pgtap', NULL, TRUE, '_pgtap'
    FROM (VALUES (1), (2)) AS v(n)
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice, row_number() OVER (ORDER BY id) AS n FROM ins;

CREATE TEMP TABLE _c AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default, user_insert)
  SELECT l.lista_id, 'c_' || l.n, 'c_' || l.n, 'campo_' || l.n, 'string', 10, '_pgtap' FROM _l l
  RETURNING id, lista_id
)
SELECT ins.id AS colonna_id, ins.lista_id, l.n FROM ins JOIN _l l USING (lista_id);

CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, attivo, user_insert)
  SELECT lista_id, 'P_LEGAMI', 'Preset test legami', 'sistema', TRUE, '_pgtap' FROM _l
  RETURNING id, lista_id
)
SELECT ins.id AS preset_id, ins.lista_id, l.n FROM ins JOIN _l l USING (lista_id);

CREATE TEMP TABLE _d AS
WITH ins AS (
  INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
  SELECT '_pgtap.dash_legami_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Dashboard test pgTAP legami ' || v.n, TRUE, '_pgtap'
    FROM (VALUES (1), (2)) AS v(n)
  RETURNING id, codice
)
SELECT id AS dashboard_id, codice AS dashboard_codice, row_number() OVER (ORDER BY id) AS n FROM ins;

-- Un widget per dashboard, nel suo pool.
CREATE TEMP TABLE _w AS
WITH ins AS (
  INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
  SELECT 'w_legami_' || d.n || '_' || substr(md5(clock_timestamp()::text), 1, 6), 'w_' || d.n, 'kpi', TRUE, '_pgtap'
    FROM _d d
  RETURNING id, codice, etichetta
)
SELECT ins.id AS widget_id, ins.codice, d.dashboard_id, d.n
  FROM ins JOIN _d d ON ins.etichetta = 'w_' || d.n;
INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT dashboard_id, widget_id, 10 FROM _w;

CREATE TEMP TABLE _dp AS
WITH ins AS (
  INSERT INTO ui.dashboard_preset (dashboard_id, codice, descrizione, ambito, attivo, user_insert)
  SELECT dashboard_id, 'P_LEGAMI_' || n, 'Preset test legami', 'sistema', TRUE, '_pgtap' FROM _d
  RETURNING id, dashboard_id
)
SELECT ins.id AS preset_id, ins.dashboard_id, d.n FROM ins JOIN _d d USING (dashboard_id);

CREATE TEMP TABLE _u AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-legami-preset', false);

-- ============================================================
-- 1-4 La composizione delle liste
-- ============================================================
INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT p.preset_id, c.colonna_id, 1, TRUE, FALSE FROM _p p JOIN _c c ON c.n = p.n AND p.n = 1;

SELECT is((SELECT pc.lista_id FROM ui.lista_preset_colonna pc WHERE pc.preset_id = (SELECT preset_id FROM _p WHERE n = 1)),
          (SELECT lista_id FROM _l WHERE n = 1)::integer,
          '1) la lista della riga la scrive il DB, dal preset');

UPDATE ui.lista_preset_colonna SET lista_id = (SELECT lista_id FROM _l WHERE n = 2)
 WHERE preset_id = (SELECT preset_id FROM _p WHERE n = 1);
SELECT is((SELECT pc.lista_id FROM ui.lista_preset_colonna pc WHERE pc.preset_id = (SELECT preset_id FROM _p WHERE n = 1)),
          (SELECT lista_id FROM _l WHERE n = 1)::integer,
          '2) ... e un valore passato e'' sostituito');

SELECT is(dbops.fn_pgtap_codice_errore($$
        INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
        SELECT (SELECT preset_id FROM _p WHERE n = 1), (SELECT colonna_id FROM _c WHERE n = 2), 2, TRUE, FALSE$$),
          'fk_ui_lista_preset_colonna_colonna_della_lista',
          '3) una colonna di un''altra lista e'' rifiutata');

-- Dal 2026-11-22 (Q55, 90_end/20261122-28) lista_colonna.lista_id e' sotto
-- lucchetto, che parla prima della FK composita: la FK resta la rete (la prova
-- l'INSERT del caso 3), e la frase che l'operatore legge e' quella del lucchetto.
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.lista_colonna SET lista_id = (SELECT lista_id FROM _l WHERE n = 2)
         WHERE id = (SELECT colonna_id FROM _c WHERE n = 1)$$),
          'E_UI_COLONNA_CODICE_IMMUTABILE',
          '4) la lista di una colonna che un preset nomina non cambia (il lucchetto, poi la FK)');

-- ============================================================
-- 5-8 La composizione delle dashboard
-- ============================================================
INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 1, TRUE FROM _dp p JOIN _w w ON w.n = p.n AND p.n = 1;

SELECT is((SELECT pw.dashboard_id FROM ui.dashboard_preset_widget pw WHERE pw.preset_id = (SELECT preset_id FROM _dp WHERE n = 1)),
          (SELECT dashboard_id FROM _d WHERE n = 1)::integer,
          '5) la dashboard della riga la scrive il DB, dal preset');

SELECT is(dbops.fn_pgtap_codice_errore($$
        INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
        SELECT (SELECT preset_id FROM _dp WHERE n = 1), (SELECT widget_id FROM _w WHERE n = 2), 2, TRUE$$),
          'fk_ui_dashboard_preset_widget_pool',
          '6) un widget fuori dal pool e'' rifiutato');

SELECT throws_like(
    $$DELETE FROM ui.dashboard_widget
       WHERE dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 1)
         AND widget_id = (SELECT widget_id FROM _w WHERE n = 1)$$,
    '%P_LEGAMI_1%',
    '7) Q8: togliere dal pool un widget proposto e'' rifiutato, col nome del preset');

DELETE FROM ui.dashboard_preset_widget WHERE preset_id = (SELECT preset_id FROM _dp WHERE n = 1);
SELECT lives_ok(
    $$DELETE FROM ui.dashboard_widget
       WHERE dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 1)
         AND widget_id = (SELECT widget_id FROM _w WHERE n = 1)$$,
    '8) ... e tolto dal preset, esce dal pool');

-- ============================================================
-- 9-11 Le preferenze
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore($$
        INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, preset_base_id, configurazione)
        VALUES ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l WHERE n = 1),
                (SELECT preset_id FROM _p WHERE n = 2), '{}')$$),
          'fk_ui_lista_preferenza_utente_preset_della_lista',
          '9) il preset di base di un''altra lista e'' rifiutato');

SELECT is(dbops.fn_pgtap_codice_errore($$
        INSERT INTO ui.dashboard_preferenza_utente (auth_user_id, dashboard_id, preset_base_id, configurazione)
        VALUES ((SELECT auth_user_id FROM _u), (SELECT dashboard_id FROM _d WHERE n = 1),
                (SELECT preset_id FROM _dp WHERE n = 2), '{}')$$),
          'fk_ui_dashboard_preferenza_utente_preset_della_dashboard',
          '10) ... e cosi'' quello di un''altra dashboard');

INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, preset_base_id, configurazione)
VALUES ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l WHERE n = 2), (SELECT preset_id FROM _p WHERE n = 2), '{}');
-- Il runner e' il migratore: il preset che la fixture ha scritto e' nato dal seed
-- (script.trgfn_seed_primo_impianto), e il migratore lo cancella solo dalla porta di
-- manutenzione, il DELETE forward-only. E' la strada vera: il caso prova la FK, non chi cancella.
SET LOCAL zeroerp.allow_seed_primo_impianto_override = 'on';
DELETE FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p WHERE n = 2);
RESET zeroerp.allow_seed_primo_impianto_override;
SELECT is((SELECT pu.preset_base_id FROM ui.lista_preferenza_utente pu
            WHERE pu.auth_user_id = (SELECT auth_user_id FROM _u) AND pu.lista_id = (SELECT lista_id FROM _l WHERE n = 2)),
          NULL::integer,
          '11) cancellato il preset, la preferenza resta senza base');

-- ============================================================
-- 12-14 La testata del preset
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.lista_preset SET lista_id = (SELECT lista_id FROM _l WHERE n = 2)
         WHERE id = (SELECT preset_id FROM _p WHERE n = 1)$$),
          'E_UI_PRESET_POSTO_IMMUTABILE',
          '12) cambiare la lista di un preset e'' rifiutato');
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.dashboard_preset SET ambito = 'emittente_fiscale'
         WHERE id = (SELECT preset_id FROM _dp WHERE n = 2)$$),
          'E_UI_PRESET_POSTO_IMMUTABILE',
          '13) ... e cosi'' l''ambito di un preset di dashboard');
SELECT lives_ok($$UPDATE ui.lista_preset SET lista_id = lista_id, ambito = ambito,
                         profilo_accesso_id = profilo_accesso_id, emittente_fiscale_id = emittente_fiscale_id
                   WHERE id = (SELECT preset_id FROM _p WHERE n = 1)$$,
                '14) riscrivere il posto uguale passa');

SELECT * FROM finish();
ROLLBACK;
