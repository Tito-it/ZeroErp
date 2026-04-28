-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.vw_articoli_componenti_dettaglio campi capability
-- (Fase 2 BE 28-04-2026, migration 20260428-03).
--
-- Capability esposte:
--   puo_chiudersi          BOOLEAN  = (valido_al IS NULL)
--   data_min_chiusura      DATE     = valido_dal      [NULL se non chiudibile]
--   data_default_chiusura  DATE     = GREATEST(valido_dal, CURRENT_DATE)
--                                                    [NULL se non chiudibile]
--   motivo_non_chiudibile  TEXT     = 'RIGA_GIA_CHIUSA' [NULL se chiudibile]
--
-- Nota decisione (28-04-2026 opzione i): attivo (true/false) e'
-- ortogonale a puo_chiudersi. La verifica e' code-review only sullo
-- SQL della vista (nessun riferimento ad ac.attivo nei CASE WHEN).
--
-- Setup: 3 righe BoM con validita' / couple disgiunti per evitare
-- overlap su ex_articoli_componenti_no_overlap. Le 2 righe con
-- valido_al NULL (aperta + futura) usano couple (prodotto, componente)
-- distinti: forziamo is_composito=true su ART_TEST_BASE e
-- ART_TEST_FALLBACK e li scambiamo. ROLLBACK finale.
--
-- Indice test (1..12):
--   Riga APERTA (BASE/FALLBACK, [oggi-30, +inf)):
--     1. puo_chiudersi          = true
--     2. data_min_chiusura      = oggi-30
--     3. data_default_chiusura  = oggi (GREATEST con valido_dal passato)
--     4. motivo_non_chiudibile  = NULL
--   Riga CHIUSA (BASE/FALLBACK, [oggi-100, oggi-50]):
--     5. puo_chiudersi          = false
--     6. data_min_chiusura      = NULL
--     7. data_default_chiusura  = NULL
--     8. motivo_non_chiudibile  = 'RIGA_GIA_CHIUSA'
--   Riga FUTURA (FALLBACK/BASE invertito, [oggi+10, +inf)):
--     9. puo_chiudersi          = true
--    10. data_min_chiusura      = oggi+10
--    11. data_default_chiusura  = oggi+10 (GREATEST con valido_dal futuro)
--    12. motivo_non_chiudibile  = NULL
-- ------------------------------------------------------------

BEGIN;
SELECT plan(12);

-- =========================================================
-- Setup fixture
-- =========================================================
CREATE TEMP TABLE _t_bomcap AS
SELECT
    (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE')     AS art_base,
    (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_FALLBACK') AS art_fallback;

DO $pgtap$
BEGIN
    IF (SELECT art_base IS NULL OR art_fallback IS NULL FROM _t_bomcap) THEN
        RAISE EXCEPTION 'Seed articoli ART_TEST_BASE / ART_TEST_FALLBACK mancanti.';
    END IF;
END
$pgtap$;

-- Entrambi devono essere is_composito=true per ammettere INSERT
-- in articoli_componenti come prodotto. ROLLBACK ripristina seed.
UPDATE catalogo.articoli
   SET is_composito = true
 WHERE id IN ((SELECT art_base FROM _t_bomcap), (SELECT art_fallback FROM _t_bomcap));

CREATE TEMP TABLE _t_righe (scenario text, riga_id uuid);

-- Riga CHIUSA: BASE/FALLBACK, [oggi-100, oggi-50]
WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, partecipa_qta, obbligatorio,
        esposto_in_fattura, determina_qta_padre, valido_dal, valido_al, attivo
    )
    SELECT art_base, art_fallback, 1, false, true, false, false,
           (CURRENT_DATE - INTERVAL '100 days')::date,
           (CURRENT_DATE - INTERVAL '50  days')::date,
           true
      FROM _t_bomcap
    RETURNING id
)
INSERT INTO _t_righe (scenario, riga_id) SELECT 'chiusa', id FROM ins;

-- Riga APERTA: BASE/FALLBACK, [oggi-30, +inf). No overlap con la
-- chiusa (oggi-30 > oggi-50).
WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, partecipa_qta, obbligatorio,
        esposto_in_fattura, determina_qta_padre, valido_dal, valido_al, attivo
    )
    SELECT art_base, art_fallback, 1, false, true, false, false,
           (CURRENT_DATE - INTERVAL '30 days')::date,
           NULL,
           true
      FROM _t_bomcap
    RETURNING id
)
INSERT INTO _t_righe (scenario, riga_id) SELECT 'aperta', id FROM ins;

-- Riga FUTURA: couple invertito FALLBACK/BASE per evitare overlap
-- con la riga aperta sullo stesso couple, [oggi+10, +inf).
WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, partecipa_qta, obbligatorio,
        esposto_in_fattura, determina_qta_padre, valido_dal, valido_al, attivo
    )
    SELECT art_fallback, art_base, 1, false, true, false, false,
           (CURRENT_DATE + INTERVAL '10 days')::date,
           NULL,
           true
      FROM _t_bomcap
    RETURNING id
)
INSERT INTO _t_righe (scenario, riga_id) SELECT 'futura', id FROM ins;

-- =========================================================
-- Riga APERTA (1..4)
-- =========================================================
SELECT is(
    (SELECT puo_chiudersi
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'aperta')),
    true,
    '1) APERTA: puo_chiudersi = true (valido_al IS NULL)'
);
SELECT is(
    (SELECT data_min_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'aperta')),
    (CURRENT_DATE - INTERVAL '30 days')::date,
    '2) APERTA: data_min_chiusura = valido_dal (oggi-30)'
);
SELECT is(
    (SELECT data_default_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'aperta')),
    CURRENT_DATE,
    '3) APERTA: data_default_chiusura = GREATEST(valido_dal, today) = today'
);
SELECT is(
    (SELECT motivo_non_chiudibile
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'aperta')),
    NULL::text,
    '4) APERTA: motivo_non_chiudibile = NULL'
);

-- =========================================================
-- Riga CHIUSA (5..8)
-- =========================================================
SELECT is(
    (SELECT puo_chiudersi
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'chiusa')),
    false,
    '5) CHIUSA: puo_chiudersi = false (valido_al NOT NULL)'
);
SELECT is(
    (SELECT data_min_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'chiusa')),
    NULL::date,
    '6) CHIUSA: data_min_chiusura = NULL (riga non chiudibile)'
);
SELECT is(
    (SELECT data_default_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'chiusa')),
    NULL::date,
    '7) CHIUSA: data_default_chiusura = NULL'
);
SELECT is(
    (SELECT motivo_non_chiudibile
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'chiusa')),
    'RIGA_GIA_CHIUSA',
    '8) CHIUSA: motivo_non_chiudibile = RIGA_GIA_CHIUSA'
);

-- =========================================================
-- Riga FUTURA (9..12)
-- =========================================================
SELECT is(
    (SELECT puo_chiudersi
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'futura')),
    true,
    '9) FUTURA: puo_chiudersi = true (valido_al IS NULL anche se valido_dal > today)'
);
SELECT is(
    (SELECT data_min_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'futura')),
    (CURRENT_DATE + INTERVAL '10 days')::date,
    '10) FUTURA: data_min_chiusura = valido_dal (oggi+10)'
);
SELECT is(
    (SELECT data_default_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'futura')),
    (CURRENT_DATE + INTERVAL '10 days')::date,
    '11) FUTURA: data_default_chiusura = GREATEST(valido_dal, today) = valido_dal (futuro)'
);
SELECT is(
    (SELECT motivo_non_chiudibile
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'futura')),
    NULL::text,
    '12) FUTURA: motivo_non_chiudibile = NULL'
);

SELECT * FROM finish();
ROLLBACK;
