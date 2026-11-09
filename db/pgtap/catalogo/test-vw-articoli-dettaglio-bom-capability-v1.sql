-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.vw_articoli_dettaglio campi capability BoM
-- (Fase 6 BE 28-04-2026, migration 20260428-07).
--
-- Capability esposte:
--   puo_gestire_bom         BOOLEAN  = is_composito AND NOT is_solo_componente
--   motivo_non_gestibile_bom TEXT    = NULL                       [ok]
--                                    | 'ARTICOLO_SOLO_COMPONENTE' [se is_solo_componente]
--                                    | 'ARTICOLO_NON_COMPOSITO'   [se NOT is_composito]
--
-- Edge case is_composito=false AND is_solo_componente=true:
--   prevale 'ARTICOLO_SOLO_COMPONENTE'.
--
-- Setup: due articoli costruiti con combinazioni distinte di
-- (is_composito, is_solo_componente) scelte alla nascita; lo Scenario C
-- spegne i due flag sul secondo.
--
-- Indice test (1..7):
--   1. presenza colonne aggiunte
--   Scenario A) composito non solo componente -> puo_gestire_bom=true, motivo=NULL
--     2. puo_gestire_bom = true
--     3. motivo_non_gestibile_bom = NULL
--   Scenario B) is_solo_componente=true (non composito: il CHECK vieta i due insieme) -> motivo='ARTICOLO_SOLO_COMPONENTE'
--     4. puo_gestire_bom = false
--     5. motivo_non_gestibile_bom = 'ARTICOLO_SOLO_COMPONENTE'
--   Scenario C) is_composito=false e is_solo_componente=false -> motivo='ARTICOLO_NON_COMPOSITO'
--     6. puo_gestire_bom = false
--     7. motivo_non_gestibile_bom = 'ARTICOLO_NON_COMPOSITO'
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

SELECT plan(7);

-- =========================================================
-- 1) Presenza colonne aggiunte
-- =========================================================
SELECT bag_has(
    $$ SELECT column_name
         FROM information_schema.columns
        WHERE table_schema = 'catalogo'
          AND table_name   = 'vw_articoli_dettaglio'
          AND column_name IN ('puo_gestire_bom', 'motivo_non_gestibile_bom') $$,
    $$ VALUES ('puo_gestire_bom'::text), ('motivo_non_gestibile_bom'::text) $$,
    '1) vw_articoli_dettaglio espone puo_gestire_bom e motivo_non_gestibile_bom'
);

-- =========================================================
-- Setup fixture: ART_TEST_BASE + ART_TEST_FALLBACK
-- =========================================================
-- ⛔ Gli articoli si COSTRUISCONO (2026-09-23). Fino a oggi questo file
--   pescava `ART_TEST_BASE` / `ART_TEST_FALLBACK`, che non stanno in nessun
--   changelog: sono due righe messe a mano su questa macchina (UUID …101 e
--   …102). Su un database ricostruito non esistono, e il file moriva nella
--   fixture — copertura zero, non parziale.
CREATE TEMP TABLE _t_ctx AS
SELECT
    dbops.fn_pgtap_crea_articolo('PGT-BOMDETT-A', p_is_composito => true)  AS art_a,
    dbops.fn_pgtap_crea_articolo('PGT-BOMDETT-B', p_is_composito => false,
                                 p_is_solo_componente => true)             AS art_b;

-- =========================================================
-- Scenario A) ART_TEST_BASE composito non solo componente -> CAN
-- =========================================================

SELECT is(
    (SELECT puo_gestire_bom FROM catalogo.vw_articoli_dettaglio
      WHERE id = (SELECT art_a FROM _t_ctx)),
    true,
    '2) Scenario A: puo_gestire_bom = true (is_composito AND NOT is_solo_componente)'
);
SELECT is(
    (SELECT motivo_non_gestibile_bom FROM catalogo.vw_articoli_dettaglio
      WHERE id = (SELECT art_a FROM _t_ctx)),
    NULL::text,
    '3) Scenario A: motivo_non_gestibile_bom = NULL'
);

-- =========================================================
-- Scenario B) ART_TEST_FALLBACK is_solo_componente=true -> motivo SOLO_COMPONENTE
-- (composito e solo componente insieme non esistono: li vieta il CHECK
-- chk_articoli_composito_non_solo_componente; resta il caso del solo componente
-- non composito, dove il motivo SOLO_COMPONENTE prevale su NON_COMPOSITO)
-- =========================================================

SELECT is(
    (SELECT puo_gestire_bom FROM catalogo.vw_articoli_dettaglio
      WHERE id = (SELECT art_b FROM _t_ctx)),
    false,
    '4) Scenario B: puo_gestire_bom = false (is_solo_componente=true)'
);
SELECT is(
    (SELECT motivo_non_gestibile_bom FROM catalogo.vw_articoli_dettaglio
      WHERE id = (SELECT art_b FROM _t_ctx)),
    'ARTICOLO_SOLO_COMPONENTE',
    '5) Scenario B: motivo = ARTICOLO_SOLO_COMPONENTE (prevale su NON_COMPOSITO)'
);

-- =========================================================
-- Scenario C) ART_TEST_FALLBACK NON composito e NON solo componente
-- -> motivo NON_COMPOSITO
-- =========================================================
UPDATE catalogo.articoli
   SET is_composito = false, is_solo_componente = false
 WHERE id = (SELECT art_b FROM _t_ctx);

SELECT is(
    (SELECT puo_gestire_bom FROM catalogo.vw_articoli_dettaglio
      WHERE id = (SELECT art_b FROM _t_ctx)),
    false,
    '6) Scenario C: puo_gestire_bom = false (NOT is_composito)'
);
SELECT is(
    (SELECT motivo_non_gestibile_bom FROM catalogo.vw_articoli_dettaglio
      WHERE id = (SELECT art_b FROM _t_ctx)),
    'ARTICOLO_NON_COMPOSITO',
    '7) Scenario C: motivo = ARTICOLO_NON_COMPOSITO'
);

SELECT * FROM finish();
ROLLBACK;
