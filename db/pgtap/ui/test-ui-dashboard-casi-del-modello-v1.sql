-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce il catalogo delle dashboard (definizione, widget, pool,
--   preset e composizione), un'area funzionale e due azioni di processo, che l'applicazione legge
--   soltanto (all'app il solo SELECT); e una vista materializzata, che l'applicazione non crea. I
--   casi giudicano la risoluzione e i guard per chiunque scriva, non la porta dell'applicazione.
-- pgTAP test per Zero ERP
--
-- Test: i casi del modello delle DASHBOARD che nessun altro test costruiva, e la
--   lista su una vista materializzata.
--   Brief: brief-db-revisione-ui, giro 6c (§3.6-quater, Q53 (a)).
--
-- ⭐ Il mondo si COSTRUISCE: un'area e due azioni, una dashboard con quattro
--   widget nel pool (uno sull'azione concessa, uno su quella non concessa, uno
--   sulla sola area, uno libero), un preset di sistema, due operatori umani (uno
--   con l'azione concessa, uno senza niente). Nessuna riga del seed decide
--   un'asserzione.
--
-- Elenco test (plan 6):
--   Chi vede il widget
--    1) ⭐ con l'azione concessa (e l'area aperta al suo minimo): il widget
--       dell'azione, quello della sola area e quello libero; non quello
--       dell'altra azione
--    2) ⭐ senza area ne' azione: il solo widget libero
--   Lo snapshot del preset di base
--    3) ⭐ la preferenza di dashboard nasce con uno snapshot passato da chi scrive:
--       conta quello del preset
--    4) ... e cambiare base e snapshot nella stessa UPDATE: quello della base nuova
--   La vista materializzata
--    5) una lista si registra su una vista materializzata
--    6) ... e una sua colonna sul campo della vista passa
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _sfx AS SELECT upper(substr(md5(clock_timestamp()::text), 1, 8)) AS s;

CREATE TEMP TABLE _area AS
WITH ins AS (
  INSERT INTO config.aree_funzionali (codice, codice_interno, descrizione, schema_db)
  SELECT '_PGTAP_DCM_' || s, '_PGTAP_DCM_' || s, 'pgTAP casi del modello, area', 'ui' FROM _sfx
  RETURNING id
)
SELECT id AS area_id FROM ins;

CREATE TEMP TABLE _az AS
WITH ins AS (
  INSERT INTO config.azioni_processo (area_id, permission_codename, descrizione)
  SELECT (SELECT area_id FROM _area), '_pgtap_dcm_' || v.n || '_' || lower(s),
         'pgTAP casi del modello, azione ' || v.n
    FROM _sfx CROSS JOIN (VALUES (1), (2)) v(n)
  RETURNING id, permission_codename
)
SELECT id AS azione_id, permission_codename, row_number() OVER (ORDER BY id) AS n FROM ins;

CREATE TEMP TABLE _d AS
WITH ins AS (
  INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
  SELECT '_pgtap.dash_casi_' || lower(s), 'Dashboard test pgTAP casi del modello', TRUE, 'pgtap' FROM _sfx
  RETURNING id, codice
)
SELECT id AS dashboard_id, codice AS dashboard_codice FROM ins;

-- I quattro widget: (codice, area, azione).
CREATE TEMP TABLE _w AS
WITH ins AS (
  INSERT INTO ui.widget (codice, etichetta, tipo_widget, area_id, azione_id, attivo, user_insert)
  SELECT 'w_dcm_' || v.k || '_' || lower(s), 'w_dcm_' || v.k, 'kpi',
         CASE WHEN v.con_area THEN (SELECT area_id FROM _area) END,
         (SELECT azione_id FROM _az WHERE n = v.azione), TRUE, 'pgtap'
    FROM _sfx CROSS JOIN (VALUES ('azione1', true, 1), ('azione2', true, 2),
                                 ('area', true, NULL), ('libero', false, NULL)) v(k, con_area, azione)
  RETURNING id, codice
)
SELECT id AS widget_id, codice, split_part(codice, '_', 3) AS k FROM ins;

INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT (SELECT dashboard_id FROM _d), w.widget_id, row_number() OVER (ORDER BY w.widget_id) * 10 FROM _w w;

-- Due preset di sistema: il primo acceso, il secondo spento (la base nuova del caso 4
--   e' il primo, ripreso dopo il cambio).
CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.dashboard_preset (dashboard_id, codice, descrizione, ambito, attivo, user_insert)
  SELECT (SELECT dashboard_id FROM _d), v.codice, 'Preset test casi del modello', 'sistema', v.attivo, 'pgtap'
    FROM (VALUES ('P_SIS', true), ('P_BOZZA', false)) v(codice, attivo)
  RETURNING id, codice
)
SELECT id AS preset_id, codice FROM ins;

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 1, TRUE FROM _p p JOIN _w w ON w.k = 'libero';

CREATE TEMP TABLE _u AS
SELECT 'con' AS chi, o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-dash-casi-con', false) o;
INSERT INTO _u SELECT 'senza', o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-dash-casi-senza', false) o;

DO $concedi$
BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _u WHERE chi = 'con'),
                                          (SELECT permission_codename FROM _az WHERE n = 1));
END
$concedi$;

-- I widget che la dashboard mostra a un utente, per chiave del widget.
CREATE FUNCTION pg_temp.visibili(p_chi text) RETURNS text LANGUAGE sql AS $f$
  SELECT string_agg(w.k, ',' ORDER BY w.k)
    FROM jsonb_array_elements(ui.fn_resolve_dashboard_config((SELECT dashboard_codice FROM _d),
                                                             (SELECT auth_user_id FROM _u WHERE chi = p_chi),
                                                             NULL) -> 'widget') e
    JOIN _w w ON w.codice = e ->> 'codice'
$f$;

-- ============================================================
-- 1-2) Chi vede il widget
-- ============================================================
SELECT is(pg_temp.visibili('con'), 'area,azione1,libero',
    '1) ⭐ con l''azione concessa: il widget dell''azione, quello della sola area e quello libero; non l''altra azione');

SELECT is(pg_temp.visibili('senza'), 'libero',
    '2) ⭐ senza area ne'' azione: il solo widget libero');

-- ============================================================
-- 3-4) Lo snapshot del preset di base
-- ============================================================
INSERT INTO ui.dashboard_preferenza_utente (auth_user_id, dashboard_id, preset_base_id,
                                            preset_base_contenuto_aggiornato_il, configurazione)
SELECT (SELECT auth_user_id FROM _u WHERE chi = 'con'), (SELECT dashboard_id FROM _d),
       (SELECT preset_id FROM _p WHERE codice = 'P_SIS'),
       '{"widget": "1999-01-01T00:00:00+00:00"}'::jsonb, '{"dimensione_max": 5}'::jsonb;

CREATE FUNCTION pg_temp.snapshot() RETURNS jsonb LANGUAGE sql AS $f$
  SELECT pu.preset_base_contenuto_aggiornato_il FROM ui.dashboard_preferenza_utente pu
   WHERE pu.auth_user_id = (SELECT auth_user_id FROM _u WHERE chi = 'con')
     AND pu.dashboard_id = (SELECT dashboard_id FROM _d)
$f$;

SELECT is(pg_temp.snapshot(),
    (SELECT dp.contenuto_aggiornato_il FROM ui.dashboard_preset dp
      WHERE dp.id = (SELECT preset_id FROM _p WHERE codice = 'P_SIS')),
    '3) ⭐ la preferenza nasce con uno snapshot passato da chi scrive: conta quello del preset');

UPDATE ui.dashboard_preferenza_utente
   SET preset_base_id = (SELECT preset_id FROM _p WHERE codice = 'P_BOZZA'),
       preset_base_contenuto_aggiornato_il = '{"widget": "1999-01-01T00:00:00+00:00"}'::jsonb
 WHERE auth_user_id = (SELECT auth_user_id FROM _u WHERE chi = 'con')
   AND dashboard_id = (SELECT dashboard_id FROM _d);

SELECT is(pg_temp.snapshot(),
    (SELECT dp.contenuto_aggiornato_il FROM ui.dashboard_preset dp
      WHERE dp.id = (SELECT preset_id FROM _p WHERE codice = 'P_BOZZA')),
    '4) ... e cambiare base e snapshot nella stessa UPDATE: quello della base nuova');

-- ============================================================
-- 5-6) La vista materializzata
-- ============================================================
CREATE MATERIALIZED VIEW ui._pgtap_casi_mv AS SELECT 1::integer AS campo_mv;

SELECT lives_ok(
    $$ INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
       VALUES ('_pgtap.dash_casi_mv', 'Lista test su vista materializzata', 'ui', '_pgtap_casi_mv', TRUE, 'pgtap') $$,
    '5) una lista si registra su una vista materializzata');

SELECT lives_ok(
    $$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default, user_insert)
       SELECT ld.id, 'campo_mv', 'campo_mv', 'campo_mv', 'numeric', 10, 'pgtap'
         FROM ui.lista_definizione ld WHERE ld.codice = '_pgtap.dash_casi_mv' $$,
    '6) ... e una sua colonna sul campo della vista passa');

SELECT * FROM finish();
ROLLBACK;
