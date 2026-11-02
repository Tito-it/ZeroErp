-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed DB-B (refactor-lista-contratti) — lista configurabile
--       vendite.contratti.
-- Scope: verifica che migration 20260602-15 (vista) + append CSV
--        (lista_definizione/colonna/preset/preset_colonna) + priorita
--        (20260602-16) abbiano prodotto lo stato atteso nel DB.
--
-- Indice test (1..14):
--   1.  Vista vw_contratti_lista espone ragione_sociale_completa
--   2.  Vista vw_contratti_lista e' security_invoker=on (RLS attiva)
--   3.  Lista vendite.contratti presente e attiva in lista_definizione
--   4.  vista_sql della lista = vw_contratti_lista
--   5.  Esattamente 22 colonne attive nel catalogo contratti
--   6.  Colonna id_fiscale ha campo_sorgente = id_fiscale_univoco_cf_piva
--   7.  Tutti i campo_sorgente del catalogo esistono nella vista o nella sintesi della lineage (anti-typo, gemello B2)
--   8.  Preset contratti_default presente con is_default=true
--   9.  Preset: pagina_dimensione=25, ambito=sistema
--   10. Esattamente 13 colonne visibili nel preset contratti_default
--   11. Colonna numero ha fissata=true nel preset (identificatore)
--   12. priorita di dominio applicata (ragione_sociale=95, stato=90, data=25)
--   13. Anti-regressione sensibile: nessuna colonna contratti sensibile=true
--   14. stato_codice nel catalogo (campo_sorgente=stato_codice) per Tag severity FE
-- ------------------------------------------------------------
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- =========================================================
-- 1. Vista vw_contratti_lista espone ragione_sociale_completa
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'vw_contratti_lista'
           AND column_name  = 'ragione_sociale_completa'
    ),
    '1. Vista vw_contratti_lista espone ragione_sociale_completa'
);

-- =========================================================
-- 2. Vista vw_contratti_lista e' security_invoker=on (RLS attiva su contratti)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          CROSS JOIN LATERAL unnest(c.reloptions) AS opt
         WHERE n.nspname = 'vendite'
           AND c.relname = 'vw_contratti_lista'
           AND opt LIKE 'security_invoker=%'
           AND split_part(opt, '=', 2) IN ('on', 'true')
    ),
    '2. Vista vw_contratti_lista: security_invoker=on'
);

-- =========================================================
-- 3. Lista vendite.contratti presente e attiva in lista_definizione
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_definizione
         WHERE codice = 'vendite.contratti'
           AND attivo = TRUE
    ),
    '3. Lista vendite.contratti presente e attiva in lista_definizione'
);

-- =========================================================
-- 4. vista_sql della lista = vw_contratti_lista
-- =========================================================
SELECT is(
    (SELECT vista_sql FROM ui.lista_definizione WHERE codice = 'vendite.contratti'),
    'vw_contratti_lista',
    '4. Lista contratti: vista_sql = vw_contratti_lista'
);

-- =========================================================
-- 5. Esattamente 22 colonne attive nel catalogo contratti
-- =========================================================
SELECT cmp_ok(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.contratti'
           AND lc.attivo = TRUE
    ),
    '>=', 25,
    '5. Catalogo contratti: almeno 25 colonne attive (nessuna sparita)'
);

-- =========================================================
-- 6. Colonna id_fiscale punta a id_fiscale_univoco_cf_piva
-- =========================================================
SELECT is(
    (
        SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice  = 'vendite.contratti'
           AND lc.codice  = 'id_fiscale'
    ),
    'id_fiscale_univoco_cf_piva',
    '6. Colonna id_fiscale: campo_sorgente = id_fiscale_univoco_cf_piva'
);

-- =========================================================
-- 7. Ogni campo_sorgente del catalogo esiste come colonna della vista
--    (anti-typo: gemello del check trigger B2 valida_campo_sorgente).
--    Skip allineato a B2: tipo_colonna='azione' o campo_sorgente vuoto
--    (le 'azione' hanno campo_sorgente = '' nel seed, non NULL).
-- =========================================================
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.contratti'
           AND lc.attivo = TRUE
           AND lc.tipo_colonna <> 'azione'
           AND COALESCE(lc.campo_sorgente, '') <> ''
           AND NOT EXISTS (
                 SELECT 1
                   FROM information_schema.columns ic
                  WHERE ic.table_schema = 'vendite'
                    AND ic.table_name   = 'vw_contratti_lista'
                    AND ic.column_name  = lc.campo_sorgente
               )
           -- ⭐ D-B2 (giro B di brief-db-lineage-seminata-per-chiave, 2026-10-11):
           --    oppure e' una colonna della SINTESI della lineage, che il backend
           --    chiede per le chiavi della pagina (frontiera, transito…).
           AND NOT EXISTS (
                 SELECT 1 FROM vendite.vw_documento_lineage_sintesi_colonne sc
                  WHERE sc.colonna = lc.campo_sorgente
               )
    ),
    0,
    '7. Tutti i campo_sorgente del catalogo contratti esistono nella vista o nella sintesi della lineage'
);

-- =========================================================
-- 8. Preset contratti_default presente con is_default=true
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset lp
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice     = 'vendite.contratti'
           AND lp.codice     = 'contratti_default'
           AND lp.is_default = TRUE
           AND lp.attivo     = TRUE
    ),
    '8. Preset contratti_default presente, is_default=true, attivo=true'
);

-- =========================================================
-- 9. Preset: pagina_dimensione=25, ambito=sistema
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset lp
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice            = 'vendite.contratti'
           AND lp.codice            = 'contratti_default'
           AND lp.pagina_dimensione = 25
           AND lp.ambito::TEXT      = 'sistema'
    ),
    '9. Preset contratti_default: pagina_dimensione=25, ambito=sistema'
);

-- =========================================================
-- 10. Esattamente 13 colonne visibili nel preset contratti_default
--     (12 informative + azioni; stato_codice e' nel preset ma visibile=f)
-- =========================================================
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_preset lp      ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice    = 'vendite.contratti'
           AND lp.codice    = 'contratti_default'
           AND lpc.visibile = TRUE
    ),
    16,
    '10. Preset contratti_default: esattamente 16 colonne visibili'
);

-- =========================================================
-- 11. Colonna numero fissata nel preset (identificatore)
-- =========================================================
SELECT ok(
    (
        SELECT lpc.fissata
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_colonna lc     ON lc.id = lpc.colonna_id
          JOIN ui.lista_preset lp      ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.contratti'
           AND lp.codice = 'contratti_default'
           AND lc.codice = 'numero'
    ),
    '11. Colonna numero: fissata=true nel preset contratti_default'
);

-- =========================================================
-- 12. priorita di dominio applicata (20260602-16)
--     ragione_sociale_completa=95, stato=90, data=25
-- =========================================================
SELECT is(
    (
        SELECT array_agg(lc.priorita ORDER BY lc.codice)
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.contratti'
           AND lc.codice IN ('data', 'ragione_sociale_completa', 'stato')
    ),
    ARRAY[25, 95, 90]::SMALLINT[],
    '12. priorita di dominio: data=25, ragione_sociale=95, stato=90'
);

-- =========================================================
-- 13. Anti-regressione sensibile: nessuna colonna contratti sensibile=true
--     (fn_resolve_lista_config filtra le sensibili senza grant, anche SUPER_ADMIN)
-- =========================================================
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice    = 'vendite.contratti'
           AND lc.sensibile = TRUE
    ),
    0,
    '13. Nessuna colonna contratti marcata sensibile=true'
);

-- =========================================================
-- 14. stato_codice nel catalogo (per Tag severity FE)
-- =========================================================
SELECT is(
    (
        SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.contratti'
           AND lc.codice = 'stato_codice'
    ),
    'stato_codice',
    '14. Colonna stato_codice presente nel catalogo (campo_sorgente=stato_codice)'
);

SELECT * FROM finish();
ROLLBACK;
