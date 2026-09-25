-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la PORTA del pannello di configurazione e il presidio della sua lista.
--   Brief: brief-db-pannello-config-verbo-generico, sezioni 3.1 e 3.5.
--
-- Elenco test (plan 7):
--   La porta (tre sedi: forward 90_end/20260925-34, loop 20260205-41, provisioning)
--    1) magazzino.causali: all'app SELECT si', nessuna scrittura
--    2) config.tabelle_gestibili: all'app SELECT si', nessuna scrittura (la lista e' una porta)
--    3) come app, UPDATE di magazzino.causali: permesso negato
--    4) come app, INSERT in config.tabelle_gestibili: permesso negato
--   Il presidio della lista (config.tabelle_gestibili)
--    5) la lista non e' vuota, e ogni riga risolve una tabella con la colonna id
--    6) nessuna riga del pannello ha la RLS (D-P2: il verbo generico non sa
--       rimettere un perimetro)
--    7) l'area di ogni riga del pannello e' a catalogo, tranne ui.lista_definizione
--       (area 'ui' non a catalogo: la scrive solo il SUPER_ADMIN, dichiarato)
--
-- ⚠️ Gira come l'APPLICAZIONE: 1-4 sono veri solo li' (da proprietario rossi per
--   costruzione). Il 4 scrive con `WHERE false`: il privilegio si controlla lo
--   stesso, e da proprietario non entra nessuna riga che sporchi i presidi dopo. I presidi 5-7 leggono la
--   lista che il seed di CATALOGO semina (nessun context): su un database
--   ricostruito da zero non e' vuota, e il 5 lo pretende.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

SELECT is(
    format('%s|%s', has_table_privilege('zeroerp_app', 'magazzino.causali', 'SELECT')::text,
                    has_table_privilege('zeroerp_app', 'magazzino.causali', 'INSERT, UPDATE, DELETE')::text),
    'true|false',
    '1) magazzino.causali: all''app SELECT si'', nessuna scrittura (la scrive il verbo del pannello)');

SELECT is(
    format('%s|%s', has_table_privilege('zeroerp_app', 'config.tabelle_gestibili', 'SELECT')::text,
                    has_table_privilege('zeroerp_app', 'config.tabelle_gestibili', 'INSERT, UPDATE, DELETE')::text),
    'true|false',
    '2) config.tabelle_gestibili: all''app SELECT si'', nessuna scrittura');

SELECT throws_ok(
    $$ UPDATE magazzino.causali SET id = id WHERE false $$,
    '42501', NULL,
    '3) come app, UPDATE di magazzino.causali: permesso negato');

SELECT throws_ok(
    $$ INSERT INTO config.tabelle_gestibili (codice_interno, schema_tabella, nome_tabella, app_label, model_name, pannello)
       SELECT 'magazzino.movimenti', 'magazzino', 'movimenti', 'magazzino', 'movimenti', true WHERE false $$,
    '42501', NULL,
    '4) come app, INSERT in config.tabelle_gestibili: permesso negato (niente tabelle chiuse aggiunte alla lista)');

SELECT is(
    (SELECT format('%s|%s', (count(*) > 0)::text,
                   COALESCE(string_agg(tg.codice_interno, ',' ORDER BY tg.codice_interno)
                                FILTER (WHERE NOT EXISTS (
                                    SELECT 1 FROM pg_class c
                                      JOIN pg_namespace n ON n.oid = c.relnamespace
                                      JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'id' AND NOT a.attisdropped
                                     WHERE n.nspname = tg.schema_tabella AND c.relname = tg.nome_tabella)), ''))
       FROM config.tabelle_gestibili tg),
    'true|',
    '5) la lista non e'' vuota e ogni riga risolve una tabella con la colonna id');

SELECT is(
    (SELECT COALESCE(string_agg(tg.codice_interno, ',' ORDER BY tg.codice_interno), '')
       FROM config.tabelle_gestibili tg
       JOIN pg_namespace n ON n.nspname = tg.schema_tabella
       JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = tg.nome_tabella
      WHERE tg.pannello AND c.relrowsecurity),
    '',
    '6) nessuna tabella del pannello ha la RLS (D-P2)');

SELECT is(
    (SELECT COALESCE(string_agg(tg.codice_interno, ',' ORDER BY tg.codice_interno), '')
       FROM config.tabelle_gestibili tg
      WHERE tg.pannello
        AND NOT EXISTS (SELECT 1 FROM config.aree_funzionali af
                         WHERE af.schema_db = script.fn_area_di_oggetto(tg.app_label, tg.model_name))),
    'ui.lista_definizione',
    '7) ogni riga del pannello ha un''area a catalogo, tranne ui.lista_definizione (solo SUPER_ADMIN, dichiarato)');

SELECT * FROM finish();
ROLLBACK;
