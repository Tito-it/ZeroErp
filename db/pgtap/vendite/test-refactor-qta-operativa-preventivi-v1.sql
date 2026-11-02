-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: refactor quantita/qta_operativa su vendite.preventivi_righe.
--       Migrations 20260531-05 (factor nullable), 20260531-06 (qta_operativa
--       NOT NULL + quantita nullable + check spostato su sorgente).
--
-- Modello canonico: la SORGENTE e' qta_operativa, quantita e' DERIVATA dal
-- trigger script.trgfn_qta_from_operativa (UNA sola derivazione).
--
-- Indice test (1..10):
--   Struttura:
--   1) qta_operativa NOT NULL
--   2) quantita NULLABLE
--   3) chk_prevrighe_qta_operativa_nonzero presente
--   4) chk_prevrighe_quantita_pos ASSENTE (rimosso)
--   5) factor_to_base NULLABLE (no default 1)
--   Fixture:
--   6) riferimenti minimi + preventivo DRAFT creati
--   Comportamento:
--   7) factor=1: qta_operativa=2 -> quantita=2 (derivazione singola, no factor^2)
--   8) factor!=1 (art ...0101, uom 2, factor 6): qta_operativa=2, factor NULL
--      -> quantita=12 (regressione smoke 8a: NON 72) e factor_to_base snapshot=6
--   9) qta_operativa negativa ammessa (resi/storni) -> lives, quantita negativa
--  10) qta_operativa=0 -> check_violation 23514
--  11) qta_operativa NULL -> E_QTA_MISSING dal trigger (messaggio parlante)
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

SELECT plan(11);

-- ============================================================
-- 1) qta_operativa NOT NULL
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.columns
            WHERE table_schema='vendite' AND table_name='preventivi_righe'
              AND column_name='qta_operativa' AND is_nullable='NO'),
    '1) preventivi_righe.qta_operativa NOT NULL'
);

-- ============================================================
-- 2) quantita NULLABLE
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.columns
            WHERE table_schema='vendite' AND table_name='preventivi_righe'
              AND column_name='quantita' AND is_nullable='YES'),
    '2) preventivi_righe.quantita NULLABLE (derivata dal trigger)'
);

-- ============================================================
-- 3) chk_prevrighe_qta_operativa_nonzero presente
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM pg_constraint c
             JOIN pg_class r ON r.oid=c.conrelid
             JOIN pg_namespace n ON n.oid=r.relnamespace
            WHERE n.nspname='vendite' AND r.relname='preventivi_righe'
              AND c.conname='chk_prevrighe_qta_operativa_nonzero'),
    '3) chk_prevrighe_qta_operativa_nonzero presente (check sulla sorgente)'
);

-- ============================================================
-- 4) chk_prevrighe_quantita_pos ASSENTE
-- ============================================================
SELECT ok(
    NOT EXISTS(SELECT 1 FROM pg_constraint c
             JOIN pg_class r ON r.oid=c.conrelid
             JOIN pg_namespace n ON n.oid=r.relnamespace
            WHERE n.nspname='vendite' AND r.relname='preventivi_righe'
              AND c.conname='chk_prevrighe_quantita_pos'),
    '4) chk_prevrighe_quantita_pos rimosso (negativi ammessi)'
);

-- ============================================================
-- 5) factor_to_base NULLABLE
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.columns
            WHERE table_schema='vendite' AND table_name='preventivi_righe'
              AND column_name='factor_to_base' AND is_nullable='YES'),
    '5) preventivi_righe.factor_to_base NULLABLE (abilita snapshot da mapping)'
);

-- ============================================================
-- Fixture: riferimenti + preventivo DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_qta_refs AS
SELECT
    (SELECT ba.id FROM anagrafiche.billing_account ba
      WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      ORDER BY ba.id LIMIT 1) AS billing_account_id,
    (SELECT ba.utility_id FROM anagrafiche.billing_account ba
      WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      ORDER BY ba.id LIMIT 1) AS utility_id,
    (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
      WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
    -- articolo factor=1: attivo, non composito, diverso da ...0101 e senza mapping factor!=1
    (SELECT a.id FROM catalogo.articoli a
      WHERE a.attivo IS TRUE AND a.is_composito = FALSE
        AND a.id <> '00000000-0000-0000-0000-000000000101'::uuid
        AND NOT EXISTS (SELECT 1 FROM catalogo.articoli_uom_operativa m
                         WHERE m.articolo_id = a.id AND m.factor_to_base <> 1)
      ORDER BY a.id LIMIT 1) AS articolo_f1_id,
    -- articolo factor!=1 (seed ...0101 + uom_id 2, factor 6), se presente e attivo/valido
    (SELECT m.articolo_id FROM catalogo.articoli_uom_operativa m
       JOIN catalogo.articoli a ON a.id = m.articolo_id
      WHERE m.uom_id = 2 AND m.factor_to_base = 6 AND m.attivo IS TRUE
        AND a.attivo IS TRUE
        AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
        AND (m.valido_al  IS NULL OR m.valido_al  >= script.fn_data_operativa())
      LIMIT 1) AS articolo_f6_id,
    (SELECT s.id FROM config.stati_doc_preventivi s
      WHERE s.codice='DRAFT' AND s.attivo IS TRUE LIMIT 1) AS stato_draft_id,
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
      ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
    -- iva > 0: il trigger z90 ricalcola_totali chiama fn_get_aliquota_iva(iva_id)
    (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
      ORDER BY i.id LIMIT 1) AS iva_id;

INSERT INTO vendite.preventivi (
    numero, rev,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, emittente_fiscale_id, storicizza, meta)
SELECT 'PGTAP-QTA-PREV', 0,
       r.billing_account_id, r.istanza_utility_id, r.utility_id,
       DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
       r.stato_draft_id, DATE '2080-01-01', r.emittente_fiscale_id, false,
       jsonb_build_object('test_scope','pgtap_qta_refactor')
  FROM tmp_qta_refs r
 WHERE r.billing_account_id IS NOT NULL AND r.stato_draft_id IS NOT NULL
   AND r.articolo_f1_id IS NOT NULL;

SELECT ok(
    EXISTS(SELECT 1 FROM vendite.preventivi WHERE numero='PGTAP-QTA-PREV'),
    '6) fixture: preventivo DRAFT creato + articolo factor=1 disponibile'
);

-- ============================================================
-- 7-9) Comportamenti positivi: INSERT top-level con RETURNING in tmp_qta_res
-- ============================================================
CREATE TEMP TABLE tmp_qta_res (label text, quantita numeric, qta_operativa numeric, factor_to_base numeric);

-- 7) factor=1: qta_operativa=2 -> quantita=2
WITH ins AS (
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
    SELECT p.id, r.articolo_f1_id, r.iva_id, 10, 2
      FROM vendite.preventivi p, tmp_qta_refs r
     WHERE p.numero='PGTAP-QTA-PREV'
    RETURNING quantita, qta_operativa, factor_to_base
)
INSERT INTO tmp_qta_res SELECT 'f1', quantita, qta_operativa, factor_to_base FROM ins;

-- 8) factor!=1: qta_operativa=2, uom 2, factor NULL -> quantita=12, factor snapshot=6
WITH ins AS (
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa, uom_operativa_id)
    SELECT p.id, r.articolo_f6_id, r.iva_id, 10, 2, 2
      FROM vendite.preventivi p, tmp_qta_refs r
     WHERE p.numero='PGTAP-QTA-PREV' AND r.articolo_f6_id IS NOT NULL
    RETURNING quantita, qta_operativa, factor_to_base
)
INSERT INTO tmp_qta_res SELECT 'f6', quantita, qta_operativa, factor_to_base FROM ins;

-- 9) qta_operativa negativa -> ammessa, quantita negativa
WITH ins AS (
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
    SELECT p.id, r.articolo_f1_id, r.iva_id, 10, -3
      FROM vendite.preventivi p, tmp_qta_refs r
     WHERE p.numero='PGTAP-QTA-PREV'
    RETURNING quantita, qta_operativa, factor_to_base
)
INSERT INTO tmp_qta_res SELECT 'neg', quantita, qta_operativa, factor_to_base FROM ins;

SELECT is(
    (SELECT quantita FROM tmp_qta_res WHERE label='f1'),
    2::numeric,
    '7) factor=1: qta_operativa=2 -> quantita=2 (derivazione singola)'
);

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_qta_res WHERE label='f6')
    THEN skip('8) mapping factor!=1 (art ...0101/uom 2) non disponibile')
    ELSE ok(
        (SELECT quantita = 12 AND factor_to_base = 6 FROM tmp_qta_res WHERE label='f6'),
        '8) factor!=1: qta_operativa=2 -> quantita=12 (NON 72) e factor snapshot=6 (regressione 8a)'
    )
END;

SELECT is(
    (SELECT quantita FROM tmp_qta_res WHERE label='neg'),
    -3::numeric,
    '9) qta_operativa negativa ammessa -> quantita derivata negativa'
);

-- ============================================================
-- 10) qta_operativa=0 -> check_violation 23514
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, prezzo_unitario, qta_operativa)
          VALUES (%s, %L::uuid, 10, 0)$$,
        (SELECT id FROM vendite.preventivi WHERE numero='PGTAP-QTA-PREV'),
        (SELECT articolo_f1_id FROM tmp_qta_refs)
    ),
    '23514', NULL,
    '10) qta_operativa=0 -> chk_prevrighe_qta_operativa_nonzero (23514)'
);

-- ============================================================
-- 11) qta_operativa NULL -> E_QTA_MISSING dal trigger (P0001), prima del NOT NULL
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, prezzo_unitario, qta_operativa)
          VALUES (%s, %L::uuid, 10, NULL)$$,
        (SELECT id FROM vendite.preventivi WHERE numero='PGTAP-QTA-PREV'),
        (SELECT articolo_f1_id FROM tmp_qta_refs)
    ),
    'P0001', NULL,
    '11) qta_operativa NULL -> E_QTA_MISSING dal trigger (messaggio parlante)'
);

SELECT * FROM finish();
ROLLBACK;
