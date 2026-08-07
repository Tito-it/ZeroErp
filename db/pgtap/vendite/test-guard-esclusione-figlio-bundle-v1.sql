-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: §6.1 Guard ESCLUSIONE su figlio bundle vietata
--       Migration: 20260516-05
--
-- Indice test (1..5):
--   Struttura:
--   1)  Funzione trgfn_contratti_righe_guard_esclusione_figlio_bundle presente
--   2)  Trigger trg_contratti_righe_a10_guard_esclusione_figlio_bundle_ins_upd presente
--
--   Comportamento (COND: skip se nessun bundle in listini_righe_componenti):
--   3)  ESCLUSIONE su figlio bundle nel listino del contratto → raise P0001
--   4)  ESCLUSIONE su padre bundle (articolo padre composito) → ammessa
--   5)  ESCLUSIONE su articolo standalone (non figlio bundle) → ammessa
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

-- ============================================================
-- Setup fixture
-- ============================================================

CREATE TEMP TABLE tmp_esc_ctx AS
SELECT
    ba.id                   AS ba_id,
    ba.istanza_utility_id,
    ba.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
    (SELECT id FROM catalogo.unita_misura WHERE attivo = TRUE ORDER BY id LIMIT 1) AS uom_id
  FROM anagrafiche.billing_account ba
 ORDER BY ba.id
 LIMIT 1;

-- Trova un bundle con componenti attivi in una versione operativa.
-- Se non esiste alcun bundle nel DB, i test 3-5 vengono skippati.
CREATE TEMP TABLE tmp_esc_bundle AS
SELECT
    lrc.articolo_figlio_id  AS figlio_id,
    lrc.articolo_padre_id   AS padre_id,
    lv.listino_id           AS listino_id,
    lv.id                   AS listino_versione_id
  FROM vendite.listini_righe_componenti lrc
  JOIN vendite.listini_versioni lv ON lv.id = lrc.listino_versione_id
 WHERE lrc.attivo  = TRUE
   AND lrc.validita @> CURRENT_DATE
   AND lv.attivo   = TRUE
   AND lv.stato    IN ('ATTIVA', 'CHIUSA')
   AND lv.validita @> CURRENT_DATE
 ORDER BY lrc.id
 LIMIT 1;

-- Articolo standalone nel listino del bundle (non è figlio di bundle)
CREATE TEMP TABLE tmp_esc_standalone AS
SELECT lr.articolo_id
  FROM vendite.listini_righe lr
 WHERE lr.listino_versione_id = (SELECT listino_versione_id FROM tmp_esc_bundle LIMIT 1)
   AND lr.attivo              = TRUE
   AND NOT EXISTS (
       SELECT 1 FROM vendite.listini_righe_componenti lrc2
        WHERE lrc2.listino_versione_id = lr.listino_versione_id
          AND lrc2.articolo_figlio_id  = lr.articolo_id
          AND lrc2.attivo              = TRUE
   )
 LIMIT 1;

-- Contratto DRAFT con il listino del bundle (per test 3, 4, 5)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, listino_id, valido_dal, valido_al)
SELECT 'PGTAP_ESC_CNT', c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, (SELECT listino_id FROM tmp_esc_bundle LIMIT 1),
       '2073-01-01'::date, '2073-12-31'::date
  FROM tmp_esc_ctx c
 WHERE (SELECT listino_id FROM tmp_esc_bundle LIMIT 1) IS NOT NULL;

-- ============================================================
SELECT plan(5);
-- ============================================================

-- ============================================================
-- 1) trgfn_contratti_righe_guard_esclusione_figlio_bundle presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'trgfn_contratti_righe_guard_esclusione_figlio_bundle'
    ),
    '1) Funzione trgfn_contratti_righe_guard_esclusione_figlio_bundle presente'
);

-- ============================================================
-- 2) Trigger presente su vendite.contratti_righe
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'contratti_righe'
           AND t.tgname  = 'trg_contratti_righe_a10_guard_esclusione_figlio_bundle_ins_upd'
           AND NOT t.tgisinternal
    ),
    '2) Trigger trg_contratti_righe_a10_guard_esclusione_figlio_bundle_ins_upd presente'
);

-- ============================================================
-- 3) ESCLUSIONE su figlio bundle → raise P0001
--    COND: skip se nessun bundle disponibile nel DB
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_esc_bundle)
         OR NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_ESC_CNT')
    THEN skip('Nessun bundle in listini_righe_componenti o fixture non creata - skip', 1)
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe(
                contratto_id, articolo_id, tipo_eccezione, qta_operativa)
              SELECT c.id, %L::uuid, 'ESCLUSIONE', 1.00
                FROM vendite.contratti c WHERE c.numero = 'PGTAP_ESC_CNT'$$,
            (SELECT figlio_id FROM tmp_esc_bundle LIMIT 1)
        ),
        'P0001',
        NULL,
        '3) ESCLUSIONE su figlio bundle → raise E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA'
    )
END;

-- ============================================================
-- 4) ESCLUSIONE su padre bundle → ammessa (LIVES_OK)
--    Il padre composito non è un figlio, l'ESCLUSIONE è valida
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_esc_bundle)
         OR NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_ESC_CNT')
    THEN skip('Nessun bundle disponibile o fixture non creata - skip', 1)
    ELSE lives_ok(
        format(
            $$INSERT INTO vendite.contratti_righe(
                contratto_id, articolo_id, tipo_eccezione, qta_operativa)
              SELECT c.id, %L::uuid, 'ESCLUSIONE', 1.00
                FROM vendite.contratti c WHERE c.numero = 'PGTAP_ESC_CNT'$$,
            (SELECT padre_id FROM tmp_esc_bundle LIMIT 1)
        ),
        '4) ESCLUSIONE su padre bundle → ammessa (padre non è figlio)'
    )
END;

-- ============================================================
-- 5) ESCLUSIONE su articolo standalone (non figlio bundle) → ammessa
--    COND: skip se nessun articolo standalone trovato nel listino
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_esc_standalone)
         OR NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_ESC_CNT')
    THEN skip('Nessun standalone trovato nel listino o fixture non creata - skip', 1)
    ELSE lives_ok(
        format(
            $$INSERT INTO vendite.contratti_righe(
                contratto_id, articolo_id, tipo_eccezione, qta_operativa)
              SELECT c.id, %L::uuid, 'ESCLUSIONE', 1.00
                FROM vendite.contratti c WHERE c.numero = 'PGTAP_ESC_CNT'$$,
            (SELECT articolo_id FROM tmp_esc_standalone LIMIT 1)
        ),
        '5) ESCLUSIONE su standalone non-figlio → ammessa'
    )
END;

SELECT * FROM finish();
ROLLBACK;
