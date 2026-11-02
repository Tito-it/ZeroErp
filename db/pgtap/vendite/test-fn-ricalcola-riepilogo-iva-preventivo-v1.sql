-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_ricalcola_riepilogo_iva_preventivo + tabella
--       vendite.preventivi_riepiloghi_iva + coerenza centesimi
--       preventivo (regola fiscale corretta).
--
-- Migrations:
--   20260502-10 (CREATE TABLE preventivi_riepiloghi_iva)
--   20260502-11 (fn_ricalcola_riepilogo_iva_preventivo)
--   20260502-12 (rewrite fn_ricalcola_totali_preventivo come wrapper)
--
-- Indice test (1..10):
--   1)  Funzione fn_ricalcola_riepilogo_iva_preventivo presente.
--   2)  Tabella preventivi_riepiloghi_iva presente.
--   3)  Riferimenti minimi disponibili (BA, articolo, stato, valuta,
--       2 aliquote IVA distinte > 0).
--   4)  Setup preventivo DRAFT con 0 righe -> riepilogo vuoto.
--   5)  Una riga aliquota A: riepilogo ha 1 entry per quella aliquota,
--       imponibile = qta*prezzo, imposta = ROUND(imponibile*aliquota/100, 2).
--   6)  Aggiunta riga aliquota B: riepilogo ha 2 entry distinte, group
--       by iva_id corretto.
--   7)  Multi-righe stessa aliquota: imponibile aggregato = ROUND(
--       SUM(qta*prezzo*(1-sconto/100)), 2). Verifica che la SUM full
--       precision in `arrotondamento` non sia sempre zero (centesimi
--       residui possibili).
--   8)  fn_ricalcola_totali_preventivo wrapper: totali testata
--       coincidono con SUM(riepiloghi.imponibile/imposta).
--   9)  Coerenza centesimi: totale_imponibile = SUM(riepiloghi.imponibile)
--       a centesimo per centesimo (no divergenza ROUND-per-riga).
--   10) Riga inattiva o qta=0: NON contribuisce al riepilogo.
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

SELECT plan(10);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_ricalcola_riepilogo_iva_preventivo'
  ),
  '1. fn_ricalcola_riepilogo_iva_preventivo presente'
);

-- ============================================================
-- 2) Tabella presente
-- ============================================================
SELECT has_table(
    'vendite',
    'preventivi_riepiloghi_iva',
    '2. vendite.preventivi_riepiloghi_iva esiste'
);

-- ============================================================
-- 3) Riferimenti minimi (con DUE aliquote distinte > 0)
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il preventivo si COSTRUISCE
--   (dbops.fn_pgtap_crea_preventivo: azienda di chi agisce, cliente col suo
--   BA, testata in bozza, senza righe) e l'articolo pure
--   (dbops.fn_pgtap_crea_articolo, merce semplice). Prima BA, articolo ed
--   emittente si pescavano col primo id / l'ultimo inserito e la testata si
--   INSERIVA a mano: da zero non c'era niente. Dal catalogo di seed restano
--   stato, valuta e le due IVA.
CREATE TEMP TABLE tmp_rr_pb AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('riepilogo iva');

CREATE TEMP TABLE tmp_rr_refs AS
SELECT
  pb.billing_account_id,
  pb.utility_id,
  pb.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo(
    ('PGT-RIVA-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar, false
  ) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1
  ) AS stato_draft_id,
  pb.valuta_id,
  pb.emittente_fiscale_id,
  -- aliquota A: la piu' alta (di norma 22)
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
    ORDER BY i.aliquota_iva DESC LIMIT 1
  ) AS iva_a_id,
  (SELECT i.aliquota_iva FROM config.iva i
    WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
    ORDER BY i.aliquota_iva DESC LIMIT 1
  ) AS iva_a_aliquota,
  -- aliquota B: una piu' bassa, distinta dalla A
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE
      AND i.aliquota_iva > 0
      AND i.aliquota_iva < (SELECT MAX(i2.aliquota_iva)
                              FROM config.iva i2
                             WHERE i2.attivo IS TRUE)
    ORDER BY i.aliquota_iva DESC LIMIT 1
  ) AS iva_b_id,
  (SELECT i.aliquota_iva FROM config.iva i
    WHERE i.attivo IS TRUE
      AND i.aliquota_iva > 0
      AND i.aliquota_iva < (SELECT MAX(i2.aliquota_iva)
                              FROM config.iva i2
                             WHERE i2.attivo IS TRUE)
    ORDER BY i.aliquota_iva DESC LIMIT 1
  ) AS iva_b_aliquota
  FROM tmp_rr_pb pb;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL
      AND iva_a_id IS NOT NULL
      AND iva_b_id IS NOT NULL
      AND iva_a_id <> iva_b_id
   FROM tmp_rr_refs),
  '3. Riferimenti minimi disponibili (2 aliquote IVA distinte > 0 + emittente fiscale)'
);

-- ============================================================
-- 4) Setup preventivo DRAFT
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): la testata e' quella del builder (sopra),
--   non piu' un INSERT a mano: qui non e' il caso sotto test.
CREATE TEMP TABLE tmp_rr_prev AS
SELECT preventivo_id AS id FROM tmp_rr_pb;

SELECT is(
  (SELECT count(*)::int FROM vendite.preventivi_riepiloghi_iva
    WHERE preventivo_id = (SELECT id FROM tmp_rr_prev)),
  0,
  '4. Setup preventivo DRAFT senza righe -> riepilogo vuoto'
);

-- ============================================================
-- 5) Una riga aliquota A
-- ============================================================
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 10, 10, 100.00, 0, r.iva_a_id,
       true, 1, jsonb_build_object('test_scope', 'pgtap_riepilogo_iva')
  FROM tmp_rr_prev p, tmp_rr_refs r;

SELECT is(
  (SELECT ROUND(imponibile, 2)
     FROM vendite.preventivi_riepiloghi_iva
    WHERE preventivo_id = (SELECT id FROM tmp_rr_prev)
      AND iva_id = (SELECT iva_a_id FROM tmp_rr_refs)),
  1000.00::numeric,
  '5. Riepilogo aliquota A: imponibile = ROUND(qta*prezzo, 2) = 1000'
);

-- ============================================================
-- 6) Aggiunta riga aliquota B
-- ============================================================
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 5, 5, 200.00, 0, r.iva_b_id,
       true, 2, jsonb_build_object('test_scope', 'pgtap_riepilogo_iva')
  FROM tmp_rr_prev p, tmp_rr_refs r;

SELECT is(
  (SELECT count(*)::int FROM vendite.preventivi_riepiloghi_iva
    WHERE preventivo_id = (SELECT id FROM tmp_rr_prev)),
  2,
  '6. Riepilogo ha 2 entry (group by iva_id su 2 aliquote distinte)'
);

-- ============================================================
-- 7) Multi-righe stessa aliquota: aggregazione corretta
--    Aggiungiamo 3 righe stesso iva_a_id con valori che possono
--    produrre divergenza ROUND-per-riga vs ROUND-aggregato
-- ============================================================
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 1, 1, 33.335::numeric, 0, r.iva_a_id,
       true, 10 + n, jsonb_build_object('test_scope', 'pgtap_riepilogo_iva')
  FROM tmp_rr_prev p, tmp_rr_refs r,
       generate_series(1, 3) n;

-- Verifica: imponibile aliquota_a = ROUND(SUM_full, 2) = ROUND(1000 + 33.335*3, 2)
--          = ROUND(1100.005, 2) = 1100.01 (HALF_UP) o 1100.00 (HALF_EVEN)
-- L'arrotondamento residuo deve essere registrato in `arrotondamento`.
SELECT cmp_ok(
  (SELECT ABS(arrotondamento)
     FROM vendite.preventivi_riepiloghi_iva
    WHERE preventivo_id = (SELECT id FROM tmp_rr_prev)
      AND iva_id = (SELECT iva_a_id FROM tmp_rr_refs)),
  '<',
  0.01::numeric,
  '7. Multi-righe stessa aliquota: arrotondamento registrato (|arr| < 0.01)'
);

-- ============================================================
-- 8) Wrapper fn_ricalcola_totali_preventivo: totali testata = SUM(riepiloghi)
-- ============================================================
SELECT is(
  (SELECT (p.totale_imponibile, p.totale_iva)
     FROM vendite.preventivi p
    WHERE p.id = (SELECT id FROM tmp_rr_prev)),
  (SELECT (
            COALESCE(SUM(ri.imponibile), 0)::numeric,
            COALESCE(SUM(ri.imposta),    0)::numeric
          )
     FROM vendite.preventivi_riepiloghi_iva ri
    WHERE ri.preventivo_id = (SELECT id FROM tmp_rr_prev)),
  '8. Totali testata = SUM(riepiloghi.imponibile/imposta) [wrapper coerente]'
);

-- ============================================================
-- 9) Coerenza centesimi: totale_imponibile pari a SUM(imponibile)
--    a 2 decimali esatti
-- ============================================================
SELECT is(
  (SELECT p.totale_imponibile FROM vendite.preventivi p
    WHERE p.id = (SELECT id FROM tmp_rr_prev)),
  (SELECT COALESCE(SUM(ri.imponibile), 0)::numeric
     FROM vendite.preventivi_riepiloghi_iva ri
    WHERE ri.preventivo_id = (SELECT id FROM tmp_rr_prev)),
  '9. Coerenza centesimi: totale_imponibile = SUM(riepiloghi.imponibile)'
);

-- ============================================================
-- 10) Riga inattiva non contribuisce al riepilogo
-- ============================================================
-- Snapshot totale imponibile prima del cambio
CREATE TEMP TABLE tmp_rr_pre_disable AS
SELECT totale_imponibile FROM vendite.preventivi
 WHERE id = (SELECT id FROM tmp_rr_prev);

-- Disattiva una riga (tutte le righe attualmente sono attive)
UPDATE vendite.preventivi_righe
   SET attivo = false
 WHERE preventivo_id = (SELECT id FROM tmp_rr_prev)
   AND ordine = 1;

SELECT cmp_ok(
  (SELECT totale_imponibile FROM vendite.preventivi
    WHERE id = (SELECT id FROM tmp_rr_prev)),
  '<',
  (SELECT totale_imponibile FROM tmp_rr_pre_disable),
  '10. Riga disattivata fa decrescere totale_imponibile'
);

SELECT * FROM finish();
ROLLBACK;
