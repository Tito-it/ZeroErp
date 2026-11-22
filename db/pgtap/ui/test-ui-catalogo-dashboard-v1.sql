-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture fabbrica il catalogo delle dashboard (definizione, widget, pool,
--   preset), che l'applicazione non scrive: lo scrive solo il migratore, dal CSV (U31, la porta di
--   90_end/20261120-60). La porta stessa si asserisce sui privilegi del ruolo applicativo
--   (has_table_privilege), e il rifiuto come applicazione lo prova ui/test-ui-catalogo-liste-v1.
-- pgTAP test per Zero ERP
--
-- Test: il CATALOGO DELLE DASHBOARD, giro 5.
--   Brief: brief-db-revisione-ui, giro 5 (U31, U33-U36, Q49, Q50; U28 per le
--   dashboard, spostato qui dal giro 4).
--   ChangeSet: 00_schema/ui/20261120-53, -55, -56; 20_code/ui/20261120-54,
--   -57, -58, -59; 90_end/20261120-60, -61, -62; il registro
--   80_data/sql/dbops/automazione_attivo_eccezioni.
--
-- ⭐ Il mondo si COSTRUISCE: due dashboard col loro pool, un widget, un preset
--   di sistema, un operatore umano per la preferenza. Area e azione del caso
--   U33 sono un'azione accesa del catalogo dei permessi e un'area accesa
--   diversa dalla sua: senza, skip() dichiarato.
-- ⚠️ I casi 4-5 (il lucchetto) chiedono il runner dei lucchetti (20261120-62) e
--   il 16 il ritiro dei trigger ATTIVO (20261120-61).
--
-- Elenco test (plan 21):
--   U31: la porta
--    1) all'app SELECT soltanto sulle cinque tabelle di catalogo
--    2) ... e la preferenza resta scrivibile
--   U35: l'azienda del preset
--    3) dashboard_preset.emittente_fiscale_id ha il tipo di emittenti_fiscali.id
--    4) il lucchetto del posto e' montato, anche sull'azienda
--    5) ... e il posto non si riscrive: E_UI_PRESET_POSTO_IMMUTABILE
--   U33: area e azione del widget
--    6) ⭐ un'area diversa da quella dell'azione e' rifiutata (23503)
--    7) l'area nulla con l'azione passa
--    8) l'area dell'azione passa
--    9) ⭐ l'azione citata con l'area non cambia area (23503)
--   U34: la dashboard per codice
--   10) il building block da' la riga della dashboard accesa
--   11) un codice assente: E_UI_DASHBOARD_NON_TROVATA
--   12) il codice NULL: E_UI_DASHBOARD_NON_TROVATA
--   U36: data_update delle preferenze
--   13) all'INSERT la scrive il DB, anche se chi scrive ne passa un'altra
--   14) ... e all'UPDATE
--   15) data_update e' NOT NULL sulle due preferenze
--   Q49: la dashboard spenta sospende i preset
--   16) ⭐ una dashboard con un preset acceso si spegne
--   17) ... e per codice non risponde piu'
--   18) ... nemmeno al resolver
--   19) ... riaccesa, il preset e' acceso ed e' di nuovo la base
--   U28: i testi vuoti (dal giro 4)
--   20) un'etichetta di widget vuota e' rifiutata dal CHECK
--   21) una descrizione di dashboard vuota e' rifiutata dal CHECK
--   22-26) gli altri CHECK dei testi, uno per caso, riconosciuti per nome
--       (aggiunti dal /verifica-db del 2026-11-22): codice, chiave i18n
--       dell'etichetta e chiave del contatore del widget; codice e note della
--       dashboard
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- ============================================================
-- Fixture: due dashboard, un widget nel pool, un preset di sistema
-- ============================================================
CREATE TEMP TABLE _d AS
WITH ins AS (
  INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
  SELECT '_pgtap.dash_cat_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Dashboard test pgTAP catalogo ' || v.n, TRUE, '_pgtap'
    FROM (VALUES (1), (2)) AS v(n)
  RETURNING id, codice
)
SELECT id AS dashboard_id, codice AS dashboard_codice, row_number() OVER (ORDER BY id) AS n FROM ins;

CREATE TEMP TABLE _w AS
WITH ins AS (
  INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
  VALUES ('_pgtap_w_cat_' || substr(md5(clock_timestamp()::text), 1, 6), 'Widget test catalogo', 'kpi', TRUE, '_pgtap')
  RETURNING id
)
SELECT id AS widget_id FROM ins;

INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT d.dashboard_id, w.widget_id, 10 FROM _d d CROSS JOIN _w w;

CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.dashboard_preset (dashboard_id, codice, descrizione, ambito, attivo, user_insert)
  SELECT dashboard_id, 'dp_cat_sistema', 'Preset test catalogo', 'sistema', TRUE, '_pgtap' FROM _d WHERE n = 1
  RETURNING id
)
SELECT id AS preset_id FROM ins;

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 10, TRUE FROM _p p CROSS JOIN _w w;

-- L'azione e l'area del caso U33: un'azione accesa e un'area accesa diversa
--   dalla sua.
CREATE TEMP TABLE _az AS
SELECT ap.id AS azione_id, ap.area_id AS area_azione_id,
       (SELECT af.id FROM config.aree_funzionali af
         WHERE af.attivo AND af.id <> ap.area_id ORDER BY af.id LIMIT 1) AS altra_area_id
  FROM config.azioni_processo ap
 WHERE ap.attivo
   AND EXISTS (SELECT 1 FROM config.aree_funzionali af WHERE af.id = ap.area_id AND af.attivo)
 ORDER BY ap.id
 LIMIT 1;

-- ============================================================
-- 1-2) U31: la porta
-- ============================================================
SELECT is(
    (SELECT array_agg(format('%s|%s|%s', t.nome,
                             has_table_privilege('zeroerp_app', t.nome, 'SELECT')::text,
                             has_table_privilege('zeroerp_app', t.nome, 'INSERT, UPDATE, DELETE')::text)
                      ORDER BY t.nome)
       FROM (VALUES ('ui.dashboard_definizione'), ('ui.widget'), ('ui.dashboard_widget'),
                    ('ui.dashboard_preset'), ('ui.dashboard_preset_widget')) AS t(nome)),
    ARRAY['ui.dashboard_definizione|true|false', 'ui.dashboard_preset|true|false',
          'ui.dashboard_preset_widget|true|false', 'ui.dashboard_widget|true|false',
          'ui.widget|true|false'],
    '1) all''app SELECT soltanto sulle cinque tabelle di catalogo delle dashboard');

SELECT is(
    format('%s|%s|%s',
           has_table_privilege('zeroerp_app', 'ui.dashboard_preferenza_utente', 'INSERT')::text,
           has_table_privilege('zeroerp_app', 'ui.dashboard_preferenza_utente', 'UPDATE')::text,
           has_table_privilege('zeroerp_app', 'ui.dashboard_preferenza_utente', 'DELETE')::text),
    'true|true|true',
    '2) ... e la preferenza resta scrivibile');

-- ============================================================
-- 3-5) U35: l'azienda del preset
-- ============================================================
SELECT is(
    (SELECT atttypid::regtype::text FROM pg_catalog.pg_attribute
      WHERE attrelid = 'ui.dashboard_preset'::regclass AND attname = 'emittente_fiscale_id'),
    (SELECT atttypid::regtype::text FROM pg_catalog.pg_attribute
      WHERE attrelid = 'anagrafiche.emittenti_fiscali'::regclass AND attname = 'id'),
    '3) dashboard_preset.emittente_fiscale_id ha il tipo di emittenti_fiscali.id');

-- Per funzione e argomenti, non per nome (linee-guida-trigger, «Il nome del trigger»).
SELECT ok(
    EXISTS (SELECT 1 FROM pg_catalog.pg_trigger tg
             WHERE tg.tgrelid = 'ui.dashboard_preset'::regclass
               AND tg.tgfoid = 'script.trgfn_lock_columns'::regproc
               AND NOT tg.tgisinternal
               AND position('emittente_fiscale_id' IN encode(tg.tgargs, 'escape')) > 0),
    '4) il lucchetto del posto e'' montato, anche sull''azienda');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ UPDATE ui.dashboard_preset SET dashboard_id = %s WHERE id = %s $$,
        (SELECT dashboard_id FROM _d WHERE n = 2), (SELECT preset_id FROM _p))),
    'E_UI_PRESET_POSTO_IMMUTABILE',
    '5) ... e il posto non si riscrive: E_UI_PRESET_POSTO_IMMUTABILE');

-- ============================================================
-- 6-9) U33: area e azione del widget
-- ============================================================
-- Un caso per istruzione: ognuno parte dallo stato lasciato dal precedente.
SELECT CASE WHEN (SELECT altra_area_id FROM _az) IS NULL
  THEN skip('nessuna azione accesa con un''altra area accesa nel catalogo dei permessi', 1)
  ELSE throws_ok(
        format($$ UPDATE ui.widget SET azione_id = %s, area_id = %s WHERE id = %s $$,
               (SELECT azione_id FROM _az), (SELECT altra_area_id FROM _az), (SELECT widget_id FROM _w)),
        '23503', NULL,
        '6) un''area diversa da quella dell''azione e'' rifiutata (fk_ui_widget_azione_della_sua_area)')
  END;

SELECT CASE WHEN (SELECT altra_area_id FROM _az) IS NULL
  THEN skip('nessuna azione accesa con un''altra area accesa nel catalogo dei permessi', 1)
  ELSE lives_ok(
        format($$ UPDATE ui.widget SET azione_id = %s, area_id = NULL WHERE id = %s $$,
               (SELECT azione_id FROM _az), (SELECT widget_id FROM _w)),
        '7) l''area nulla con l''azione passa')
  END;

SELECT CASE WHEN (SELECT altra_area_id FROM _az) IS NULL
  THEN skip('nessuna azione accesa con un''altra area accesa nel catalogo dei permessi', 1)
  ELSE lives_ok(
        format($$ UPDATE ui.widget SET azione_id = %s, area_id = %s WHERE id = %s $$,
               (SELECT azione_id FROM _az), (SELECT area_azione_id FROM _az), (SELECT widget_id FROM _w)),
        '8) l''area dell''azione passa')
  END;

SELECT CASE WHEN (SELECT altra_area_id FROM _az) IS NULL
  THEN skip('nessuna azione accesa con un''altra area accesa nel catalogo dei permessi', 1)
  ELSE throws_ok(
        format($$ UPDATE config.azioni_processo SET area_id = %s WHERE id = %s $$,
               (SELECT altra_area_id FROM _az), (SELECT azione_id FROM _az)),
        '23503', NULL,
        '9) l''azione citata con l''area non cambia area (fk_ui_widget_azione_della_sua_area)')
  END;

-- Il widget torna senza area ne' azione: i casi dopo non dipendono dai permessi.
UPDATE ui.widget SET azione_id = NULL, area_id = NULL WHERE id = (SELECT widget_id FROM _w);

-- ============================================================
-- 10-12) U34: la dashboard per codice
-- ============================================================
SELECT is(
    (SELECT (ui.fn_dashboard_da_codice((SELECT dashboard_codice FROM _d WHERE n = 1))).id),
    (SELECT dashboard_id FROM _d WHERE n = 1),
    '10) il building block da'' la riga della dashboard accesa');

SELECT is(
    dbops.fn_pgtap_codice_errore($$ SELECT ui.fn_dashboard_da_codice('_pgtap.dashboard_che_non_esiste') $$),
    'E_UI_DASHBOARD_NON_TROVATA',
    '11) un codice assente: E_UI_DASHBOARD_NON_TROVATA');

SELECT is(
    dbops.fn_pgtap_codice_errore($$ SELECT ui.fn_dashboard_da_codice(NULL) $$),
    'E_UI_DASHBOARD_NON_TROVATA',
    '12) il codice NULL: E_UI_DASHBOARD_NON_TROVATA');

-- ============================================================
-- 13-15) U36: data_update delle preferenze
-- ============================================================
CREATE TEMP TABLE _ctx AS
SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-catalogo-dashboard', false);

INSERT INTO ui.dashboard_preferenza_utente (auth_user_id, dashboard_id, configurazione, data_update)
SELECT c.auth_user_id, d.dashboard_id, '{}'::jsonb, '2000-01-01 00:00:00+00'
  FROM _ctx c CROSS JOIN _d d WHERE d.n = 1;

SELECT is(
    (SELECT pu.data_update FROM ui.dashboard_preferenza_utente pu
      WHERE pu.auth_user_id = (SELECT auth_user_id FROM _ctx)
        AND pu.dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 1)),
    now(),
    '13) all''INSERT data_update la scrive il DB, anche se chi scrive ne passa un''altra');

UPDATE ui.dashboard_preferenza_utente SET data_update = '2000-01-01 00:00:00+00'
 WHERE auth_user_id = (SELECT auth_user_id FROM _ctx)
   AND dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 1);

SELECT is(
    (SELECT pu.data_update FROM ui.dashboard_preferenza_utente pu
      WHERE pu.auth_user_id = (SELECT auth_user_id FROM _ctx)
        AND pu.dashboard_id = (SELECT dashboard_id FROM _d WHERE n = 1)),
    now(),
    '14) ... e all''UPDATE');

SELECT is(
    (SELECT array_agg(attrelid::regclass::text || '|' || attnotnull::text ORDER BY attrelid::regclass::text)
       FROM pg_catalog.pg_attribute
      WHERE attrelid IN ('ui.lista_preferenza_utente'::regclass, 'ui.dashboard_preferenza_utente'::regclass)
        AND attname = 'data_update' AND NOT attisdropped),
    ARRAY['ui.dashboard_preferenza_utente|true', 'ui.lista_preferenza_utente|true'],
    '15) data_update e'' NOT NULL sulle due preferenze');

-- ============================================================
-- 16-19) Q49: la dashboard spenta sospende i preset
-- ============================================================
SELECT lives_ok(
    format($$ UPDATE ui.dashboard_definizione SET attivo = false WHERE id = %s $$,
           (SELECT dashboard_id FROM _d WHERE n = 1)),
    '16) una dashboard con un preset acceso si spegne');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ SELECT ui.fn_dashboard_da_codice(%L) $$, (SELECT dashboard_codice FROM _d WHERE n = 1))),
    'E_UI_DASHBOARD_NON_TROVATA',
    '17) ... e per codice non risponde piu''');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ SELECT ui.fn_resolve_dashboard_config(%L, %s, NULL) $$,
        (SELECT dashboard_codice FROM _d WHERE n = 1), (SELECT auth_user_id FROM _ctx))),
    'E_UI_DASHBOARD_NON_TROVATA',
    '18) ... nemmeno al resolver');

UPDATE ui.dashboard_definizione SET attivo = true WHERE id = (SELECT dashboard_id FROM _d WHERE n = 1);

SELECT is(
    (SELECT format('%s|%s',
                   (SELECT dp.attivo FROM ui.dashboard_preset dp WHERE dp.id = p.preset_id)::text,
                   (SELECT b.preset_id = p.preset_id
                      FROM ui.fn_preset_di_base('dashboard', (SELECT dashboard_id FROM _d WHERE n = 1),
                                                (SELECT auth_user_id FROM _ctx), NULL, NULL) b)::text)
       FROM _p p),
    'true|true',
    '19) ... riaccesa, il preset e'' acceso ed e'' di nuovo la base');

-- ============================================================
-- 20-21) U28: i testi vuoti
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
       VALUES ('_pgtap_widget_vuoto', '', 'kpi', TRUE, '_pgtap') $$,
    '23514', NULL,
    '20) un''etichetta di widget vuota e'' rifiutata (chk_widget_etichetta_non_vuota)');

SELECT throws_ok(
    $$ INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
       VALUES ('_pgtap.dash_vuota', ' ', TRUE, '_pgtap') $$,
    '23514', NULL,
    '21) una descrizione di dashboard vuota e'' rifiutata (chk_dashboard_definizione_descrizione_non_vuota)');

SELECT is(dbops.fn_pgtap_codice_errore(
        $$ INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
           VALUES (' ', 'Widget test pgTAP', 'kpi', TRUE, '_pgtap') $$),
    'chk_widget_codice_non_vuoto',
    '22) un codice di widget vuoto e'' rifiutato dal CHECK');
SELECT is(dbops.fn_pgtap_codice_errore(
        $$ INSERT INTO ui.widget (codice, etichetta, etichetta_i18n_key, tipo_widget, attivo, user_insert)
           VALUES ('_pgtap_widget_i18n_vuota', 'Widget test pgTAP', ' ', 'kpi', TRUE, '_pgtap') $$),
    'chk_widget_etichetta_i18n_key_non_vuota',
    '23) una chiave i18n dell''etichetta vuota e'' rifiutata dal CHECK (NULL resta ammesso)');
SELECT is(dbops.fn_pgtap_codice_errore(
        $$ INSERT INTO ui.widget (codice, etichetta, contatore_key, tipo_widget, attivo, user_insert)
           VALUES ('_pgtap_widget_contatore_vuoto', 'Widget test pgTAP', ' ', 'kpi', TRUE, '_pgtap') $$),
    'chk_widget_contatore_key_non_vuota',
    '24) una chiave del contatore vuota e'' rifiutata dal CHECK (NULL resta ammesso)');
SELECT is(dbops.fn_pgtap_codice_errore(
        $$ INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
           VALUES (' ', 'Dashboard test pgTAP', TRUE, '_pgtap') $$),
    'chk_dashboard_definizione_codice_non_vuoto',
    '25) un codice di dashboard vuoto e'' rifiutato dal CHECK');
SELECT is(dbops.fn_pgtap_codice_errore(
        $$ INSERT INTO ui.dashboard_definizione (codice, descrizione, note, attivo, user_insert)
           VALUES ('_pgtap.dash_note_vuote', 'Dashboard test pgTAP', ' ', TRUE, '_pgtap') $$),
    'chk_dashboard_definizione_note_non_vuote',
    '26) una nota di dashboard vuota e'' rifiutata dal CHECK (NULL resta ammesso)');

SELECT * FROM finish();
ROLLBACK;
