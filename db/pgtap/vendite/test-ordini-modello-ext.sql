-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- ⚠️ rev 2026-11-07 (brief-db-sorgente-documento-e-riga, giro T.5, 20261106-96): documento_origine_*
--   e i loro vincoli sono ritirati; da dove nasce l'ordine lo dice la provenienza (sorgente_*). I test
--   6-12 guardano la provenienza con le stesse due meta' della regola A1: nessuna UNIQUE piena (piu'
--   ordini da uno stesso preventivo), una UNIQUE parziale sulla sola offerta (1:1). Piano invariato.
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
--   - estensione A1, oggi sulla provenienza (sorgente_*): tipo con FK verso le sorgenti,
--     nullable, SENZA UNIQUE piena -> piu' ordini da una stessa origine
--
-- Indice test (1..12):
--   1.  chk_ordini_v_r_qta_pos referenzia la QUANTITA' (quantita)
--   2.  chk_ordini_v_r_qta_pos NON referenzia il prezzo (anti-regressione bug)
--   3.  CHECK co-presenza UoM operativa presente su ordini_righe
--   4.  agente_soggetto_ruolo_id presente e nullable
--   5.  FK fk_ordini_v_agente_ruolo -> anagrafiche.soggetti_ruoli
--   6.  documento_origine_tipo e documento_origine_id non ci sono piu' (giro T.5)
--   7.  sorgente_tipo_id, sorgente_id, sorgente_uid presenti e nullable
--   8.  FK fk_ordini_v_sorgente_tipo verso config.sorgenti(id)
--   9.  CHECK chk_ordini_sorgente_forma presente (il tipo con una sola chiave)
--   10. Nessuna UNIQUE PIENA su sorgente_* (A1: piu' ordini da una origine)
--   11. Esiste la UNIQUE PARZIALE limitata a OFFERTA_COMMERCIALE (1:1 offerta->ordine)
--   12. Nessun vincolo ne' indice dell'ordine nomina piu' documento_origine
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

-- 6. Le colonne parallele sono ritirate (giro T.5, 20261106-96)
SELECT is(
    (
        SELECT COUNT(*)::INTEGER FROM information_schema.columns
         WHERE table_schema = 'vendite' AND table_name = 'ordini'
           AND column_name IN ('documento_origine_tipo', 'documento_origine_id')
    ),
    0,
    '6. documento_origine_tipo e documento_origine_id non ci sono piu'' (la provenienza e'' sorgente_*)'
);

-- 7. La provenienza: le tre colonne, nullable (un ordine puo' nascere da solo)
SELECT is(
    (
        SELECT string_agg(column_name || '/' || is_nullable, ',' ORDER BY column_name)
          FROM information_schema.columns
         WHERE table_schema = 'vendite' AND table_name = 'ordini'
           AND column_name IN ('sorgente_tipo_id', 'sorgente_id', 'sorgente_uid')
    ),
    'sorgente_id/YES,sorgente_tipo_id/YES,sorgente_uid/YES',
    '7. sorgente_tipo_id, sorgente_id, sorgente_uid presenti e nullable'
);

-- 8. Il vocabolario del tipo: FK verso le sorgenti
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_ordini_v_sorgente_tipo'
           AND conrelid = 'vendite.ordini'::regclass
           AND contype = 'f'
           AND confrelid = 'config.sorgenti'::regclass
           AND pg_get_constraintdef(oid) LIKE '%(sorgente_tipo_id) REFERENCES %(id)%'
    ),
    '8. FK fk_ordini_v_sorgente_tipo verso config.sorgenti(id)'
);

-- 9. CHECK di forma: nessuna provenienza, o il tipo con una chiave sola
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'chk_ordini_sorgente_forma'
           AND conrelid = 'vendite.ordini'::regclass
           AND contype = 'c'
    ),
    '9. CHECK chk_ordini_sorgente_forma presente'
);

-- 10-11. Le UNIQUE sulla provenienza
-- 🔴 PRECISATO IL 2026-08-18, e passato alla provenienza il 2026-11-07 (giro T.5).
--   La scelta A1 del `20260603-13` («piu' ordini da una stessa origine», per i
--   riordini) e la sua eccezione per la sola OFFERTA (`20260607-07`, ratificata
--   da Tid il 2026-06-07: un'offerta e' una condizione quadro atomica, l'1:1 e' la
--   sua natura) valgono oggi su sorgente_*. PREVENTIVO non e' toccato: il suo
--   modello e' lo split per riga.
--
--   ⚠️ Le due meta' della regola si guardano separatamente: «una UNIQUE qualsiasi»
--   passerebbe anche se qualcuno togliesse il `WHERE` e vincolasse pure i
--   preventivi, che e' il danno che A1 voleva evitare.
SELECT is(
    (
        SELECT COUNT(*)::INTEGER FROM pg_indexes
         WHERE schemaname = 'vendite' AND tablename = 'ordini'
           AND indexdef ILIKE '%sorgente_%'
           AND indexdef ILIKE '%unique%'
           AND indexdef NOT ILIKE '%where%'
    ),
    0,
    '10. Nessuna UNIQUE PIENA su sorgente_* (A1: piu ordini da una stessa origine)'
);

-- Il predicato nomina l'id di OFFERTA_COMMERCIALE nel catalogo (D-8): si confronta
-- col catalogo, non con un numero scritto qui.
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM pg_index i
          JOIN pg_class c ON c.oid = i.indexrelid
         WHERE i.indrelid = 'vendite.ordini'::regclass
           AND i.indisunique
           AND i.indpred IS NOT NULL
           AND pg_get_indexdef(i.indexrelid) ILIKE '%sorgente_%'
           AND pg_get_expr(i.indpred, i.indrelid) LIKE
               '%(sorgente_tipo_id = ' || (SELECT s.id FROM config.sorgenti s
                                           WHERE s.codice_interno = 'OFFERTA_COMMERCIALE')::text || ')%'
    ),
    1,
    '11. Esiste la UNIQUE parziale limitata a OFFERTA_COMMERCIALE (1:1 offerta->ordine, sulla provenienza)'
);

-- 12. Niente dell'ordine nomina piu' la colonna parallela (giro T.5)
SELECT is_empty(
    $$SELECT c.conname::text
        FROM pg_constraint c
       WHERE c.conrelid = 'vendite.ordini'::regclass
         AND (c.conname ~ 'documento_origine' OR pg_get_constraintdef(c.oid) ~ 'documento_origine')
      UNION ALL
      SELECT i.indexrelid::regclass::text
        FROM pg_index i
       WHERE i.indrelid = 'vendite.ordini'::regclass
         AND pg_get_indexdef(i.indexrelid) ~ 'documento_origine'$$,
    '12. nessun vincolo ne'' indice dell''ordine nomina piu'' documento_origine'
);

SELECT * FROM finish();
ROLLBACK;
