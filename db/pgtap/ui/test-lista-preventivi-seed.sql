-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed DB-B (db-brief-lista-preventivi-offerte) — lista configurabile
--       vendite.preventivi.
-- Scope: verifica che migration 20260603-05 (vista vw_preventivi_lista) +
--        append CSV (lista_definizione/colonna/preset/preset_colonna) +
--        priorita (20260603-07) abbiano prodotto lo stato atteso nel DB.
--
-- Indice test (1..14):
--   1.  Vista vw_preventivi_lista espone ragione_sociale_completa
--   2.  Vista vw_preventivi_lista e' security_invoker=on (RLS-ready)
--   3.  Lista vendite.preventivi presente e attiva in lista_definizione
--   4.  vista_sql della lista = vw_preventivi_lista
--   5.  Esattamente 21 colonne attive nel catalogo preventivi
--   6.  Colonna id_fiscale ha campo_sorgente = id_fiscale_univoco_cf_piva
--   7.  Tutti i campo_sorgente del catalogo esistono nella vista (anti-typo, gemello B2)
--   8.  Preset preventivi_default presente con is_default=true
--   9.  Preset: pagina_dimensione=25, ambito=sistema
--   10. Esattamente 12 colonne visibili nel preset preventivi_default
--   11. Colonna numero ha fissata=true nel preset (identificatore)
--   12. priorita di dominio applicata (data=25, ragione_sociale=95, stato=90)
--   13. Anti-regressione sensibile: nessuna colonna preventivi sensibile=true
--   14. stato_codice_interno nel catalogo (campo_sorgente=stato_codice_interno) per Tag severity FE
-- ------------------------------------------------------------
BEGIN;
SELECT plan(14);

-- 1. Vista espone ragione_sociale_completa
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'vw_preventivi_lista'
           AND column_name  = 'ragione_sociale_completa'
    ),
    '1. Vista vw_preventivi_lista espone ragione_sociale_completa'
);

-- 2. Vista security_invoker=on
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          CROSS JOIN LATERAL unnest(c.reloptions) AS opt
         WHERE n.nspname = 'vendite'
           AND c.relname = 'vw_preventivi_lista'
           AND opt LIKE 'security_invoker=%'
           AND split_part(opt, '=', 2) IN ('on', 'true')
    ),
    '2. Vista vw_preventivi_lista: security_invoker=on'
);

-- 3. Lista presente e attiva
SELECT ok(
    EXISTS (
        SELECT 1 FROM ui.lista_definizione
         WHERE codice = 'vendite.preventivi' AND attivo = TRUE
    ),
    '3. Lista vendite.preventivi presente e attiva in lista_definizione'
);

-- 4. vista_sql corretta
SELECT is(
    (SELECT vista_sql FROM ui.lista_definizione WHERE codice = 'vendite.preventivi'),
    'vw_preventivi_lista',
    '4. Lista preventivi: vista_sql = vw_preventivi_lista'
);

-- 5. 21 colonne attive nel catalogo
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.preventivi' AND lc.attivo = TRUE
    ),
    21,
    '5. Catalogo preventivi: esattamente 21 colonne attive'
);

-- 6. id_fiscale -> id_fiscale_univoco_cf_piva
SELECT is(
    (
        SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.preventivi' AND lc.codice = 'id_fiscale'
    ),
    'id_fiscale_univoco_cf_piva',
    '6. Colonna id_fiscale: campo_sorgente = id_fiscale_univoco_cf_piva'
);

-- 7. Ogni campo_sorgente esiste nella vista (anti-typo, gemello B2)
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.preventivi'
           AND lc.attivo = TRUE
           AND lc.tipo_colonna <> 'azione'
           AND COALESCE(lc.campo_sorgente, '') <> ''
           AND NOT EXISTS (
                 SELECT 1 FROM information_schema.columns ic
                  WHERE ic.table_schema = 'vendite'
                    AND ic.table_name   = 'vw_preventivi_lista'
                    AND ic.column_name  = lc.campo_sorgente
               )
    ),
    0,
    '7. Tutti i campo_sorgente del catalogo preventivi esistono nella vista'
);

-- 8. Preset preventivi_default is_default=true
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset lp
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.preventivi'
           AND lp.codice = 'preventivi_default'
           AND lp.is_default = TRUE
           AND lp.attivo = TRUE
    ),
    '8. Preset preventivi_default presente, is_default=true, attivo=true'
);

-- 9. Preset: pagina_dimensione=25, ambito=sistema
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset lp
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.preventivi'
           AND lp.codice = 'preventivi_default'
           AND lp.pagina_dimensione = 25
           AND lp.ambito::TEXT = 'sistema'
    ),
    '9. Preset preventivi_default: pagina_dimensione=25, ambito=sistema'
);

-- 10. 12 colonne visibili nel preset
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_preset lp      ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.preventivi'
           AND lp.codice = 'preventivi_default'
           AND lpc.visibile = TRUE
    ),
    12,
    '10. Preset preventivi_default: esattamente 12 colonne visibili'
);

-- 11. numero fissata=true
SELECT ok(
    (
        SELECT lpc.fissata
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_colonna lc     ON lc.id = lpc.colonna_id
          JOIN ui.lista_preset lp      ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.preventivi'
           AND lp.codice = 'preventivi_default'
           AND lc.codice = 'numero'
    ),
    '11. Colonna numero: fissata=true nel preset preventivi_default'
);

-- 12. priorita di dominio (data=25, ragione_sociale=95, stato=90)
SELECT is(
    (
        SELECT array_agg(lc.priorita ORDER BY lc.codice)
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.preventivi'
           AND lc.codice IN ('data', 'ragione_sociale_completa', 'stato')
    ),
    ARRAY[25, 95, 90]::SMALLINT[],
    '12. priorita di dominio: data=25, ragione_sociale=95, stato=90'
);

-- 13. nessuna colonna sensibile=true
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.preventivi' AND lc.sensibile = TRUE
    ),
    0,
    '13. Nessuna colonna preventivi marcata sensibile=true'
);

-- 14. stato_codice_interno nel catalogo (Tag severity FE)
SELECT is(
    (
        SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.preventivi' AND lc.codice = 'stato_codice_interno'
    ),
    'stato_codice_interno',
    '14. Colonna stato_codice_interno presente (campo_sorgente=stato_codice_interno)'
);

SELECT * FROM finish();
ROLLBACK;
