-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su ui.dashboard_definizione, che a runtime NON scrive nessuno
--   (ne' una funzione DB ne' il backend): e' seed di migrazione, e il SELECT-only del ruolo
--   applicativo e' corretto. Stessa ragione del gemello test-fn-resolve-dashboard-config.sql.
-- pgTAP test per Zero ERP
--
-- Test: la cascata PER CHIAVE di ui.fn_resolve_dashboard_config e la data del
--   contenuto dei preset di dashboard.
--   Richiesta BE/FE «la preferenza di lista per chiave» §4 (simmetria con la
--   dashboard, 2026-11-01). ChangeSet: 20_code/ui/20261101-20, -21, -24, -25, -27.
--
-- ⭐ Il mondo si COSTRUISCE: una dashboard, due widget non gated nel suo pool,
--   un preset di sistema con un widget solo e dimensione 6, un utente. Nessun
--   dato esistente decide un'asserzione.
--
-- Elenco test (plan 11):
--   La cascata
--    1) preferenza di soli widget: dimensione dal preset, origine lo dice
--    2) ... e la dimensione standard e' quella del preset
--    3) preferenza di sola dimensione: i widget vengono dal preset
--    4) ... la dimensione e' quella della preferenza, lo standard resta il preset
--    5) senza preferenza, preset senza dimensione: 8, origine catalogo
--   La data del contenuto del preset
--    6) riscrivere la riga del preset uguale: contenuto_aggiornato_il non si sposta
--    7) cambiare dimensione_max: contenuto_aggiornato_il = now()
--    8) riscrivere i widget del preset uguali: contenuto_aggiornato_il non si sposta
--    9) cambiare un widget del preset: contenuto_aggiornato_il = now()
--   Il flag
--   10) il preset cambia davvero: flag acceso
--   I trigger
--   11) i due trigger delle dashboard ci sono, sulle due funzioni condivise
-- ------------------------------------------------------------
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli
--   (il COMMIT non arriva mai). Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo (veste OPERATORE). L'utente della dashboard non ha
-- identita' ne' profili: niente preset di ruolo, e i widget del test non sono
-- gated, quindi le mappe dei permessi (fail-closed) non tolgono niente.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _d AS
WITH ins AS (
  INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
  VALUES ('_pgtap.dash_cascata_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Dashboard test pgTAP cascata per chiave', TRUE, '_pgtap')
  RETURNING id, codice
)
SELECT id AS dashboard_id, codice AS dashboard_codice FROM ins;

CREATE TEMP TABLE _w AS
WITH ins AS (
  INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
  SELECT v.codice || '_' || substr(md5(clock_timestamp()::text), 1, 6), v.codice, 'kpi', TRUE, '_pgtap'
    FROM (VALUES ('w_uno'), ('w_due')) AS v(codice)
  RETURNING id, etichetta AS nome
)
SELECT id AS widget_id, nome FROM ins;

INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT d.dashboard_id, w.widget_id, CASE w.nome WHEN 'w_uno' THEN 10 ELSE 20 END
  FROM _d d, _w w;

-- Il preset di sistema: il solo w_uno, dimensione 6.
CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.dashboard_preset (dashboard_id, codice, descrizione, ambito, is_default,
                                   dimensione_max, attivo, user_insert)
  SELECT dashboard_id, 'SISTEMA_CASCATA', 'Preset sistema test cascata', 'sistema', TRUE, 6, TRUE, '_pgtap'
    FROM _d
  RETURNING id
)
SELECT id AS preset_id FROM ins;

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 10, TRUE FROM _p p, _w w WHERE w.nome = 'w_uno';

CREATE TEMP TABLE _u AS
WITH ins AS (
  INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                first_name, last_name, email, date_joined)
  VALUES ('_pgtap_dash_cascata_' || substr(md5(clock_timestamp()::text), 1, 6),
          '!', TRUE, FALSE, FALSE, '', '', '', now())
  RETURNING id
)
SELECT id AS auth_user_id FROM ins;

CREATE OR REPLACE FUNCTION pg_temp.preferenza(p_configurazione jsonb) RETURNS void
LANGUAGE sql AS $$
    INSERT INTO ui.dashboard_preferenza_utente (auth_user_id, dashboard_id, configurazione)
    VALUES ((SELECT auth_user_id FROM _u), (SELECT dashboard_id FROM _d), p_configurazione)
    ON CONFLICT (auth_user_id, dashboard_id) DO UPDATE SET configurazione = EXCLUDED.configurazione;
$$;

CREATE OR REPLACE FUNCTION pg_temp.risolta() RETURNS jsonb
LANGUAGE sql AS $$
    SELECT ui.fn_resolve_dashboard_config((SELECT dashboard_codice FROM _d), (SELECT auth_user_id FROM _u), NULL);
$$;

-- I nomi dei widget visibili, in ordine: dice da dove vengono i widget.
CREATE OR REPLACE FUNCTION pg_temp.visibili(p_config jsonb) RETURNS text
LANGUAGE sql AS $$
    SELECT string_agg(w.nome, ',' ORDER BY (e ->> 'ordine')::integer)
      FROM jsonb_array_elements(p_config -> 'widget') e
      JOIN ui.widget uw ON uw.codice = e ->> 'codice'
      JOIN _w w ON w.widget_id = uw.id
     WHERE (e ->> 'visibile')::boolean;
$$;

-- I widget di preferenza: il solo w_due visibile (il preset mostra w_uno).
CREATE TEMP TABLE _pref_widget AS
SELECT jsonb_build_array(
         jsonb_build_object('codice', (SELECT uw.codice FROM ui.widget uw JOIN _w w ON w.widget_id = uw.id WHERE w.nome = 'w_uno'),
                            'ordine', 1, 'visibile', false),
         jsonb_build_object('codice', (SELECT uw.codice FROM ui.widget uw JOIN _w w ON w.widget_id = uw.id WHERE w.nome = 'w_due'),
                            'ordine', 2, 'visibile', true)) AS widget;

-- ============================================================
-- 1-5 La cascata
-- ============================================================
SELECT pg_temp.preferenza(jsonb_build_object('widget', (SELECT widget FROM _pref_widget)));

SELECT is(
    (SELECT format('%s|%s|%s', r ->> 'dimensione_max', pg_temp.visibili(r), r -> 'origine')
       FROM (SELECT pg_temp.risolta() AS r) x),
    format('6|w_due|%s', '{"widget": "preferenza", "dimensione_max": "sistema"}'::jsonb),
    '1) preferenza di soli widget: la dimensione viene dal preset (6, non 8), e origine lo dice');

SELECT is((pg_temp.risolta() ->> 'dimensione_max_standard')::integer, 6,
    '2) ... e la dimensione standard e'' quella del preset');

SELECT pg_temp.preferenza('{"dimensione_max": 9}'::jsonb);

SELECT is(
    (SELECT format('%s|%s', pg_temp.visibili(r), r -> 'origine' ->> 'widget')
       FROM (SELECT pg_temp.risolta() AS r) x),
    'w_uno|sistema',
    '3) preferenza di sola dimensione: i widget vengono dal preset');

SELECT is(
    (SELECT format('%s|%s|%s', r ->> 'dimensione_max', r -> 'origine' ->> 'dimensione_max',
                   r ->> 'dimensione_max_standard')
       FROM (SELECT pg_temp.risolta() AS r) x),
    '9|preferenza|6',
    '4) ... la dimensione e'' quella della preferenza, lo standard resta il preset');

DELETE FROM ui.dashboard_preferenza_utente WHERE auth_user_id = (SELECT auth_user_id FROM _u);
UPDATE ui.dashboard_preset SET dimensione_max = NULL WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT format('%s|%s|%s', r ->> 'dimensione_max', r ->> 'dimensione_max_standard',
                   r -> 'origine' ->> 'dimensione_max')
       FROM (SELECT pg_temp.risolta() AS r) x),
    '8|8|catalogo',
    '5) senza preferenza, preset senza dimensione: il ripiego 8, e origine dice catalogo');

UPDATE ui.dashboard_preset SET dimensione_max = 6 WHERE id = (SELECT preset_id FROM _p);

-- ============================================================
-- 6-9 La data del contenuto del preset
-- ============================================================
UPDATE ui.dashboard_preset SET contenuto_aggiornato_il = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);

UPDATE ui.dashboard_preset SET dimensione_max = dimensione_max, descrizione = descrizione
 WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT contenuto_aggiornato_il FROM ui.dashboard_preset WHERE id = (SELECT preset_id FROM _p)),
    TIMESTAMPTZ '2026-01-01 10:00:00+00',
    '6) riscrivere la riga del preset uguale (come fa il seed): contenuto_aggiornato_il non si sposta');

UPDATE ui.dashboard_preset SET dimensione_max = 7 WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT contenuto_aggiornato_il FROM ui.dashboard_preset WHERE id = (SELECT preset_id FROM _p)),
    now(),
    '7) cambiare dimensione_max: contenuto_aggiornato_il = now()');

UPDATE ui.dashboard_preset SET contenuto_aggiornato_il = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);

UPDATE ui.dashboard_preset_widget SET ordine = ordine, visibile = visibile
 WHERE preset_id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT contenuto_aggiornato_il FROM ui.dashboard_preset WHERE id = (SELECT preset_id FROM _p)),
    TIMESTAMPTZ '2026-01-01 10:00:00+00',
    '8) riscrivere i widget del preset uguali: contenuto_aggiornato_il non si sposta');

UPDATE ui.dashboard_preset_widget SET ordine = 15 WHERE preset_id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT contenuto_aggiornato_il FROM ui.dashboard_preset WHERE id = (SELECT preset_id FROM _p)),
    now(),
    '9) cambiare un widget del preset: contenuto_aggiornato_il = now()');

-- ============================================================
-- 10 Il flag
-- ============================================================
UPDATE ui.dashboard_preset SET contenuto_aggiornato_il = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);

INSERT INTO ui.dashboard_preferenza_utente (auth_user_id, dashboard_id, preset_base_id,
                                            preset_base_contenuto_aggiornato_il, configurazione)
VALUES ((SELECT auth_user_id FROM _u), (SELECT dashboard_id FROM _d), (SELECT preset_id FROM _p),
        TIMESTAMPTZ '2026-01-01 10:00:00+00', jsonb_build_object('widget', (SELECT widget FROM _pref_widget)));

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 20, TRUE FROM _p p, _w w WHERE w.nome = 'w_due';

SELECT is((pg_temp.risolta() ->> 'preset_aggiornato')::boolean, TRUE,
    '10) il preset cambia davvero (un widget in piu''): preset_aggiornato acceso');

-- ============================================================
-- 11 I trigger
-- ============================================================
-- Per funzione e argomento, non per nome; schema e tabella dal catalogo
-- (regclass::text dipende dal search_path).
SELECT is(
    (SELECT string_agg(format('%s.%s:%s', n.nspname, c.relname, p.proname), ',' ORDER BY c.relname)
       FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
       JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND t.tgrelid IN ('ui.dashboard_preset'::regclass, 'ui.dashboard_preset_widget'::regclass)
        AND p.proname IN ('trgfn_preset_contenuto_aggiornato', 'trgfn_preset_riga_tocca_preset')),
    'ui.dashboard_preset:trgfn_preset_contenuto_aggiornato,ui.dashboard_preset_widget:trgfn_preset_riga_tocca_preset',
    '11) i due trigger delle dashboard ci sono, sulle due funzioni condivise');

SELECT * FROM finish();
ROLLBACK;
