-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.vw_articoli_uom_operativa_dettaglio (Fase 6 BE
-- 28-04-2026, migration 20260428-06).
--
-- Capability esposte:
--   puo_eliminarsi          BOOLEAN  = NOT is_base
--   motivo_non_eliminabile  TEXT     = 'UOM_BASE_NON_ELIMINABILE' [NULL se eliminabile]
--
-- Setup: usiamo ART_TEST_BASE come articolo prodotto e creiamo 2
-- righe articoli_uom_operativa nel test:
--   - is_base=true   (UoM base, non eliminabile)
--   - is_base=false  (UoM operativa secondaria, eliminabile)
-- ROLLBACK ripristina lo stato.
--
-- Indice test (1..6):
--   1. presenza vista
--   2. UoM BASE: puo_eliminarsi = false
--   3. UoM BASE: motivo_non_eliminabile = 'UOM_BASE_NON_ELIMINABILE'
--   4. UoM SECONDARIA: puo_eliminarsi = true
--   5. UoM SECONDARIA: motivo_non_eliminabile = NULL
--   6. denormalizzazione articolo_codice/uom_codice presenti
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

SELECT plan(6);

-- =========================================================
-- 1) Presenza vista
-- =========================================================
SELECT has_view(
    'catalogo', 'vw_articoli_uom_operativa_dettaglio',
    '1) catalogo.vw_articoli_uom_operativa_dettaglio presente'
);

-- =========================================================
-- Setup fixture: un articolo COSTRUITO + 2 UoM del seed
-- =========================================================
-- ⛔ L'articolo si costruisce (2026-09-23). Fino a oggi il file pescava
--   `ART_TEST_BASE`, che non sta in nessun changelog — e' una riga messa a
--   mano su questa macchina — e su un database ricostruito moriva in fixture.
-- ⭐ Su un articolo NUOVO cade anche la «pulizia preventiva» che serviva a
--   togliere di mezzo le righe del seed: un articolo appena costruito non ha
--   nessuna riga operativa, quindi le due che seguono sono le sue uniche —
--   che e' esattamente la precondizione che il file voleva.
-- ⚠️ Le UoM invece si SCELGONO: sono seed di 80_data, ci sono anche su un
--   database ricostruito. `ORDER BY` esplicito, e la coppia si sceglie una
--   volta sola.
CREATE TEMP TABLE _t_ctx AS
SELECT
    dbops.fn_pgtap_crea_articolo('PGT-UOMOP-CAP')                       AS art_id,
    (SELECT id FROM catalogo.unita_misura ORDER BY id LIMIT 1)          AS uom_a_id,
    (SELECT id FROM catalogo.unita_misura ORDER BY id OFFSET 1 LIMIT 1) AS uom_b_id;

DO $pgtap$
BEGIN
    IF (SELECT uom_a_id IS NULL OR uom_b_id IS NULL FROM _t_ctx) THEN
        RAISE EXCEPTION 'Seed mancante: servono almeno 2 UoM in catalogo.unita_misura';
    END IF;
END
$pgtap$;

CREATE TEMP TABLE _t_uom_riga (kind text, uom_op_id bigint);

-- Riga BASE: non si scrive, C'E' GIA'. Un articolo nasce con la sua riga
-- operativa di base (`is_base = true`, fattore 1) sulla UoM dell'articolo:
-- la scrive un trigger. Scriverla di nuovo violerebbe
-- `uq_artuomop_articolo_uom` — ed e' il motivo per cui la vecchia fixture
-- doveva fare una «pulizia preventiva» prima di inserirla.
INSERT INTO _t_uom_riga (kind, uom_op_id)
SELECT 'base', auo.id
  FROM catalogo.articoli_uom_operativa auo
  JOIN _t_ctx c ON c.art_id = auo.articolo_id
 WHERE auo.is_base;

-- Riga SECONDARIA (uom_b)
WITH ins AS (
    INSERT INTO catalogo.articoli_uom_operativa (
        articolo_id, uom_id, is_base, factor_to_base, attivo
    )
    SELECT art_id, uom_b_id, false, 6, true FROM _t_ctx
    RETURNING id
)
INSERT INTO _t_uom_riga (kind, uom_op_id) SELECT 'secondaria', id FROM ins;

-- =========================================================
-- 2..3) Riga BASE
-- =========================================================
SELECT is(
    (SELECT puo_eliminarsi
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'base')),
    false,
    '2) UoM BASE: puo_eliminarsi = false'
);
SELECT is(
    (SELECT motivo_non_eliminabile
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'base')),
    'UOM_BASE_NON_ELIMINABILE',
    '3) UoM BASE: motivo_non_eliminabile = UOM_BASE_NON_ELIMINABILE'
);

-- =========================================================
-- 4..5) Riga SECONDARIA
-- =========================================================
SELECT is(
    (SELECT puo_eliminarsi
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'secondaria')),
    true,
    '4) UoM SECONDARIA: puo_eliminarsi = true (NOT is_base)'
);
SELECT is(
    (SELECT motivo_non_eliminabile
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'secondaria')),
    NULL::text,
    '5) UoM SECONDARIA: motivo_non_eliminabile = NULL'
);

-- =========================================================
-- 6) Denormalizzazione: articolo_codice e uom_codice valorizzati
-- =========================================================
SELECT ok(
    -- ⚠️ Il codice atteso e' quello dell'articolo COSTRUITO, non una stringa
    --   scritta a mano: la vista deve denormalizzare cio' che c'e'.
    (SELECT v.articolo_codice = 'PGT-UOMOP-CAP'
        AND v.uom_codice IS NOT NULL
       FROM catalogo.vw_articoli_uom_operativa_dettaglio v
      WHERE v.id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'base')),
    '6) Denormalizzazione: articolo_codice e uom_codice valorizzati per la riga BASE'
);

SELECT * FROM finish();
ROLLBACK;
