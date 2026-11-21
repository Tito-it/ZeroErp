-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il preset di base e il banner (giro 1a del brief-db-revisione-ui).
--   ui.fn_preset_di_base, ui.fn_preset_aggiornato, la chiave preset_base e
--   preset_base_cambiato dei resolver, lo snapshot scritto dal DB
--   (ui.trgfn_preferenza_preset_base_snapshot), un preset acceso per posto.
--   ChangeSet: 20261119-09 … -14; il banner per chiave e il lucchetto, giro
--   1b (20261120-02 … -11).
--
-- Gira come l'applicazione (runner di default). Tutti i soggetti si
--   costruiscono qui: due liste, una dashboard col suo pool, un'azienda, un
--   operatore con un profilo AD_HOC, i preset e le preferenze.
--
-- Elenco test (plan 20):
--    1-4) fn_preset_aggiornato, per chiave: senza snapshot nessuna; contenuto
--         piu' recente la chiave; U6, una chiave non passata non entra;
--         contenuto uguale nessuna
--    5) U3: un preset d'azienda senza colonne attive non ferma la cascata:
--       vince il sistema
--    6) … con una colonna attiva vince l'azienda
--    7) U7: l'azienda spenta non si applica: torna il sistema
--    8) il preset di ruolo del profilo, con la veste: vince il ruolo
--    9) Q28: con la veste NULL il ruolo si salta
--   10) nessun preset con contenuto: nessuna base
--   11) U3 dashboard: un preset fatto di widget spenti del pool non e' base
--   12) … con un widget del pool lo e'
--   13) Q30: un secondo preset acceso nello stesso posto e' rifiutato
--   14) … spento passa (la bozza)
--   15) U1: lo snapshot lo scrive il DB, il valore dell'app non conta
--   16) U2: il resolver espone preset_base, con l'id della base
--   17) U5: base salvata diversa da quella di oggi: preset_base_cambiato
--   18) … e preset_aggiornato tace
--   19) base di oggi, la misura del preset cambia dopo lo snapshot e la
--       preferenza imposta la misura: preset_aggiornato (dal giro 2 di
--       brief-db-revisione-ui la preferenza non porta piu' l'ordinamento)
--   20) … e preset_base_cambiato falso
--   21) Q38: riscrivere lo stesso preset_base_id chiude il banner
--   22) … e il cambio successivo del preset lo riaccende
--   23) U8: l'app che scrive la data del contenuto riceve E_UI_PRESET_CONTENUTO_DERIVATO
--   24) … e cosi' l'app che scrive un'impronta finta
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  VALUES ('_pgtap.base_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP preset di base', 'pgtap', NULL, TRUE, '_pgtap')
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice FROM ins;

CREATE TEMP TABLE _l2 AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  VALUES ('_pgtap.base_vuota_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP senza preset con contenuto', 'pgtap', NULL, TRUE, '_pgtap')
  RETURNING id
)
SELECT id AS lista_id FROM ins;

CREATE TEMP TABLE _c AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente,
                                tipo_colonna, tipo_dato, ordine_default, attivo, user_insert)
  SELECT l.lista_id, v.codice, v.codice, v.codice, 'informazione', 'string', v.ordine, v.attivo, '_pgtap'
    FROM (SELECT lista_id FROM _l UNION ALL SELECT lista_id FROM _l2) l,
         (VALUES ('c_uno', 10, TRUE), ('c_spenta', 20, FALSE)) AS v(codice, ordine, attivo)
  RETURNING id, lista_id, codice
)
SELECT id AS colonna_id, lista_id, codice FROM ins;

CREATE TEMP TABLE _u AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-preset-di-base', false);

CREATE TEMP TABLE _e AS
SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente();

CREATE TEMP TABLE _prof AS
WITH ins AS (
  INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
  VALUES ('AD_HOC', '_PGTAP_BASE_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
          'Profilo AD_HOC test preset di base', TRUE)
  RETURNING id
)
SELECT id AS profilo_id FROM ins;

DO $lega$ BEGIN
  PERFORM config.fn_lega_profilo_identita((SELECT profilo_id FROM _prof), (SELECT identita_id FROM _u));
END $lega$;

-- Un preset per posto sulla lista: sistema con una colonna attiva, azienda
-- con la sola colonna spenta, ruolo del profilo con una colonna attiva.
CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, profilo_accesso_id,
                               emittente_fiscale_id, attivo, user_insert)
  SELECT l.lista_id, v.codice, v.codice, v.ambito::ui.ambito_preset,
         CASE WHEN v.ambito = 'ruolo' THEN (SELECT profilo_id FROM _prof) END,
         CASE WHEN v.ambito = 'emittente_fiscale' THEN (SELECT emittente_fiscale_id FROM _e) END,
         TRUE, '_pgtap'
    FROM _l l,
         (VALUES ('p_sistema', 'sistema'), ('p_azienda', 'emittente_fiscale'), ('p_ruolo', 'ruolo')) AS v(codice, ambito)
  RETURNING id, codice
)
SELECT id AS preset_id, codice FROM ins;

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile)
SELECT p.preset_id, c.colonna_id, 1, TRUE
  FROM _p p
  JOIN _c c ON c.lista_id = (SELECT lista_id FROM _l)
 WHERE (p.codice IN ('p_sistema', 'p_ruolo') AND c.codice = 'c_uno')
    OR (p.codice = 'p_azienda' AND c.codice = 'c_spenta');

-- La seconda lista: un preset di sistema con la sola colonna spenta.
WITH x AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, attivo, user_insert)
  SELECT lista_id, 'p_vuoto', 'p_vuoto', 'sistema', TRUE, '_pgtap' FROM _l2
  RETURNING id
)
INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile)
SELECT x.id, c.colonna_id, 1, TRUE
  FROM x
  JOIN _c c ON c.lista_id = (SELECT lista_id FROM _l2) AND c.codice = 'c_spenta';

CREATE OR REPLACE FUNCTION pg_temp.base_lista(p_veste config.ruolo_applicativo, p_lista integer DEFAULT NULL)
RETURNS text LANGUAGE sql AS $$
    SELECT (SELECT codice FROM ui.lista_preset WHERE id = b.preset_id)
      FROM ui.fn_preset_di_base('lista', COALESCE(p_lista, (SELECT lista_id FROM _l)),
                                (SELECT auth_user_id FROM _u), p_veste,
                                (SELECT emittente_fiscale_id FROM _e)) b;
$$;

-- La dashboard: pool coi widget w_pool (acceso) e w_spento (spento).
CREATE TEMP TABLE _d AS
WITH ins AS (
  INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
  VALUES ('_pgtap.base_' || substr(md5(clock_timestamp()::text), 1, 6), 'Dashboard test preset di base', TRUE, '_pgtap')
  RETURNING id
)
SELECT id AS dashboard_id FROM ins;

CREATE TEMP TABLE _w AS
WITH ins AS (
  INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
  VALUES ('_pgtap_w_pool_' || substr(md5(clock_timestamp()::text), 1, 6), 'Nel pool', 'kpi', TRUE, '_pgtap'),
         ('_pgtap_w_spento_' || substr(md5(clock_timestamp()::text), 1, 6), 'Spento nel pool', 'kpi', FALSE, '_pgtap')
  RETURNING id, etichetta
)
SELECT id AS widget_id, etichetta FROM ins;

INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT d.dashboard_id, w.widget_id, 10 FROM _d d, _w w;
-- ⚠️ Dal giro 2b di brief-db-revisione-ui un preset non puo' proporre un widget
--   fuori dal pool (fk_ui_dashboard_preset_widget_pool): il caso 11 lo costruisce
--   con l'unico widget del pool spento, che la scelta della base non conta.

CREATE TEMP TABLE _dp AS
WITH ins AS (
  INSERT INTO ui.dashboard_preset (dashboard_id, codice, descrizione, ambito, dimensione_max, attivo, user_insert)
  SELECT dashboard_id, 'dp_sistema', 'dp_sistema', 'sistema', 6, TRUE, '_pgtap' FROM _d
  RETURNING id
)
SELECT id AS preset_id FROM ins;

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 1, TRUE FROM _dp p, _w w WHERE w.etichetta = 'Spento nel pool';

-- ============================================================
-- 1-4 Il flag
-- ============================================================
-- Snapshot e contenuto sono mappe {chiave: data}; il chiamante passa le chiavi
-- che la preferenza imposta.
SELECT is(ui.fn_preset_aggiornato(NULL, jsonb_build_object('colonne', now()), ARRAY['colonne']),
          ARRAY[]::text[], '1) senza snapshot: nessuna chiave');
SELECT is(ui.fn_preset_aggiornato(jsonb_build_object('colonne', now() - interval '1 day'),
                                  jsonb_build_object('colonne', now()), ARRAY['colonne']),
          ARRAY['colonne'], '2) contenuto piu'' recente dello snapshot: la chiave');
SELECT is(ui.fn_preset_aggiornato(jsonb_build_object('colonne', now() - interval '1 day', 'pagina_dimensione', now() - interval '1 day'),
                                  jsonb_build_object('colonne', now() - interval '1 day', 'pagina_dimensione', now()),
                                  ARRAY['colonne']),
          ARRAY[]::text[], '3) U6: cambia una chiave che la preferenza non imposta: nessuna');
SELECT is(ui.fn_preset_aggiornato(jsonb_build_object('colonne', now()), jsonb_build_object('colonne', now()),
                                  ARRAY['colonne']),
          ARRAY[]::text[], '4) contenuto uguale allo snapshot: nessuna');

-- ============================================================
-- 5-10 La scelta, liste
-- ============================================================
SELECT is(pg_temp.base_lista(NULL), 'p_sistema',
          '5) U3: il preset d''azienda senza colonne attive non ferma la cascata');

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile)
SELECT p.preset_id, c.colonna_id, 2, TRUE
  FROM _p p JOIN _c c ON c.lista_id = (SELECT lista_id FROM _l) AND c.codice = 'c_uno'
 WHERE p.codice = 'p_azienda';

SELECT is(pg_temp.base_lista(NULL), 'p_azienda', '6) … con una colonna attiva vince l''azienda');

UPDATE anagrafiche.emittenti_fiscali SET attivo = false WHERE id = (SELECT emittente_fiscale_id FROM _e);

SELECT is(pg_temp.base_lista(NULL), 'p_sistema', '7) U7: l''azienda spenta non si applica');

SELECT is(pg_temp.base_lista('OPERATORE'), 'p_ruolo', '8) con la veste vince il preset di ruolo del profilo');

SELECT is(pg_temp.base_lista(NULL), 'p_sistema', '9) Q28: con la veste NULL il ruolo si salta');

SELECT is(pg_temp.base_lista('OPERATORE', (SELECT lista_id FROM _l2)), NULL,
          '10) nessun preset con contenuto: nessuna base');

-- ============================================================
-- 11-12 La scelta, dashboard
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM ui.fn_preset_di_base('dashboard', (SELECT dashboard_id FROM _d),
                                                    (SELECT auth_user_id FROM _u), 'OPERATORE', NULL)),
    0,
    '11) U3: un preset fatto di widget spenti del pool non e'' base');

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 2, TRUE FROM _dp p, _w w WHERE w.etichetta = 'Nel pool';

SELECT is(
    (SELECT b.preset_id FROM ui.fn_preset_di_base('dashboard', (SELECT dashboard_id FROM _d),
                                                  (SELECT auth_user_id FROM _u), 'OPERATORE', NULL) b),
    (SELECT preset_id FROM _dp),
    '12) … con un widget del pool lo e''');

-- ============================================================
-- 13-14 Un preset acceso per posto
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$
        INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, attivo, user_insert)
        SELECT lista_id, 'p_sistema_bis', 'p_sistema_bis', 'sistema', TRUE, '_pgtap' FROM _l$$),
    'uq_ui_lista_preset_posto',
    '13) Q30: un secondo preset acceso nello stesso posto e'' rifiutato');

SELECT is(
    dbops.fn_pgtap_codice_errore($$
        INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, attivo, user_insert)
        SELECT lista_id, 'p_sistema_bozza', 'p_sistema_bozza', 'sistema', FALSE, '_pgtap' FROM _l$$),
    NULL,
    '14) … spento passa: la bozza');

-- ============================================================
-- 15-20 Lo snapshot e il banner, attraverso il resolver
-- ============================================================
-- La preferenza salva come base il preset di sistema, con uno snapshot
-- inventato dall'app: conta la data del preset.
INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, configurazione, preset_base_id,
                                        preset_base_contenuto_aggiornato_il)
VALUES ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l), '{}'::jsonb,
        (SELECT preset_id FROM _p WHERE codice = 'p_sistema'),
        '{"colonne": "2000-01-01T00:00:00+00:00"}'::jsonb);

SELECT is(
    (SELECT pu.preset_base_contenuto_aggiornato_il FROM ui.lista_preferenza_utente pu
      WHERE pu.auth_user_id = (SELECT auth_user_id FROM _u) AND pu.lista_id = (SELECT lista_id FROM _l)),
    (SELECT lp.contenuto_aggiornato_il FROM ui.lista_preset lp JOIN _p p ON p.preset_id = lp.id
      WHERE p.codice = 'p_sistema'),
    '15) U1: lo snapshot lo scrive il DB, il valore dell''app non conta');

-- Senza veste (contesto del test) e con l'azienda spenta la base di oggi e' il sistema.
CREATE OR REPLACE FUNCTION pg_temp.risolta() RETURNS jsonb LANGUAGE sql AS $$
    SELECT ui.fn_resolve_lista_config((SELECT lista_codice FROM _l), (SELECT auth_user_id FROM _u),
                                      (SELECT emittente_fiscale_id FROM _e));
$$;

SELECT is(
    (pg_temp.risolta() -> 'preset_base' ->> 'id')::integer,
    (SELECT b.preset_id FROM ui.fn_preset_di_base('lista', (SELECT lista_id FROM _l),
                                                  (SELECT auth_user_id FROM _u), ui.fn_veste_corrente(),
                                                  (SELECT emittente_fiscale_id FROM _e)) b),
    '16) U2: il resolver espone preset_base, con l''id della base');

-- La preferenza salva come base il preset di ruolo: oggi la base e' un'altra
-- se la veste del contesto non lo rende applicabile, e il test lo forza
-- scegliendo come base salvata un preset che non e' quella di oggi.
UPDATE ui.lista_preferenza_utente
   SET preset_base_id = (SELECT p.preset_id FROM _p p
                          WHERE p.codice <> (SELECT lp.codice FROM ui.lista_preset lp
                                              WHERE lp.id = (pg_temp.risolta() -> 'preset_base' ->> 'id')::integer)
                          ORDER BY p.codice LIMIT 1)
 WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND lista_id = (SELECT lista_id FROM _l);

SELECT is((pg_temp.risolta() ->> 'preset_base_cambiato')::boolean, true,
          '17) U5: la base salvata non e'' quella di oggi: preset_base_cambiato');
SELECT is((pg_temp.risolta() ->> 'preset_aggiornato')::boolean, false, '18) … e preset_aggiornato tace');

-- Di nuovo la base di oggi, con una preferenza sulla misura; poi la misura
-- del preset cambia dopo lo snapshot.
UPDATE ui.lista_preferenza_utente
   SET preset_base_id = (pg_temp.risolta() -> 'preset_base' ->> 'id')::integer,
       configurazione = jsonb_build_object('pagina_dimensione', (SELECT min(m.misura) FROM ui.misure_pagina m))
 WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND lista_id = (SELECT lista_id FROM _l);
CREATE TEMP TABLE _base AS SELECT (pg_temp.risolta() -> 'preset_base' ->> 'id')::integer AS preset_id;
UPDATE ui.lista_preset SET pagina_dimensione = (SELECT max(m.misura) FROM ui.misure_pagina m)
 WHERE id = (SELECT preset_id FROM _base);

SELECT is((pg_temp.risolta() ->> 'preset_aggiornato')::boolean, true,
          '19) base di oggi, preset cambiato dopo lo snapshot: preset_aggiornato');
SELECT is((pg_temp.risolta() ->> 'preset_base_cambiato')::boolean, false, '20) … e preset_base_cambiato falso');

-- ============================================================
-- 21-22 Q38: «Ignora» e' riscrivere preset_base_id
-- ============================================================
UPDATE ui.lista_preferenza_utente SET preset_base_id = preset_base_id
 WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND lista_id = (SELECT lista_id FROM _l);

SELECT is(format('%s|%s', pg_temp.risolta() ->> 'preset_aggiornato', pg_temp.risolta() -> 'preset_aggiornato_chiavi'),
          'false|[]', '21) Q38: riscrivere lo stesso preset_base_id riallinea lo snapshot: il banner si chiude');

UPDATE ui.lista_preset SET pagina_dimensione = (SELECT min(m.misura) FROM ui.misure_pagina m)
 WHERE id = (SELECT preset_id FROM _base);

SELECT is(format('%s|%s', pg_temp.risolta() ->> 'preset_aggiornato', pg_temp.risolta() -> 'preset_aggiornato_chiavi'),
          'true|["pagina_dimensione"]', '22) … e il cambio successivo del preset lo riaccende');

-- ============================================================
-- 23-24 U8: la data del contenuto e l'impronta le scrive solo il DB
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$
        UPDATE ui.lista_preset SET contenuto_aggiornato_il = contenuto_aggiornato_il || '{"colonne": "2000-01-01T00:00:00+00:00"}'::jsonb
         WHERE id = (SELECT preset_id FROM _base)$$),
    'E_UI_PRESET_CONTENUTO_DERIVATO',
    '23) U8: l''app scrive la data del contenuto: rifiutato');
SELECT is(
    dbops.fn_pgtap_codice_errore($$
        UPDATE ui.lista_preset SET composizione_impronta = 'finta' WHERE id = (SELECT preset_id FROM _base)$$),
    'E_UI_PRESET_CONTENUTO_DERIVATO',
    '24) U8: l''app scrive un''impronta che non e'' quella della composizione: rifiutato');

SELECT * FROM finish();
ROLLBACK;
