-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   il tipo dell'origine non ha piu' un CHECK col suo vocabolario: e' una FK verso
--   config.sorgenti(codice_interno) (G-3). Il test 8 cerca la FK, il 12 che nessun CHECK
--   enumeri i codici; l'11 cerca il predicato col codice della sorgente, OFFERTA_COMMERCIALE.
-- pgTAP test per Zero ERP
--
-- Test: estensione modello DB-ORD (db-brief-ordini-vendita §5, §6, §6.A).
-- Scope: verifica strutturale (introspezione, no fixture) di:
--   - fix CHECK chk_ordini_v_r_qta_pos (era sul prezzo, ora su quantita)
--   - CHECK co-presenza UoM operativa
--   - estensione E: agente_soggetto_ruolo_id (FK soggetti_ruoli, nullable)
--   - estensione A1: documento_origine_tipo/_id (varchar+FK verso le sorgenti, nullable,
--     SENZA UNIQUE -> piu' ordini da una stessa origine)
--
-- Indice test (1..12):
--   1.  chk_ordini_v_r_qta_pos referenzia la QUANTITA' (quantita)
--   2.  chk_ordini_v_r_qta_pos NON referenzia il prezzo (anti-regressione bug)
--   3.  CHECK co-presenza UoM operativa presente su ordini_righe
--   4.  agente_soggetto_ruolo_id presente e nullable
--   5.  FK fk_ordini_v_agente_ruolo -> anagrafiche.soggetti_ruoli
--   6.  documento_origine_tipo presente e nullable
--   7.  documento_origine_id presente, bigint, nullable
--   8.  FK fk_ordini_documento_origine_tipo_sorgenti verso config.sorgenti(codice_interno)
--   9.  CHECK chk_ordini_documento_origine_copres presente (co-presenza tipo<->id)
--   10. Nessuna UNIQUE PIENA su documento_origine_* (A1: piu' ordini da una origine)
--   11. Esiste la UNIQUE PARZIALE limitata a OFFERTA_COMMERCIALE (1:1 offerta->ordine)
--   12. Nessun CHECK enumera i codici del tipo origine (il vocabolario e' config.sorgenti)
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

-- 8. Il vocabolario del tipo: FK verso le sorgenti (rev 2026-10-19, lotto 2b)
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_ordini_documento_origine_tipo_sorgenti'
           AND conrelid = 'vendite.ordini'::regclass
           AND contype = 'f'
           AND confrelid = 'config.sorgenti'::regclass
           AND pg_get_constraintdef(oid) LIKE '%(documento_origine_tipo) REFERENCES %(codice_interno)%'
    ),
    '8. FK fk_ordini_documento_origine_tipo_sorgenti verso config.sorgenti(codice_interno)'
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

-- 10-11. Le UNIQUE su documento_origine_*
-- 🔴 PRECISATO IL 2026-08-18.
--   Il test pretendeva ZERO indici unici su `documento_origine_*` — la scelta
--   A1 del `20260603-13`, «piu' ordini da una stessa origine», per consentire i
--   riordini. Falliva con have=1, e non e' una regressione: il `20260607-07` ha
--   invertito quella scelta **per la sola origine OFFERTA** (ratificato Tid,
--   2026-06-07), perche' un'offerta non ha righe materializzate — e' una
--   condizione quadro atomica, quindi l'1:1 e' la sua natura e non un ripiego.
--   PREVENTIVO non e' toccato: il suo modello e' lo split per riga.
--
--   ⚠️ Il test non si rovescia e non si cancella: si RENDE PRECISO. «Nessuna
--   UNIQUE» era troppo, «una UNIQUE qualsiasi» sarebbe troppo poco — passerebbe
--   anche se qualcuno togliesse il `WHERE` e vincolasse pure i preventivi, che
--   e' esattamente il danno che A1 voleva evitare. Le due meta' della regola
--   vanno guardate separatamente, ed e' per questo che qui i test sono due.
SELECT is(
    (
        SELECT COUNT(*)::INTEGER FROM pg_indexes
         WHERE schemaname = 'vendite' AND tablename = 'ordini'
           AND indexdef ILIKE '%documento_origine%'
           AND indexdef ILIKE '%unique%'
           AND indexdef NOT ILIKE '%where%'
    ),
    0,
    '10. Nessuna UNIQUE PIENA su documento_origine_* (A1: piu ordini da una stessa origine)'
);

SELECT is(
    (
        SELECT COUNT(*)::INTEGER FROM pg_indexes
         WHERE schemaname = 'vendite' AND tablename = 'ordini'
           AND indexdef ILIKE '%documento_origine%'
           AND indexdef ILIKE '%unique%'
           AND indexdef ILIKE '%where%'
           AND indexdef ILIKE '%''OFFERTA_COMMERCIALE''%'
    ),
    1,
    '11. Esiste la UNIQUE parziale limitata a OFFERTA_COMMERCIALE (1:1 offerta->ordine, 20260607-07)'
);

-- 12. Nessun CHECK enumera i codici del tipo origine (rev 2026-10-19, lotto 2b):
--     un tipo nuovo e' una riga di config.sorgenti, non un CHECK da riscrivere (G-3).
SELECT is_empty(
    $$SELECT c.conname
        FROM pg_constraint c
       WHERE c.conrelid = 'vendite.ordini'::regclass
         AND c.contype = 'c'
         AND pg_get_constraintdef(c.oid) LIKE '%documento_origine_tipo%'
         AND pg_get_constraintdef(c.oid) ~ '''[A-Z_]+'''$$,
    '12. nessun CHECK enumera i codici del tipo origine (il vocabolario e'' config.sorgenti)'
);

SELECT * FROM finish();
ROLLBACK;
