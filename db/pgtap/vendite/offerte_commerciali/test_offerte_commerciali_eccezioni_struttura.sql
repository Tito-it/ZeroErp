-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: struttura vendite.offerte_commerciali_eccezioni (Step 3).
--       Mirror fedele di contratti_righe: enum tipo_eccezione_contratto,
--       5 CHECK semantici, 2 UNIQUE parziali, esclusione campi I4.
--
-- Indice test (1..10):
--   1)  Tabella vendite.offerte_commerciali_eccezioni esiste
--   2)  tipo_eccezione usa enum vendite.tipo_eccezione_contratto (B3)
--   3)  fonte_quantita_attesa obbligatoria sulle righe che non sono ESCLUSIONE (CHECK)
--   4)  FK fk_offerte_commerciali_eccezioni_erogazione_fonte presente (rev 2026-10-07)
--   5)  i CHECK della matrice erogazione/fonte sono ritirati
--   6)  CHECK chk_offerte_eccezioni_coerenza_canone presente
--   7)  la FK lega la coppia (tipo_erogazione, fonte_quantita_attesa)
--   8)  CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione presente
--   9)  UNIQUE parziale uq_offerte_eccezioni_one_eccezione_per_articolo presente
--  10)  Campi I4 assenti: stato_approvazione_prezzo e pratica_approvazione_prezzo_id
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(10);

-- ============================================================
-- 1) Tabella esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali_eccezioni'
    ),
    '1) vendite.offerte_commerciali_eccezioni esiste'
);

-- ============================================================
-- 2) tipo_eccezione usa enum vendite.tipo_eccezione_contratto (B3)
--    Il riuso dello stesso enum rende il push 1:1 triviale.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM information_schema.columns c
          JOIN pg_attribute a   ON a.attname = c.column_name
          JOIN pg_class t       ON t.oid = a.attrelid
          JOIN pg_namespace nt  ON nt.oid = t.relnamespace
          JOIN pg_type ty       ON ty.oid = a.atttypid
          JOIN pg_namespace nty ON nty.oid = ty.typnamespace
         WHERE c.table_schema = 'vendite'
           AND c.table_name   = 'offerte_commerciali_eccezioni'
           AND c.column_name  = 'tipo_eccezione'
           AND ty.typname     = 'tipo_eccezione_contratto'
           AND nty.nspname    = 'vendite'
    ),
    '2) tipo_eccezione usa enum vendite.tipo_eccezione_contratto (B3)'
);

-- ============================================================
-- 3) fonte_quantita_attesa obbligatoria, tranne sull'ESCLUSIONE
-- ============================================================
-- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R1): il NOT
--   NULL scende al CHECK chk_offerte_eccezioni_fonte_per_tipo_eccezione,
--   specchio del contratto. Un'esclusione non ha fonte.
SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
        AND c.conname  = 'chk_offerte_eccezioni_fonte_per_tipo_eccezione'),
    'CHECK (((tipo_eccezione = ''ESCLUSIONE''::vendite.tipo_eccezione_contratto) OR (fonte_quantita_attesa IS NOT NULL)))',
    '3) fonte_quantita_attesa obbligatoria sulle righe che non sono ESCLUSIONE (specchio contratti_righe)'
);

-- ============================================================
-- 4) FK fk_offerte_commerciali_eccezioni_erogazione_fonte su config.erogazioni_fonti
--    ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.7, giro B1):
--    erano i CHECK chk_offerte_eccezioni_tipo_erog / _fonte_qta /
--    _coerenza_fonte_erogazione, ritirati da 20261007-54. La matrice e' un dato.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
         WHERE c.conrelid  = 'vendite.offerte_commerciali_eccezioni'::regclass
           AND c.conname   = 'fk_offerte_commerciali_eccezioni_erogazione_fonte'
           AND c.contype   = 'f'
           AND c.confrelid = 'config.erogazioni_fonti'::regclass
    ),
    '4) FK fk_offerte_commerciali_eccezioni_erogazione_fonte su config.erogazioni_fonti presente'
);

-- ============================================================
-- 5) I tre CHECK della matrice non ci sono piu': la sede e' una (la FK)
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM pg_constraint c
         WHERE c.conrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
           AND c.conname IN ('chk_offerte_eccezioni_tipo_erog',
                             'chk_offerte_eccezioni_fonte_qta',
                             'chk_offerte_eccezioni_coerenza_fonte_erogazione')
    ),
    '5) i CHECK della matrice erogazione/fonte sono ritirati (la FK e'' la sede unica)'
);

-- ============================================================
-- 6) CHECK chk_offerte_eccezioni_coerenza_canone
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_eccezioni'
           AND c.conname = 'chk_offerte_eccezioni_coerenza_canone'
           AND c.contype = 'c'
    ),
    '6) CHECK chk_offerte_eccezioni_coerenza_canone presente (I3)'
);

-- ============================================================
-- 7) La FK lega la COPPIA (tipo_erogazione, fonte_quantita_attesa), nell'ordine
--    del vocabolario (rev 2026-10-07: era il CHECK della coerenza)
-- ============================================================
SELECT is(
    (SELECT array_agg(a.attname ORDER BY k.ord)
       FROM pg_constraint c
       CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
       JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
      WHERE c.conrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
        AND c.conname  = 'fk_offerte_commerciali_eccezioni_erogazione_fonte'),
    ARRAY['tipo_erogazione', 'fonte_quantita_attesa']::name[],
    '7) la FK lega la coppia (tipo_erogazione, fonte_quantita_attesa)'
);

-- ============================================================
-- 8) CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_eccezioni'
           AND c.conname = 'chk_offerte_eccezioni_prezzo_per_tipo_eccezione'
           AND c.contype = 'c'
    ),
    '8) CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione presente (I3)'
);

-- ============================================================
-- 9) UNIQUE parziale per (offerta_id, articolo_id) su OVERRIDE/ESCLUSIONE
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE schemaname = 'vendite'
           AND tablename  = 'offerte_commerciali_eccezioni'
           AND indexname  = 'uq_offerte_eccezioni_one_eccezione_per_articolo'
    ),
    '9) UNIQUE parziale uq_offerte_eccezioni_one_eccezione_per_articolo presente'
);

-- ============================================================
-- 10) Campi I4 PRESENTI: stato_approvazione_prezzo + pratica_approvazione_prezzo_id
--
-- ⭐ ROVESCIATO IL 2026-08-24, e la storia va lasciata scritta perche' e' una
--    decisione presa due volte in senso opposto — non un errore.
--
--    Il 2026-05-24 (changeSet 20260524-05) la tabella nasce apposta SENZA quei
--    due campi: «il flusso di approvazione prezzo e' solo sui contratti, non
--    sull'offerta pre-negoziazione». Questa asserzione presidiava quella scelta.
--
--    Il 2026-06-01 (changeSet 20260601-01) la scelta e' stata RIBALTATA, con
--    la sua ragione: le eccezioni COMPONENTI quei campi ce li avevano gia'
--    (20260526-22), e senza la simmetria sulla riga un OVERRIDE/AGGIUNTA non
--    composito non aveva dove registrare lo stato L3 — ne' il push poteva
--    trasportarlo 1:1 a contratti_righe. Riferimento: refactor-prezzi-db §3.1.
--
--    ⚠️ Il test e' rimasto indietro di dodici settimane senza che nessuno lo
--    sapesse: questo file vive in una sottocartella, e fino al 2026-08-24 i
--    presidi pgTAP guardavano un livello solo — brief-db-pgtap-rami-ciechi.
--
--    ⭐ L'asserzione non si cancella, si ROVESCIA: quello che oggi vale la pena
--    presidiare e' la SIMMETRIA — se qualcuno togliesse quei campi dalla riga
--    lasciandoli sulle componenti, il push tornerebbe a perdere lo stato L3.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'offerte_commerciali_eccezioni'
        AND column_name IN ('stato_approvazione_prezzo', 'pratica_approvazione_prezzo_id')),
    2,
    '10) Campi I4 presenti sulla riga: la simmetria con le componenti regge (20260601-01)'
);

SELECT * FROM finish();
ROLLBACK;
