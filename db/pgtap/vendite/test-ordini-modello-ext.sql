-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: estensione modello DB-ORD (db-brief-ordini-vendita §5, §6, §6.A).
-- Scope: verifica strutturale (introspezione, no fixture) di:
--   - fix CHECK chk_ordini_v_r_qta_pos (era sul prezzo, ora su quantita)
--   - CHECK co-presenza UoM operativa
--   - estensione E: agente_soggetto_ruolo_id (FK soggetti_ruoli, nullable)
--   - estensione A1: documento_origine_tipo/_id (varchar+CHECK, nullable,
--     SENZA UNIQUE -> piu' ordini da una stessa origine)
--
-- Indice test (1..11):
--   1.  chk_ordini_v_r_qta_pos referenzia la QUANTITA' (quantita)
--   2.  chk_ordini_v_r_qta_pos NON referenzia il prezzo (anti-regressione bug)
--   3.  CHECK co-presenza UoM operativa presente su ordini_righe
--   4.  agente_soggetto_ruolo_id presente e nullable
--   5.  FK fk_ordini_v_agente_ruolo -> anagrafiche.soggetti_ruoli
--   6.  documento_origine_tipo presente e nullable
--   7.  documento_origine_id presente, bigint, nullable
--   8.  CHECK chk_ordini_documento_origine_tipo presente (vocabolario)
--   9.  CHECK chk_ordini_documento_origine_copres presente (co-presenza tipo<->id)
--   10. NESSUNA UNIQUE su documento_origine_* (anti-A2: piu' ordini da una origine)
--   11. Il CHECK del tipo origine enumera PREVENTIVO/OFFERTA
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

-- 1. chk_ordini_v_r_qta_pos referenzia quantita
SELECT ok(
    (
        SELECT pg_get_constraintdef(c.oid)
          FROM pg_constraint c
         WHERE c.conname = 'chk_ordini_v_r_qta_pos'
           AND c.conrelid = 'vendite.ordini_righe'::regclass
    ) LIKE '%quantita%',
    '1. chk_ordini_v_r_qta_pos vincola la quantita (quantita > 0)'
);

-- 2. chk_ordini_v_r_qta_pos NON referenzia il prezzo (anti-regressione bug)
SELECT ok(
    (
        SELECT pg_get_constraintdef(c.oid)
          FROM pg_constraint c
         WHERE c.conname = 'chk_ordini_v_r_qta_pos'
           AND c.conrelid = 'vendite.ordini_righe'::regclass
    ) NOT LIKE '%prezzo%',
    '2. chk_ordini_v_r_qta_pos NON vincola piu il prezzo (bug corretto)'
);

-- 3. CHECK co-presenza UoM operativa
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'chk_ordini_v_r_uom_qta_operativa_copres'
           AND conrelid = 'vendite.ordini_righe'::regclass
    ),
    '3. CHECK co-presenza UoM operativa presente su ordini_righe'
);

-- 4. agente_soggetto_ruolo_id presente e nullable
SELECT is(
    (
        SELECT is_nullable FROM information_schema.columns
         WHERE table_schema = 'vendite' AND table_name = 'ordini'
           AND column_name = 'agente_soggetto_ruolo_id'
    ),
    'YES',
    '4. agente_soggetto_ruolo_id presente e nullable'
);

-- 5. FK agente -> soggetti_ruoli
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
         WHERE c.conname = 'fk_ordini_v_agente_ruolo'
           AND c.conrelid = 'vendite.ordini'::regclass
           AND c.confrelid = 'anagrafiche.soggetti_ruoli'::regclass
           AND c.contype = 'f'
    ),
    '5. FK fk_ordini_v_agente_ruolo -> anagrafiche.soggetti_ruoli'
);

-- 6. documento_origine_tipo presente e nullable
SELECT is(
    (
        SELECT is_nullable FROM information_schema.columns
         WHERE table_schema = 'vendite' AND table_name = 'ordini'
           AND column_name = 'documento_origine_tipo'
    ),
    'YES',
    '6. documento_origine_tipo presente e nullable'
);

-- 7. documento_origine_id presente, bigint, nullable
SELECT is(
    (
        SELECT data_type || '/' || is_nullable FROM information_schema.columns
         WHERE table_schema = 'vendite' AND table_name = 'ordini'
           AND column_name = 'documento_origine_id'
    ),
    'bigint/YES',
    '7. documento_origine_id presente, bigint, nullable'
);

-- 8. CHECK vocabolario tipo
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'chk_ordini_documento_origine_tipo'
           AND conrelid = 'vendite.ordini'::regclass
    ),
    '8. CHECK chk_ordini_documento_origine_tipo presente'
);

-- 9. CHECK co-presenza tipo <-> id
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'chk_ordini_documento_origine_copres'
           AND conrelid = 'vendite.ordini'::regclass
    ),
    '9. CHECK chk_ordini_documento_origine_copres presente'
);

-- 10. NESSUNA UNIQUE su documento_origine_* (anti-A2)
SELECT is(
    (
        SELECT COUNT(*)::INTEGER FROM pg_indexes
         WHERE schemaname = 'vendite' AND tablename = 'ordini'
           AND indexdef ILIKE '%documento_origine%'
           AND indexdef ILIKE '%unique%'
    ),
    0,
    '10. Nessuna UNIQUE su documento_origine_* (piu ordini da una stessa origine)'
);

-- 11. Il CHECK tipo enumera PREVENTIVO/OFFERTA
SELECT ok(
    (
        SELECT pg_get_constraintdef(c.oid)
          FROM pg_constraint c
         WHERE c.conname = 'chk_ordini_documento_origine_tipo'
           AND c.conrelid = 'vendite.ordini'::regclass
    ) LIKE '%PREVENTIVO%',
    '11. chk_ordini_documento_origine_tipo enumera il vocabolario (PREVENTIVO/OFFERTA)'
);

SELECT * FROM finish();
ROLLBACK;
