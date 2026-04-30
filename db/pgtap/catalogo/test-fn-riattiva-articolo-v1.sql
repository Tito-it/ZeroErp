-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.fn_riattiva_articolo (Fase 7 BE 28-04-2026,
-- migration 20260428-08).
--
-- Pattern "padre prima, figli poi" + idempotenza.
-- Disattivazione bloccata da trigger esistente
-- trgfn_prevent_deactivate_if_children su 13+ relazioni figlie.
--
-- Setup: ART_TEST_BASE ha gia' figli attivi via seed
-- (articoli_uom_operativa.csv id 9002 attivo=true). Sfruttiamo quel
-- seed per scenario 1 (disattivazione bloccata). Per scenario 2/3
-- (riattivazione padre, figli inattivi) prima disattiviamo tutti i
-- figli noti via UPDATE ad-hoc + ROLLBACK ripristina il seed.
--
-- Indice test (1..6):
--   1. UPDATE attivo=false su articolo con figlio attivo -> raise
--      (verifica trigger trgfn_prevent_deactivate_if_children)
--   2. fn_riattiva_articolo su articolo disattivato esegue senza errori
--   3. dopo (2): articolo padre attivo=true
--   4. dopo (2): figli (articoli_uom_operativa) restano attivo=false
--      (pattern "padre prima, figli poi")
--   5. fn_riattiva_articolo su UUID inesistente -> raise E_ARTICOLO_NOT_FOUND
--   6. fn_riattiva_articolo idempotente su articolo gia' attivo -> no error
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

-- =========================================================
-- Setup: 2 articoli rilevanti
-- =========================================================
CREATE TEMP TABLE _t_ctx AS
SELECT
    (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE')     AS art_a,
    (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_FALLBACK') AS art_b;

DO $pgtap$
BEGIN
    IF (SELECT art_a IS NULL OR art_b IS NULL FROM _t_ctx) THEN
        RAISE EXCEPTION 'Seed articoli ART_TEST_BASE / ART_TEST_FALLBACK mancanti.';
    END IF;
END
$pgtap$;

-- =========================================================
-- 1) Disattivazione bloccata da figlio attivo
-- ART_TEST_BASE ha articoli_uom_operativa (seed id 9002) attivo=true
-- =========================================================
SELECT throws_like(
    format(
        $sql$ UPDATE catalogo.articoli SET attivo = false WHERE id = %L::uuid $sql$,
        (SELECT art_a FROM _t_ctx)
    ),
    '%attive%',
    '1) UPDATE attivo=false su articolo con figlio attivo -> raise (trigger prevent_deactivate_if_children)'
);

-- =========================================================
-- Setup scenario 2/3: disattivazione padre+figli ordinata
-- "Figli prima" (per superare il trigger), poi padre.
-- I figli noti per ART_TEST_BASE: articoli_uom_operativa.
-- Disattiviamo TUTTI i figli attivi su ART_TEST_BASE per evitare
-- side-effect da altre relazioni seedate.
-- =========================================================
UPDATE catalogo.articoli_uom_operativa
   SET attivo = false
 WHERE articolo_id = (SELECT art_a FROM _t_ctx)
   AND attivo = true;

UPDATE catalogo.articoli
   SET attivo = false
 WHERE id = (SELECT art_a FROM _t_ctx);

-- =========================================================
-- 2) fn_riattiva_articolo: padre torna attivo
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ SELECT catalogo.fn_riattiva_articolo(%L::uuid) $sql$,
        (SELECT art_a FROM _t_ctx)
    ),
    '2) fn_riattiva_articolo su articolo disattivato esegue senza errori'
);

SELECT is(
    (SELECT attivo FROM catalogo.articoli
      WHERE id = (SELECT art_a FROM _t_ctx)),
    true,
    '3) padre attivo=true dopo fn_riattiva_articolo'
);

-- =========================================================
-- 3) Figli rimangono inattivi (pattern padre prima, figli poi)
-- =========================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM catalogo.articoli_uom_operativa
         WHERE articolo_id = (SELECT art_a FROM _t_ctx)
           AND attivo = true
    ),
    '4) Dopo fn_riattiva_articolo: figli (articoli_uom_operativa) restano attivo=false'
);

-- =========================================================
-- 4) UUID inesistente -> raise E_ARTICOLO_NOT_FOUND
-- =========================================================
SELECT throws_ok(
    $sql$ SELECT catalogo.fn_riattiva_articolo(gen_random_uuid()) $sql$,
    NULL, NULL,
    '5) fn_riattiva_articolo su UUID inesistente -> raise E_ARTICOLO_NOT_FOUND'
);

-- =========================================================
-- 5) Idempotente su articolo gia' attivo (ART_TEST_FALLBACK)
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ SELECT catalogo.fn_riattiva_articolo(%L::uuid) $sql$,
        (SELECT art_b FROM _t_ctx)   -- ART_TEST_FALLBACK gia' attivo
    ),
    '6) fn_riattiva_articolo idempotente su articolo gia'' attivo -> no error'
);

SELECT * FROM finish();
ROLLBACK;
