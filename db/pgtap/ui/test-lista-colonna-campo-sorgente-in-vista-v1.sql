-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il catalogo delle liste regge contro le viste che dichiara, cercate
--       NEL LORO SCHEMA (changeSet 20260927-30 e -31,
--       brief-db-liste-datatable-grezze §8 punti 6 e 7, Tid 2026-09-27).
--
--   Due presidi diversi, e servono entrambi:
--   - i TRIGGER (ui.trgfn_ui_lista_definizione_a10_valida_vista_sql,
--     ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente) giudicano la riga
--     che si scrive. Fino al 2026-09-27 cercavano la relazione per solo nome:
--     un'omonima in un altro schema (`comuni` in config e in storico) bastava.
--     I test 4 e 5 costruiscono proprio quel caso;
--   - il CATALOGO INTERO (test 1 e 2) si guarda qui, perche' i trigger non
--     vedono una riga che non si riscrive: una vista che cambia colonne, o una
--     lista che cambia vista, lasciano le colonne vecchie senza che nessun
--     trigger scatti. ⛔ La ri-validazione non si e' messa nel trigger della
--     definizione: il CSV delle definizioni si carica prima di quello delle
--     colonne, e un cambio di vista fatto insieme alle colonne farebbe morire
--     il migrate a meta'.
--
-- ⚠️ Il test 5 ha bisogno della gemella storica `storico.comuni` (la crea
--   l'automazione di storicizzazione): se non c'e', skip() dichiarato — senza
--   omonima il caso non si puo' costruire, e un verde lo direbbe per sottrazione.
--
-- Elenco test (plan 6):
--   1) ogni lista attiva con vista_sql ha la vista nel proprio schema_dati
--   2) ogni campo_sorgente (non azione, non vuoto) di quelle liste e' una colonna della vista
--      o della sintesi della lineage (D-B2, 2026-10-11)
--   3) le sei liste geografiche dichiarano tutte una vista (decisione §8 punto 6)
--   4) vista_sql che esiste solo in un ALTRO schema: E_UI_VISTA_SQL_NON_TROVATA
--   5) campo_sorgente che esiste solo nell'omonima di un altro schema: E_UI_CAMPO_SORGENTE_NON_TROVATO
--   6) la vista giusta nello schema giusto passa
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1-2) Il catalogo intero
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(ld.codice::text ORDER BY ld.codice), '{}'::text[])
       FROM ui.lista_definizione ld
      WHERE ld.attivo AND ld.vista_sql IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_class c
              JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = ld.schema_dati
               AND c.relname = ld.vista_sql
               AND c.relkind IN ('v', 'm', 'r'))),
    '{}'::text[],
    '1) ogni lista attiva con vista_sql ha la vista nel proprio schema_dati');

SELECT is(
    (SELECT COALESCE(array_agg(ld.codice || '.' || lc.campo_sorgente ORDER BY ld.codice, lc.campo_sorgente),
                     '{}'::text[])
       FROM ui.lista_colonna lc
       JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
      WHERE ld.attivo AND ld.vista_sql IS NOT NULL
        AND lc.tipo_colonna <> 'azione'
        AND COALESCE(lc.campo_sorgente, '') <> ''
        AND NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_class c
              JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
              JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid
             WHERE n.nspname = ld.schema_dati
               AND c.relname = ld.vista_sql
               AND a.attname = lc.campo_sorgente
               AND a.attnum > 0 AND NOT a.attisdropped)
        -- ⭐ D-B2 (giro B di brief-db-lineage-seminata-per-chiave, 2026-10-11):
        --    oppure e' una colonna della sintesi della lineage, che il backend
        --    chiede per le chiavi della pagina. Stessa regola del guard
        --    trgfn_ui_lista_colonna_a10_valida_campo_sorgente (20261011-99).
        AND NOT EXISTS (
            SELECT 1 FROM vendite.vw_documento_lineage_sintesi_colonne sc
             WHERE sc.colonna = lc.campo_sorgente)),
    '{}'::text[],
    '2) ogni campo_sorgente delle liste con vista e'' una colonna della vista o della sintesi della lineage (anche le colonne spente)');

-- ============================================================
-- 3) Le geografiche: tutte con la vista
-- ============================================================
SELECT is(
    (SELECT array_agg(ld.codice::text || ':' || COALESCE(ld.vista_sql, 'NULL') ORDER BY ld.codice)
       FROM ui.lista_definizione ld
      WHERE ld.codice IN ('config.regioni', 'config.province', 'config.stati',
                          'config.comuni', 'config.codici_postali', 'config.toponomastica')),
    ARRAY['config.codici_postali:vw_codici_postali_lista',
          'config.comuni:vw_comuni_lista',
          'config.province:vw_province_lista',
          'config.regioni:vw_regioni_lista',
          'config.stati:stati',
          'config.toponomastica:toponomastica'],
    '3) le sei liste geografiche dichiarano la loro vista');

-- ============================================================
-- 4-6) I trigger cercano nello schema della lista
-- ============================================================
-- `comuni` esiste in config (e in storico), non in anagrafiche.
SELECT throws_like(
    $$ INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
       VALUES ('_pgtap.vista_altro_schema', 'Lista pgTAP: vista in un altro schema',
               'anagrafiche', 'comuni', TRUE, 'pgtap') $$,
    '%anagrafiche.comuni%',
    '4) vista_sql che esiste solo in un altro schema: E_UI_VISTA_SQL_NON_TROVATA, col nome qualificato');

-- La lista giusta: config.comuni, la tabella (le colonne della gemella storica non ci sono).
INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
VALUES ('_pgtap.vista_schema_giusto', 'Lista pgTAP: vista nel suo schema',
        'config', 'comuni', TRUE, 'pgtap');

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                  JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                 WHERE n.nspname = 'storico' AND c.relname = 'comuni'
                   AND a.attname = 'valid_from' AND NOT a.attisdropped)
    THEN throws_like(
        $$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_colonna,
                                         tipo_dato, ordine_default, user_insert)
           SELECT ld.id, 'valid_from', 'Valido dal', 'valid_from', 'informazione', 'date', 10, 'pgtap'
             FROM ui.lista_definizione ld WHERE ld.codice = '_pgtap.vista_schema_giusto' $$,
        '%valid_from%config.comuni%',
        '5) campo_sorgente che esiste solo in storico.comuni: rifiutato su config.comuni')
    ELSE skip('5) storico.comuni non c''e'' (storicizzazione non applicata): l''omonima non si puo'' costruire', 1)
END;

SELECT lives_ok(
    $$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_colonna,
                                     tipo_dato, ordine_default, user_insert)
       SELECT ld.id, 'descrizione', 'Comune', 'descrizione', 'informazione', 'string', 10, 'pgtap'
         FROM ui.lista_definizione ld WHERE ld.codice = '_pgtap.vista_schema_giusto' $$,
    '6) la colonna vera della vista giusta nello schema giusto passa');

SELECT * FROM finish();
ROLLBACK;
