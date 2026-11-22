-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: i casi 15-20 fabbricano le righe «scritte prima del
--   guard» spegnendo il trigger di forma delle due preferenze (ALTER TABLE …
--   DISABLE TRIGGER), che solo il proprietario puo' fare. Le tabelle di ui non
--   hanno RLS: il ruolo non cambia nessuna risposta. Tutto in transazione annullata.
-- pgTAP test per Zero ERP
--
-- Test: la FORMA della configurazione delle preferenze e dell'ordinamento dei
--   preset, e i resolver che non cadono sulle righe scritte prima del guard.
--   Brief: brief-db-revisione-ui, giro 2 (U10-U13, U19, U21; Q6, Q7, Q12,
--   Q34, Q42; il ritiro di Q38/Q39 §6). ChangeSet: 20_code/ui/20261120-21 →
--   -24, 00_schema/ui/20261120-25, 20_code/ui/20261120-26 → -31.
--
-- ⭐ Il mondo si COSTRUISCE: una lista con cinque colonne (una spenta, una non
--   ordinabile, una sensibile senza grant), una seconda lista, una dashboard col
--   suo pool, un operatore umano senza aree. Le righe «scritte prima del guard»
--   si fabbricano spegnendo il trigger di forma, per nome (e' scritto a mano, non
--   generato), e riaccendendolo subito dopo.
--
-- Elenco test (plan 31):
--   Il guard delle preferenze di lista
--    1) una chiave fuori famiglia (filtri) e' rifiutata
--    2) ... e cosi' ordinamento (Q39 §6: la preferenza non lo porta piu')
--    3) un campo della voce a null e' rifiutato
--    4) un codice di un'altra lista e' rifiutato
--    5) un codice ripetuto e' rifiutato
--    6) ordine scritto come stringa e' rifiutato (U19)
--    7) visibile non booleano e' rifiutato
--    8) una radice che non e' un oggetto e' rifiutata
--    9) {} passa
--   10) Q42 (a): la voce di una colonna spenta passa
--   11) la misura fuori catalogo la rifiuta il guard della misura, col suo codice
--   Il guard delle preferenze di dashboard
--   12) un codice fuori dal pool e' rifiutato
--   13) dimensione_max 101 e' rifiutata (U21)
--   14) una voce con una chiave in piu' e' rifiutata
--   Le righe scritte prima del guard
--   15) un UPDATE che non cambia la configurazione passa (il banner)
--   16) ... e un UPDATE che la cambia la giudica
--   17) U12: il resolver delle liste non cade, un codice vale una volta, l'ordine
--       non intero prende il default del catalogo
--   18) U11: una voce senza codice non spegne le colonne nuove
--   19) U12: un campo che manca esce col default, non null
--   20) U12: il resolver delle dashboard non cade, un codice vale una volta
--   21) ⭐ U10: una card nuova del pool di un'area non concessa non conta
--   22) ... e una card nuova senza area conta
--   Il guard dell'ordinamento del preset
--   23) un campo sorgente al posto del codice e' rifiutato (Q34)
--   24) una direzione fuori dominio e' rifiutata
--   25) una colonna ripetuta e' rifiutata
--   26) riscrivere l'ordinamento uguale passa
--   L'ordinamento risolto (ui.fn_ordinamento_lista)
--   27) ⭐ U13: via le colonne spenta, non ordinabile e sensibile; il campo sorgente esce
--   28) una lista senza preset: []
--   La struttura
--   29) la data del contenuto di un preset di lista ha le chiavi colonne e pagina_dimensione
--   30) ui.lista_preset non ha filtri_default
--   31) il guard di forma e' montato sulle due preferenze, quello della sola misura no
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(31);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  VALUES ('_pgtap.forma_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP forma', 'pgtap', NULL, TRUE, '_pgtap'),
         ('_pgtap.forma_altra_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP forma, l''altra', 'pgtap', NULL, TRUE, '_pgtap')
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice,
       row_number() OVER (ORDER BY id) AS n FROM ins;

-- c_ok ordinabile; c_spenta spenta; c_noord non ordinabile; c_sens sensibile
-- senza grant; c_nuova nasce dopo, per il merge. Nell'altra lista, c_altrove.
CREATE TEMP TABLE _c AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_colonna, tipo_dato,
                                ordine_default, larghezza_default, ordinabile, sensibile, attivo, user_insert)
  SELECT CASE WHEN v.codice = 'c_altrove' THEN (SELECT lista_id FROM _l WHERE n = 2)
              ELSE (SELECT lista_id FROM _l WHERE n = 1) END,
         v.codice, v.codice, 'campo_' || v.codice, 'informazione', 'string',
         v.ordine, 120, v.ordinabile, v.sensibile, v.attivo, '_pgtap'
    FROM (VALUES ('c_ok',      10, true,  false, true),
                 ('c_spenta',  20, true,  false, false),
                 ('c_noord',   30, false, false, true),
                 ('c_sens',    40, true,  true,  true),
                 ('c_altrove', 10, true,  false, true)) AS v(codice, ordine, ordinabile, sensibile, attivo)
  RETURNING id, lista_id, codice
)
SELECT id AS colonna_id, lista_id, codice FROM ins;

-- Il preset di sistema della prima lista: c_ok in composizione, l'ordinamento
-- per codice su tutte le colonne (Q42 (a): anche la spenta).
CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, ordinamento_default, attivo, user_insert)
  SELECT lista_id, 'SISTEMA_FORMA', 'Preset sistema test forma', 'sistema',
         '[{"col": "c_spenta", "dir": "asc"}, {"col": "c_noord", "dir": "asc"},
           {"col": "c_sens", "dir": "desc"}, {"col": "c_ok", "dir": "desc"}]'::jsonb,
         TRUE, '_pgtap'
    FROM _l WHERE n = 1
  RETURNING id
)
SELECT id AS preset_id FROM ins;

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT (SELECT preset_id FROM _p), colonna_id, 1, TRUE, FALSE FROM _c WHERE codice = 'c_ok';

CREATE TEMP TABLE _u AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-forma-configurazione', false);

-- La dashboard: w_uno nel preset; w_area (di un'area che l'operatore non ha) e
-- w_libero (senza area) nel pool, nuovi per chi segue il preset.
CREATE TEMP TABLE _d AS
WITH ins AS (
  INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
  VALUES ('_pgtap.dash_forma_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Dashboard test pgTAP forma', TRUE, '_pgtap')
  RETURNING id, codice
)
SELECT id AS dashboard_id, codice AS dashboard_codice FROM ins;

CREATE TEMP TABLE _w AS
WITH ins AS (
  INSERT INTO ui.widget (codice, etichetta, tipo_widget, area_id, attivo, user_insert)
  SELECT v.nome || '_' || substr(md5(clock_timestamp()::text), 1, 6), v.nome, 'kpi',
         CASE WHEN v.nome = 'w_area' THEN (SELECT min(id) FROM config.aree_funzionali) END,
         TRUE, '_pgtap'
    FROM (VALUES ('w_uno'), ('w_area'), ('w_libero'), ('w_fuori')) AS v(nome)
  RETURNING id, codice, etichetta AS nome
)
SELECT id AS widget_id, codice, nome FROM ins;

-- w_fuori non e' nel pool; w_libero entra nel pool solo al caso 22.
INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT (SELECT dashboard_id FROM _d), w.widget_id, CASE w.nome WHEN 'w_uno' THEN 10 ELSE 20 END
  FROM _w w WHERE w.nome IN ('w_uno', 'w_area');

CREATE TEMP TABLE _dp AS
WITH ins AS (
  INSERT INTO ui.dashboard_preset (dashboard_id, codice, descrizione, ambito, dimensione_max, attivo, user_insert)
  SELECT dashboard_id, 'SISTEMA_FORMA', 'Preset sistema test forma', 'sistema', 6, TRUE, '_pgtap' FROM _d
  RETURNING id
)
SELECT id AS preset_id FROM ins;
INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT (SELECT preset_id FROM _dp), widget_id, 10, TRUE FROM _w WHERE nome = 'w_uno';

-- La preferenza di lista e quella di dashboard, scritte come le scrive l'app.
CREATE FUNCTION pg_temp.pref_lista(p_configurazione jsonb) RETURNS void LANGUAGE sql AS $f$
    INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, configurazione)
    VALUES ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l WHERE n = 1), p_configurazione)
    ON CONFLICT (auth_user_id, lista_id) DO UPDATE SET configurazione = EXCLUDED.configurazione;
$f$;
CREATE FUNCTION pg_temp.pref_dash(p_configurazione jsonb) RETURNS void LANGUAGE sql AS $f$
    INSERT INTO ui.dashboard_preferenza_utente (auth_user_id, dashboard_id, configurazione)
    VALUES ((SELECT auth_user_id FROM _u), (SELECT dashboard_id FROM _d), p_configurazione)
    ON CONFLICT (auth_user_id, dashboard_id) DO UPDATE SET configurazione = EXCLUDED.configurazione;
$f$;
CREATE FUNCTION pg_temp.lista() RETURNS jsonb LANGUAGE sql AS $f$
    SELECT ui.fn_resolve_lista_config((SELECT lista_codice FROM _l WHERE n = 1), (SELECT auth_user_id FROM _u), NULL);
$f$;
CREATE FUNCTION pg_temp.dash() RETURNS jsonb LANGUAGE sql AS $f$
    SELECT ui.fn_resolve_dashboard_config((SELECT dashboard_codice FROM _d), (SELECT auth_user_id FROM _u), NULL);
$f$;
-- Il codice del widget dal suo nome di fixture.
CREATE FUNCTION pg_temp.w(p_nome text) RETURNS text LANGUAGE sql AS $f$
    SELECT codice FROM _w WHERE nome = p_nome;
$f$;

-- ============================================================
-- 1-11 Il guard delle preferenze di lista
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore($$SELECT pg_temp.pref_lista('{"filtri": {}}')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '1) una chiave fuori famiglia (filtri) e'' rifiutata');
SELECT is(dbops.fn_pgtap_codice_errore($$SELECT pg_temp.pref_lista('{"ordinamento": []}')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '2) ... e cosi'' ordinamento');
SELECT is(dbops.fn_pgtap_codice_errore(
              $$SELECT pg_temp.pref_lista('{"colonne": [{"codice": "c_ok", "larghezza": null}]}')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '3) un campo della voce a null e'' rifiutato');
SELECT is(dbops.fn_pgtap_codice_errore(
              $$SELECT pg_temp.pref_lista('{"colonne": [{"codice": "c_altrove"}]}')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '4) un codice di un''altra lista e'' rifiutato');
SELECT is(dbops.fn_pgtap_codice_errore(
              $$SELECT pg_temp.pref_lista('{"colonne": [{"codice": "c_ok"}, {"codice": "c_ok"}]}')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '5) un codice ripetuto e'' rifiutato');
SELECT is(dbops.fn_pgtap_codice_errore(
              $$SELECT pg_temp.pref_lista('{"colonne": [{"codice": "c_ok", "ordine": "3"}]}')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '6) ordine scritto come stringa e'' rifiutato');
SELECT is(dbops.fn_pgtap_codice_errore(
              $$SELECT pg_temp.pref_lista('{"colonne": [{"codice": "c_ok", "visibile": "si"}]}')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '7) visibile non booleano e'' rifiutato');
SELECT is(dbops.fn_pgtap_codice_errore($$SELECT pg_temp.pref_lista('[]')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '8) una radice che non e'' un oggetto e'' rifiutata');
SELECT lives_ok($$SELECT pg_temp.pref_lista('{}')$$, '9) {} passa');
SELECT lives_ok($$SELECT pg_temp.pref_lista('{"colonne": [{"codice": "c_spenta", "ordine": 2}, {"codice": "c_ok"}]}')$$,
                '10) Q42 (a): la voce di una colonna spenta passa');
SELECT is(dbops.fn_pgtap_codice_errore($$SELECT pg_temp.pref_lista('{"pagina_dimensione": 7}')$$),
          'E_UI_MISURA_PAGINA_NON_AMMESSA', '11) la misura fuori catalogo la rifiuta il guard della misura');

-- ============================================================
-- 12-14 Il guard delle preferenze di dashboard
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(
              format($$SELECT pg_temp.pref_dash('{"widget": [{"codice": "%s"}]}')$$, pg_temp.w('w_fuori'))),
          'E_UI_CONFIGURAZIONE_FORMA', '12) un codice fuori dal pool e'' rifiutato');
SELECT is(dbops.fn_pgtap_codice_errore($$SELECT pg_temp.pref_dash('{"dimensione_max": 101}')$$),
          'E_UI_CONFIGURAZIONE_FORMA', '13) dimensione_max 101 e'' rifiutata');
SELECT is(dbops.fn_pgtap_codice_errore(
              format($$SELECT pg_temp.pref_dash('{"widget": [{"codice": "%s", "fissata": true}]}')$$, pg_temp.w('w_uno'))),
          'E_UI_CONFIGURAZIONE_FORMA', '14) una voce con una chiave in piu'' e'' rifiutata');

-- ============================================================
-- 15-22 Le righe scritte prima del guard
-- ============================================================
ALTER TABLE ui.lista_preferenza_utente DISABLE TRIGGER trg_ui_lista_preferenza_utente_a10_guard_forma_ins_upd;
SELECT pg_temp.pref_lista('{"colonne": [{"codice": "c_ok", "ordine": "x"}, {"ordine": 1},
                                        {"codice": "c_ok", "ordine": 9}, {"codice": "c_sens"}]}');
ALTER TABLE ui.lista_preferenza_utente ENABLE TRIGGER trg_ui_lista_preferenza_utente_a10_guard_forma_ins_upd;

SELECT lives_ok($$UPDATE ui.lista_preferenza_utente SET preset_base_id = (SELECT preset_id FROM _p)
                   WHERE auth_user_id = (SELECT auth_user_id FROM _u)$$,
                '15) un UPDATE che non cambia la configurazione passa');
SELECT is(dbops.fn_pgtap_codice_errore(
              $$UPDATE ui.lista_preferenza_utente SET configurazione = configurazione || '{"pagina_dimensione": 25}'
                 WHERE auth_user_id = (SELECT auth_user_id FROM _u)$$),
          'E_UI_CONFIGURAZIONE_FORMA', '16) ... e un UPDATE che la cambia la giudica');

-- c_ok una volta (la prima voce), ordine dal catalogo (10); c_sens BLOCCATO esce.
SELECT is(
    (SELECT string_agg(format('%s:%s', e ->> 'codice', e ->> 'ordine'), ',' ORDER BY e ->> 'codice')
       FROM jsonb_array_elements(pg_temp.lista() -> 'colonne') e WHERE (e ->> 'visibile')::boolean),
    'c_ok:10',
    '17) U12: il resolver non cade, c_ok vale una volta, l''ordine non intero prende il default del catalogo');

INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default, user_insert)
SELECT lista_id, 'c_nuova', 'c_nuova', 'campo_c_nuova', 'string', 50, '_pgtap' FROM _l WHERE n = 1;

-- Nuove per questa preferenza: c_noord (accesa, non nominata) e c_nuova.
SELECT is((pg_temp.lista() ->> 'colonne_nuove')::integer, 2,
          '18) U11: una voce senza codice non spegne le colonne nuove');
SELECT is(
    (SELECT format('%s|%s', e -> 'visibile', e -> 'larghezza')
       FROM jsonb_array_elements(pg_temp.lista() -> 'colonne') e WHERE e ->> 'codice' = 'c_ok'),
    'true|120',
    '19) U12: visibile e larghezza che mancano escono col default, non null');

ALTER TABLE ui.dashboard_preferenza_utente DISABLE TRIGGER trg_ui_dashboard_preferenza_utente_a10_guard_forma_ins_upd;
SELECT pg_temp.pref_dash(jsonb_build_object('widget', jsonb_build_array(
    jsonb_build_object('codice', pg_temp.w('w_uno'), 'ordine', 'x'),
    jsonb_build_object('codice', pg_temp.w('w_uno'), 'ordine', 3))));
ALTER TABLE ui.dashboard_preferenza_utente ENABLE TRIGGER trg_ui_dashboard_preferenza_utente_a10_guard_forma_ins_upd;

SELECT is(
    (SELECT string_agg(format('%s:%s:%s', e ->> 'codice', e ->> 'ordine', e ->> 'visibile'), ',')
       FROM jsonb_array_elements(pg_temp.dash() -> 'widget') e WHERE e ->> 'codice' = pg_temp.w('w_uno')),
    format('%s:10:true', pg_temp.w('w_uno')),
    '20) U12: il resolver delle dashboard non cade, w_uno vale una volta, ordine e visibile dal pool');

DELETE FROM ui.dashboard_preferenza_utente WHERE auth_user_id = (SELECT auth_user_id FROM _u);
SELECT is((pg_temp.dash() ->> 'widget_nuovi')::integer, 0,
          '21) U10: una card nuova del pool di un''area non concessa non conta');

INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT (SELECT dashboard_id FROM _d), widget_id, 30 FROM _w WHERE nome = 'w_libero';
SELECT is((pg_temp.dash() ->> 'widget_nuovi')::integer, 1,
          '22) ... e una card nuova senza area conta');

-- ============================================================
-- 23-26 Il guard dell'ordinamento del preset
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(
              $$UPDATE ui.lista_preset SET ordinamento_default = '[{"col": "campo_c_ok", "dir": "asc"}]'
                 WHERE id = (SELECT preset_id FROM _p)$$),
          'E_UI_CONFIGURAZIONE_FORMA', '23) un campo sorgente al posto del codice e'' rifiutato');
SELECT is(dbops.fn_pgtap_codice_errore(
              $$UPDATE ui.lista_preset SET ordinamento_default = '[{"col": "c_ok", "dir": "su"}]'
                 WHERE id = (SELECT preset_id FROM _p)$$),
          'E_UI_CONFIGURAZIONE_FORMA', '24) una direzione fuori dominio e'' rifiutata');
SELECT is(dbops.fn_pgtap_codice_errore(
              $$UPDATE ui.lista_preset SET ordinamento_default = '[{"col": "c_ok", "dir": "asc"}, {"col": "c_ok", "dir": "desc"}]'
                 WHERE id = (SELECT preset_id FROM _p)$$),
          'E_UI_CONFIGURAZIONE_FORMA', '25) una colonna ripetuta e'' rifiutata');
SELECT lives_ok($$UPDATE ui.lista_preset SET ordinamento_default = ordinamento_default
                   WHERE id = (SELECT preset_id FROM _p)$$,
                '26) riscrivere l''ordinamento uguale passa');

-- ============================================================
-- 27-28 L'ordinamento risolto
-- ============================================================
SELECT is(
    ui.fn_ordinamento_lista((SELECT lista_codice FROM _l WHERE n = 1), (SELECT auth_user_id FROM _u), NULL),
    '[{"col": "c_ok", "dir": "desc", "campo_sorgente": "campo_c_ok"}]'::jsonb,
    '27) U13: via la spenta, la non ordinabile e la sensibile; il campo sorgente esce');
SELECT is(
    ui.fn_ordinamento_lista((SELECT lista_codice FROM _l WHERE n = 2), (SELECT auth_user_id FROM _u), NULL),
    '[]'::jsonb,
    '28) una lista senza preset: []');

-- ============================================================
-- 29-31 La struttura
-- ============================================================
SELECT is(
    (SELECT string_agg(k, ',' ORDER BY k) FROM ui.lista_preset p, jsonb_object_keys(p.contenuto_aggiornato_il) k
      WHERE p.id = (SELECT preset_id FROM _p)),
    'colonne,pagina_dimensione',
    '29) la data del contenuto di un preset di lista ha le chiavi colonne e pagina_dimensione');
SELECT hasnt_column('ui', 'lista_preset', 'filtri_default', '30) ui.lista_preset non ha filtri_default');
SELECT is(
    (SELECT string_agg(format('%s:%s', t.tgrelid::regclass, t.tgfoid::regproc), ','
                       ORDER BY t.tgrelid::regclass::text COLLATE "C")
       FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND t.tgrelid IN ('ui.lista_preferenza_utente'::regclass, 'ui.dashboard_preferenza_utente'::regclass)
        AND t.tgname ~ '_a10_'),
    'ui.dashboard_preferenza_utente:ui.trgfn_preferenza_guard_forma,ui.lista_preferenza_utente:ui.trgfn_preferenza_guard_forma',
    '31) il guard di forma e'' montato sulle due preferenze, e nessun altro a10');

SELECT * FROM finish();
ROLLBACK;
