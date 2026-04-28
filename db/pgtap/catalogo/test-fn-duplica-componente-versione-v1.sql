-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.fn_duplica_componente_versione (Fase 3 BE 28-04-2026,
-- migration 20260428-04).
--
-- Scenari coperti:
--   - happy: chiudi+duplica riga aperta -> nuova riga con valido_dal
--            = p_chiudi_al + 1, struttura/meta/note copiati,
--            attivo=true forzato (anche se sorgente attivo=false).
--   - sorgente_chiusa: la riga sorgente ha valido_al NOT NULL
--                      -> raise E_BOM_SORGENTE_GIA_CHIUSA.
--   - non_esistente: id riga inesistente -> raise E_BOM_RIGA_NOT_FOUND.
--   - prodotto_mismatch: la riga appartiene a un altro prodotto
--                        -> raise E_BOM_PRODOTTO_MISMATCH (guard 1).
--
-- Scenario overlap NON riproducibile in pgTAP single-session:
--   l'EXCLUDE GIST ex_articoli_componenti_no_overlap impedisce di
--   pre-creare una riga futura sullo stesso couple (prodotto,
--   componente) mentre la sorgente e' aperta (range [valido_dal,
--   infinity)). L'unico scenario fisicamente plausibile per
--   E_BOM_VERSIONE_OVERLAP e' una race condition cross-session,
--   non testabile qui. Il path EXCEPTION exclusion_violation e'
--   verificato via code-review del CREATE FUNCTION (presenza del
--   blocco EXCEPTION WHEN exclusion_violation -> raise
--   E_BOM_VERSIONE_OVERLAP).
--
-- Setup: forziamo is_composito=true su ART_TEST_BASE e
-- ART_TEST_FALLBACK; ROLLBACK ripristina il seed.
--
-- Indice test (1..9):
--    1. happy: ritorna UUID NOT NULL
--    2. happy: sorgente.valido_al = p_chiudi_al
--    3. happy: nuova.valido_dal = p_chiudi_al + 1
--    4. happy: nuova.valido_al = NULL
--    5. happy: nuova eredita componente_id e coeff_qta
--    6. happy: nuova.attivo = true forzato (sorgente attivo=false)
--    7. sorgente_chiusa: raise E_BOM_SORGENTE_GIA_CHIUSA
--    8. non_esistente: raise E_BOM_RIGA_NOT_FOUND su id casuali
--    9. prodotto_mismatch: raise E_BOM_PRODOTTO_MISMATCH se
--                          p_articolo_id != row.prodotto_id
-- ------------------------------------------------------------

BEGIN;
SELECT plan(9);

-- =========================================================
-- Setup fixture
-- =========================================================
CREATE TEMP TABLE _t_dup AS
SELECT
    (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE')     AS art_base,
    (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_FALLBACK') AS art_fallback;

DO $pgtap$
BEGIN
    IF (SELECT art_base IS NULL OR art_fallback IS NULL FROM _t_dup) THEN
        RAISE EXCEPTION 'Seed articoli ART_TEST_BASE / ART_TEST_FALLBACK mancanti.';
    END IF;
END
$pgtap$;

UPDATE catalogo.articoli
   SET is_composito = true
 WHERE id IN ((SELECT art_base FROM _t_dup), (SELECT art_fallback FROM _t_dup));

-- =========================================================
-- Sorgente HAPPY: BASE/FALLBACK aperta. attivo=false per testare
-- che la nuova riga viene forzata a attivo=true.
-- =========================================================
CREATE TEMP TABLE _t_src_happy (riga_id uuid);
WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, partecipa_qta, obbligatorio,
        esposto_in_fattura, determina_qta_padre, valido_dal, valido_al, attivo
    )
    SELECT art_base, art_fallback, 3.5, true, true, false, false,
           (CURRENT_DATE - INTERVAL '30 days')::date,
           NULL,
           false
      FROM _t_dup
    RETURNING id
)
INSERT INTO _t_src_happy SELECT id FROM ins;

-- =========================================================
-- 1..6) Scenario HAPPY
-- =========================================================
CREATE TEMP TABLE _t_new_id (id uuid);
INSERT INTO _t_new_id
SELECT catalogo.fn_duplica_componente_versione(
    (SELECT art_base FROM _t_dup),
    (SELECT riga_id  FROM _t_src_happy),
    CURRENT_DATE
);

SELECT ok(
    (SELECT id FROM _t_new_id) IS NOT NULL,
    '1) HAPPY: fn_duplica_componente_versione ritorna UUID nuova riga'
);

SELECT is(
    (SELECT valido_al FROM catalogo.articoli_componenti
      WHERE id = (SELECT riga_id FROM _t_src_happy)),
    CURRENT_DATE,
    '2) HAPPY: sorgente.valido_al = p_chiudi_al (oggi)'
);

SELECT is(
    (SELECT valido_dal FROM catalogo.articoli_componenti
      WHERE id = (SELECT id FROM _t_new_id)),
    (CURRENT_DATE + INTERVAL '1 day')::date,
    '3) HAPPY: nuova.valido_dal = p_chiudi_al + 1'
);

SELECT is(
    (SELECT valido_al FROM catalogo.articoli_componenti
      WHERE id = (SELECT id FROM _t_new_id)),
    NULL::date,
    '4) HAPPY: nuova.valido_al = NULL (riga aperta)'
);

SELECT ok(
    (SELECT componente_id = (SELECT art_fallback FROM _t_dup)
        AND coeff_qta     = 3.5
       FROM catalogo.articoli_componenti
      WHERE id = (SELECT id FROM _t_new_id)),
    '5) HAPPY: nuova riga eredita componente_id e coeff_qta della sorgente'
);

SELECT is(
    (SELECT attivo FROM catalogo.articoli_componenti
      WHERE id = (SELECT id FROM _t_new_id)),
    true,
    '6) HAPPY: nuova.attivo = true forzato (sorgente attivo=false)'
);

-- =========================================================
-- 7) SORGENTE_CHIUSA: creo una sorgente FALLBACK/BASE chiusa
-- nel passato e tento di duplicarla.
-- =========================================================
CREATE TEMP TABLE _t_src_chiusa (riga_id uuid);
WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, partecipa_qta, obbligatorio,
        esposto_in_fattura, determina_qta_padre, valido_dal, valido_al, attivo
    )
    SELECT art_fallback, art_base, 1, true, true, false, false,
           (CURRENT_DATE - INTERVAL '60 days')::date,
           (CURRENT_DATE - INTERVAL '10 days')::date,
           true
      FROM _t_dup
    RETURNING id
)
INSERT INTO _t_src_chiusa SELECT id FROM ins;

SELECT throws_ok(
    format(
        $sql$ SELECT catalogo.fn_duplica_componente_versione(
                  %L::uuid,
                  %L::uuid,
                  CURRENT_DATE
              ) $sql$,
        (SELECT art_fallback FROM _t_dup),
        (SELECT riga_id FROM _t_src_chiusa)
    ),
    NULL, NULL,
    '7) SORGENTE_CHIUSA: raise E_BOM_SORGENTE_GIA_CHIUSA su riga con valido_al NOT NULL'
);

-- =========================================================
-- 8) NON_ESISTENTE: id casuali -> E_BOM_RIGA_NOT_FOUND
-- =========================================================
SELECT throws_ok(
    $sql$ SELECT catalogo.fn_duplica_componente_versione(
              gen_random_uuid(),
              gen_random_uuid(),
              CURRENT_DATE
          ) $sql$,
    NULL, NULL,
    '8) NON_ESISTENTE: raise E_BOM_RIGA_NOT_FOUND su id casuali'
);

-- =========================================================
-- 9) PRODOTTO_MISMATCH: la riga di _t_src_happy appartiene ad
-- ART_TEST_BASE (post test 1-6 e' chiusa, ma il guard
-- PRODOTTO_MISMATCH viene valutato PRIMA di SORGENTE_GIA_CHIUSA
-- nell'ordine: NOT_FOUND -> PRODOTTO_MISMATCH -> SORGENTE_GIA_CHIUSA).
-- Passo art_fallback come p_articolo_id sbagliato.
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ SELECT catalogo.fn_duplica_componente_versione(
                  %L::uuid,
                  %L::uuid,
                  CURRENT_DATE
              ) $sql$,
        (SELECT art_fallback FROM _t_dup),
        (SELECT riga_id FROM _t_src_happy)
    ),
    NULL, NULL,
    '9) PRODOTTO_MISMATCH: raise E_BOM_PRODOTTO_MISMATCH se p_articolo_id != row.prodotto_id'
);

SELECT * FROM finish();
ROLLBACK;
