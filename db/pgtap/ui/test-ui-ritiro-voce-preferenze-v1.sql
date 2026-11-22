-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture fabbrica una dashboard col suo pool e le sue
--   card, che l'applicazione non scrive: lo fa solo il migratore. Le colonne
--   che la fixture scrive nascono dal seed di primo impianto, e il migratore le
--   ritira dalla porta di manutenzione, la strada vera del ritiro (come
--   80_data/changelog/20261121-01). Il trigger del ritiro e i lucchetti non
--   esentano il proprietario. Tutto in transazione annullata.
-- pgTAP test per Zero ERP
--
-- Test: il RITIRO di una colonna della lista o di una card del pool toglie la
--   voce dalle preferenze, e le strade dell'UPDATE sono chiuse dal lucchetto.
--   Brief: brief-db-revisione-ui, Q55 (a) (dal /verifica-db del giro 2).
--   ChangeSet: 20_code/ui/20261122-26, 90_end/20261122-28; i lucchetti in
--   80_data/sql/dbops/automation_lock_columns.csv.
--
-- ⭐ Il mondo si COSTRUISCE: due liste con le stesse colonne (c_uno, c_due,
--   c_tre), una dashboard con due card nel pool, un operatore umano con le sue
--   preferenze. Nessun dato esistente decide un'asserzione.
--
-- Elenco test (plan 15):
--   Il building block (ui.fn_configurazione_senza_codici)
--    1) toglie le voci dei codici dati e tiene le altre, nel loro ordine
--    2) l'elenco che resta vuoto esce
--    3) una configurazione senza voci di quei codici torna com'e', anche un [] salvato
--   Il ritiro di una colonna
--    4) ⭐ la voce della colonna ritirata esce dalla preferenza della lista
--    5) ... e la preferenza dell'altra lista, con lo stesso codice, non cambia
--    6) ⭐ Q55, il controesempio: dopo il ritiro l'utente cambia la sola misura e salva
--    7) la preferenza la cui unica voce era la colonna ritirata segue il preset
--   Il ritiro di una card dal pool
--    8) ⭐ la voce della card esce dalla preferenza della dashboard
--    9) ... e dopo il ritiro la preferenza si salva
--   15) ... e la preferenza di un'altra dashboard, con la stessa card nel pool,
--       non cambia (aggiunto dal /verifica-db del 2026-11-22; numerato in coda)
--   I lucchetti
--   10) una colonna non cambia lista: E_UI_COLONNA_CODICE_IMMUTABILE
--   11) una riga del pool non cambia dashboard: E_UI_WIDGET_IMMUTABILE
--   12) ... ne' card: E_UI_WIDGET_IMMUTABILE
--   13) il codice di una card non si riscrive: E_UI_WIDGET_IMMUTABILE
--   La struttura
--   14) la funzione del ritiro e' montata AFTER DELETE sulle due tabelle
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  SELECT '_pgtap.ritiro_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Lista test pgTAP ritiro ' || v.n, 'pgtap', NULL, TRUE, '_pgtap'
    FROM (VALUES (1), (2)) AS v(n)
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice, row_number() OVER (ORDER BY id) AS n FROM ins;

CREATE TEMP TABLE _c AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default, user_insert)
  SELECT l.lista_id, v.codice, v.codice, 'campo_' || v.codice, 'string', v.ordine, '_pgtap'
    FROM _l l,
         (VALUES ('c_uno', 10), ('c_due', 20), ('c_tre', 30)) AS v(codice, ordine)
  RETURNING id, lista_id, codice
)
SELECT ins.id AS colonna_id, ins.lista_id, ins.codice, l.n FROM ins JOIN _l l USING (lista_id);

CREATE TEMP TABLE _d AS
WITH ins AS (
  INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
  SELECT '_pgtap.dash_ritiro_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Dashboard test pgTAP ritiro ' || v.n, TRUE, '_pgtap'
    FROM (VALUES (1), (2)) AS v(n)
  RETURNING id
)
SELECT id AS dashboard_id, row_number() OVER (ORDER BY id) AS n FROM ins;

-- Due card nel pool della prima dashboard.
CREATE TEMP TABLE _w AS
WITH ins AS (
  INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
  SELECT 'w_ritiro_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6), 'w_' || v.n, 'kpi', TRUE, '_pgtap'
    FROM (VALUES (1), (2)) AS v(n)
  RETURNING id, codice, etichetta
)
SELECT id AS widget_id, codice, substr(etichetta, 3)::int AS n FROM ins;
INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT (SELECT dashboard_id FROM _d WHERE n = 1), widget_id, 10 * n FROM _w;
-- La seconda card anche nel pool della seconda dashboard: il ritiro dalla
-- prima non tocca le preferenze dell'altra (caso 15).
INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT (SELECT dashboard_id FROM _d WHERE n = 2), widget_id, 10 FROM _w WHERE n = 2;

CREATE TEMP TABLE _u AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-ritiro-voce-preferenze', false);
CREATE TEMP TABLE _u2 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-ritiro-voce-preferenze-2', false);

-- Le preferenze: sulla prima lista c_uno, c_due, c_tre (u) e la sola c_due (u2);
-- sulla seconda lista c_due (u). Sulla dashboard le due card (u).
INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, configurazione)
VALUES ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l WHERE n = 1),
        '{"colonne": [{"codice": "c_uno", "ordine": 1}, {"codice": "c_due", "ordine": 2},
                      {"codice": "c_tre", "ordine": 3, "visibile": false}]}'::jsonb),
       ((SELECT auth_user_id FROM _u2), (SELECT lista_id FROM _l WHERE n = 1),
        '{"colonne": [{"codice": "c_due", "ordine": 1}]}'::jsonb),
       ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l WHERE n = 2),
        '{"colonne": [{"codice": "c_due", "ordine": 1}]}'::jsonb);
INSERT INTO ui.dashboard_preferenza_utente (auth_user_id, dashboard_id, configurazione)
SELECT (SELECT auth_user_id FROM _u), (SELECT dashboard_id FROM _d WHERE n = 1),
       jsonb_build_object('widget', jsonb_build_array(
           jsonb_build_object('codice', (SELECT codice FROM _w WHERE n = 1), 'ordine', 1),
           jsonb_build_object('codice', (SELECT codice FROM _w WHERE n = 2), 'ordine', 2)))
UNION ALL
SELECT (SELECT auth_user_id FROM _u), (SELECT dashboard_id FROM _d WHERE n = 2),
       jsonb_build_object('widget', jsonb_build_array(
           jsonb_build_object('codice', (SELECT codice FROM _w WHERE n = 2), 'ordine', 1)));

-- La preferenza di (utente, lista), per i confronti.
CREATE FUNCTION pg_temp.pref(p_utente integer, p_lista_n integer) RETURNS jsonb LANGUAGE sql AS $$
    SELECT pu.configurazione FROM ui.lista_preferenza_utente pu
     WHERE pu.auth_user_id = p_utente AND pu.lista_id = (SELECT lista_id FROM _l WHERE n = p_lista_n)
$$;

-- ============================================================
-- 1-3 Il building block
-- ============================================================
SELECT is(ui.fn_configurazione_senza_codici(
              '{"colonne": [{"codice": "a"}, {"codice": "b"}, {"codice": "c"}], "pagina_dimensione": 25}'::jsonb,
              'colonne', ARRAY['b']::varchar[]),
          '{"colonne": [{"codice": "a"}, {"codice": "c"}], "pagina_dimensione": 25}'::jsonb,
          '1) toglie le voci dei codici dati e tiene le altre, nel loro ordine');
SELECT is(ui.fn_configurazione_senza_codici(
              '{"widget": [{"codice": "a"}], "dimensione_max": 6}'::jsonb, 'widget', ARRAY['a']::varchar[]),
          '{"dimensione_max": 6}'::jsonb,
          '2) l''elenco che resta vuoto esce');
SELECT ok(ui.fn_configurazione_senza_codici('{"colonne": [{"codice": "a"}]}'::jsonb, 'colonne', ARRAY['z']::varchar[])
              = '{"colonne": [{"codice": "a"}]}'::jsonb
          AND ui.fn_configurazione_senza_codici('{"colonne": []}'::jsonb, 'colonne', ARRAY['z']::varchar[])
              = '{"colonne": []}'::jsonb,
          '3) senza voci di quei codici la configurazione torna com''e'', anche un [] salvato');

-- ============================================================
-- 4-7 Il ritiro di una colonna
-- ============================================================
-- Le colonne della fixture sono nate dal seed: il migratore le ritira dalla porta.
SET LOCAL zeroerp.allow_seed_primo_impianto_override = 'on';
DELETE FROM ui.lista_colonna
 WHERE id = (SELECT colonna_id FROM _c WHERE n = 1 AND codice = 'c_due');
RESET zeroerp.allow_seed_primo_impianto_override;

SELECT is(pg_temp.pref((SELECT auth_user_id FROM _u), 1),
          '{"colonne": [{"codice": "c_uno", "ordine": 1}, {"codice": "c_tre", "ordine": 3, "visibile": false}]}'::jsonb,
          '4) la voce della colonna ritirata esce dalla preferenza della lista');
SELECT is(pg_temp.pref((SELECT auth_user_id FROM _u), 2),
          '{"colonne": [{"codice": "c_due", "ordine": 1}]}'::jsonb,
          '5) la preferenza dell''altra lista, con lo stesso codice, non cambia');
SELECT lives_ok($$
        UPDATE ui.lista_preferenza_utente
           SET configurazione = configurazione
                                || jsonb_build_object('pagina_dimensione', (SELECT min(m.misura) FROM ui.misure_pagina m))
         WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND lista_id = (SELECT lista_id FROM _l WHERE n = 1)$$,
          '6) Q55: dopo il ritiro l''utente cambia la sola misura, e la preferenza si salva');
SELECT is(pg_temp.pref((SELECT auth_user_id FROM _u2), 1),
          '{}'::jsonb,
          '7) la preferenza la cui unica voce era la colonna ritirata segue il preset');

-- ============================================================
-- 8-9 Il ritiro di una card dal pool
-- ============================================================
DELETE FROM ui.dashboard_widget
 WHERE dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 1)
   AND widget_id    = (SELECT widget_id FROM _w WHERE n = 2);

SELECT is((SELECT pu.configurazione FROM ui.dashboard_preferenza_utente pu
            WHERE pu.auth_user_id = (SELECT auth_user_id FROM _u)
              AND pu.dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 1)),
          jsonb_build_object('widget', jsonb_build_array(
              jsonb_build_object('codice', (SELECT codice FROM _w WHERE n = 1), 'ordine', 1))),
          '8) la voce della card esce dalla preferenza della dashboard');
SELECT lives_ok($$
        UPDATE ui.dashboard_preferenza_utente
           SET configurazione = configurazione || '{"dimensione_max": 6}'::jsonb
         WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 1)$$,
          '9) ... e dopo il ritiro la preferenza si salva');
SELECT is((SELECT pu.configurazione FROM ui.dashboard_preferenza_utente pu
            WHERE pu.auth_user_id = (SELECT auth_user_id FROM _u)
              AND pu.dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 2)),
          jsonb_build_object('widget', jsonb_build_array(
              jsonb_build_object('codice', (SELECT codice FROM _w WHERE n = 2), 'ordine', 1))),
          '15) ... e la preferenza di un''altra dashboard, con la stessa card nel pool, non cambia');

-- ============================================================
-- 10-13 I lucchetti
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.lista_colonna SET lista_id = (SELECT lista_id FROM _l WHERE n = 2)
         WHERE id = (SELECT colonna_id FROM _c WHERE n = 1 AND codice = 'c_uno')$$),
          'E_UI_COLONNA_CODICE_IMMUTABILE',
          '10) una colonna non cambia lista');
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.dashboard_widget SET dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 2)
         WHERE widget_id = (SELECT widget_id FROM _w WHERE n = 1)$$),
          'E_UI_WIDGET_IMMUTABILE',
          '11) una riga del pool non cambia dashboard');
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.dashboard_widget SET widget_id = (SELECT widget_id FROM _w WHERE n = 2)
         WHERE widget_id = (SELECT widget_id FROM _w WHERE n = 1)$$),
          'E_UI_WIDGET_IMMUTABILE',
          '12) ... ne'' card');
SELECT is(dbops.fn_pgtap_codice_errore($$
        UPDATE ui.widget SET codice = codice || '_x' WHERE id = (SELECT widget_id FROM _w WHERE n = 1)$$),
          'E_UI_WIDGET_IMMUTABILE',
          '13) il codice di una card non si riscrive');

-- ============================================================
-- 14 La struttura
-- ============================================================
-- Per funzione e tabella, non per nome (linee-guida-trigger).
-- Schema e nome dal catalogo: regclass::text dipende dal search_path.
SELECT is((SELECT array_agg(n.nspname || '.' || c.relname ORDER BY n.nspname || '.' || c.relname)
             FROM pg_catalog.pg_trigger t
             JOIN pg_catalog.pg_class c     ON c.oid = t.tgrelid
             JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE t.tgfoid = 'ui.trgfn_voce_ritira_dalle_preferenze()'::regprocedure
              AND NOT t.tgisinternal
              AND (t.tgtype::int & 1) = 1              -- ROW
              AND (t.tgtype::int & 2) = 0              -- non BEFORE: AFTER
              AND (t.tgtype::int & 8) = 8              -- DELETE
              AND (t.tgtype::int & (4 | 16)) = 0),     -- solo DELETE
          ARRAY['ui.dashboard_widget', 'ui.lista_colonna'],
          '14) la funzione del ritiro e'' montata AFTER DELETE per riga su ui.lista_colonna e ui.dashboard_widget');

SELECT * FROM finish();
ROLLBACK;
