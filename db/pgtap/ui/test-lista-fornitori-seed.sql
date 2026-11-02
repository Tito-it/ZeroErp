-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed DEF-8 — lista configurabile anagrafiche.fornitori
-- Scope: verifica che migration 20260524-11/12 + aggiornamenti CSV
--        abbiano prodotto lo stato atteso nel DB.
--
-- Indice test (1..12):
--   1.  Vista vw_fornitori_dettaglio ha id_fiscale_univoco_cf_piva
--   2.  Lista anagrafiche.fornitori presente in lista_definizione
--   3.  vista_sql della lista = vw_fornitori_dettaglio
--   4.  Esattamente 15 colonne attive nel catalogo fornitori
--   5.  Colonna id_fiscale ha campo_sorgente = id_fiscale_univoco_cf_piva
--   6.  Colonne con tipo_dato='boolean' hanno formato='yesno' (split_payment + ritenuta_acconto)
--   7.  Preset fornitori_default presente con is_default=true
--   8.  Preset fornitori_default: pagina_dimensione=50, ambito=sistema
--   9.  Esattamente 7 colonne nel preset fornitori_default
--   10. Tutte le 7 colonne del preset hanno visibile=true
--   11. Colonna codice ha fissata=true nel preset
--   12. Il preset mostra id_fiscale (CF/PIVA unificato), NON codice_fiscale
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

SELECT plan(12);

-- =========================================================
-- 1. Vista vw_fornitori_dettaglio ha id_fiscale_univoco_cf_piva
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'anagrafiche'
           AND table_name   = 'vw_fornitori_dettaglio'
           AND column_name  = 'id_fiscale_univoco_cf_piva'
    ),
    '1. Vista vw_fornitori_dettaglio espone id_fiscale_univoco_cf_piva'
);

-- =========================================================
-- 2. Lista anagrafiche.fornitori presente in lista_definizione
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_definizione
         WHERE codice = 'anagrafiche.fornitori'
           AND attivo = TRUE
    ),
    '2. Lista anagrafiche.fornitori presente e attiva in lista_definizione'
);

-- =========================================================
-- 3. vista_sql della lista = vw_fornitori_dettaglio
-- =========================================================
SELECT is(
    (SELECT vista_sql FROM ui.lista_definizione WHERE codice = 'anagrafiche.fornitori'),
    'vw_fornitori_dettaglio',
    '3. Lista fornitori: vista_sql = vw_fornitori_dettaglio'
);

-- =========================================================
-- 4. Esattamente 15 colonne attive nel catalogo fornitori
-- =========================================================
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'anagrafiche.fornitori'
           AND lc.attivo = TRUE
    ),
    -- ⚠️ 13, non 15, e il 15 non e' mai stato vero rispetto al seed.
    --    Il commit che ha parametrizzato questa lista (2000d8261) ha introdotto
    --    `id_fiscale` — che UNISCE codice fiscale e partita IVA, vedi il test 5
    --    qui sotto — e ha disattivato le due colonne che rimpiazza
    --    (`codice_fiscale` e `partita_iva`, entrambe `attivo=f` nel CSV dallo
    --    stesso commit). Il conto pero' e' rimasto a quello di prima.
    --    15 colonne attive erano ottenibili solo con un database DIVERGENTE dal
    --    seed: il test passava per la divergenza, non nonostante.
    --    Emerso il 2026-08-02, quando una modifica non correlata allo stesso
    --    CSV ha fatto ri-girare il loader `runOnChange` e riallineato il DB.
    13,
    '4. Catalogo fornitori: esattamente 13 colonne attive (id_fiscale unisce CF e P.IVA)'
);

-- =========================================================
-- 5. Colonna id_fiscale punta a id_fiscale_univoco_cf_piva
-- =========================================================
SELECT is(
    (
        SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice  = 'anagrafiche.fornitori'
           AND lc.codice  = 'id_fiscale'
    ),
    'id_fiscale_univoco_cf_piva',
    '5. Colonna id_fiscale: campo_sorgente = id_fiscale_univoco_cf_piva'
);

-- =========================================================
-- 6. Colonne boolean hanno formato='yesno' (split_payment e ritenuta_acconto)
-- =========================================================
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice    = 'anagrafiche.fornitori'
           AND lc.tipo_dato = 'boolean'
           AND lc.formato   = 'yesno'
    ),
    2,
    '6. Colonne boolean (split_payment, ritenuta_acconto): formato = yesno'
);

-- =========================================================
-- 7. Preset fornitori_default presente con is_default=true
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset lp
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice   = 'anagrafiche.fornitori'
           AND lp.codice   = 'fornitori_default'
           AND lp.is_default = TRUE
           AND lp.attivo   = TRUE
    ),
    '7. Preset fornitori_default presente, is_default=true, attivo=true'
);

-- =========================================================
-- 8. Preset: pagina_dimensione=50, ambito=sistema
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset lp
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice          = 'anagrafiche.fornitori'
           AND lp.codice          = 'fornitori_default'
           AND lp.pagina_dimensione = 50
           AND lp.ambito::TEXT    = 'sistema'
    ),
    '8. Preset fornitori_default: pagina_dimensione=50, ambito=sistema'
);

-- =========================================================
-- 9. Esattamente 7 colonne nel preset fornitori_default
-- =========================================================
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_preset lp ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice  = 'anagrafiche.fornitori'
           AND lp.codice  = 'fornitori_default'
    ),
    7,
    '9. Preset fornitori_default: esattamente 7 colonne'
);

-- =========================================================
-- 10. Tutte le 7 colonne del preset hanno visibile=true
-- =========================================================
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_preset lp ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice    = 'anagrafiche.fornitori'
           AND lp.codice    = 'fornitori_default'
           AND lpc.visibile = TRUE
    ),
    7,
    '10. Tutte le 7 colonne del preset hanno visibile=true'
);

-- =========================================================
-- 11. Colonna codice fissata nel preset (identificatore)
-- =========================================================
SELECT ok(
    (
        SELECT lpc.fissata
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_colonna lc ON lc.id = lpc.colonna_id
          JOIN ui.lista_preset lp ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'anagrafiche.fornitori'
           AND lp.codice = 'fornitori_default'
           AND lc.codice = 'codice'
    ),
    '11. Colonna codice: fissata=true nel preset fornitori_default'
);

-- =========================================================
-- 12. Il preset mostra id_fiscale (CF/PIVA unificato), NON codice_fiscale
--     Verifica fix migration 20260524-12: riga stale codice_fiscale rimossa.
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_colonna lc    ON lc.id = lpc.colonna_id
          JOIN ui.lista_preset lp     ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'anagrafiche.fornitori'
           AND lp.codice = 'fornitori_default'
           AND lc.codice = 'id_fiscale'
    )
    AND NOT EXISTS (
        SELECT 1
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_colonna lc    ON lc.id = lpc.colonna_id
          JOIN ui.lista_preset lp     ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'anagrafiche.fornitori'
           AND lp.codice = 'fornitori_default'
           AND lc.codice = 'codice_fiscale'
    ),
    '12. Preset fornitori_default: colonna id_fiscale presente, codice_fiscale assente (fix 20260524-12)'
);

SELECT * FROM finish();
ROLLBACK;
