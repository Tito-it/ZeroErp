-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_ricalcola_totali_preventivo
--       + trigger trgfn_preventivi_righe_ricalcola_totali
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) Funzione presente
-- 2) Trigger STATEMENT presenti su preventivi_righe (ins/upd/dlt)
-- 3) Riferimenti minimi disponibili
-- 4) Setup preventivo DRAFT
-- 5) Insert riga: trigger aggiorna totali testata
-- 6) Ricalcolo corretto con sconto
-- 7) Ricalcolo corretto con IVA
-- 8) Delete riga: totali tornano a 0
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

SELECT plan(8);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_ricalcola_totali_preventivo'
  ),
  '1. fn_ricalcola_totali_preventivo presente'
);

-- ============================================================
-- 2) Trigger STATEMENT presenti su preventivi_righe
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) = 3
   FROM pg_trigger t
   JOIN pg_class c ON c.oid = t.tgrelid
   JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'vendite'
     AND c.relname = 'preventivi_righe'
     AND t.tgname IN (
       'trg_preventivi_righe_z90_ricalcola_totali_ins',
       'trg_preventivi_righe_z90_ricalcola_totali_upd',
       'trg_preventivi_righe_z90_ricalcola_totali_dlt'
     )
  ),
  '2. Trigger STATEMENT ricalcolo presenti (ins/upd/dlt)'
);

-- ============================================================
-- 3) Riferimenti minimi
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il preventivo si COSTRUISCE
--   (dbops.fn_pgtap_crea_preventivo: azienda di chi agisce, cliente col suo
--   BA, testata in bozza, senza righe) e l'articolo pure
--   (dbops.fn_pgtap_crea_articolo, merce semplice). Prima BA, articolo ed
--   emittente si pescavano col primo id / l'ultimo inserito e la testata si
--   INSERIVA a mano: da zero non c'era niente. Dal catalogo di seed restano
--   stato, valuta e IVA. La testata resta la stessa di prima nel 4.
CREATE TEMP TABLE tmp_rc_pb AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('ricalcola totali');

CREATE TEMP TABLE tmp_rc_refs AS
WITH iva_scelta AS (
  -- Una sola estrazione: id e aliquota vengono per forza dalla stessa riga.
  SELECT i.id, i.aliquota_iva
    FROM config.iva i
   WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
   ORDER BY i.id
   LIMIT 1
)
SELECT
  pb.billing_account_id,
  pb.utility_id,
  pb.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo(
    ('PGT-RC-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar, false
  ) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1
  ) AS stato_draft_id,
  pb.valuta_id,
  pb.emittente_fiscale_id,
  -- ⚠️ L'IVA si sceglie UNA volta sola, e da li' si proiettano id e aliquota.
  --   Prima erano due sotto-select indipendenti sullo stesso insieme: niente
  --   garantiva che pescassero la stessa riga, e il test avrebbe calcolato i
  --   totali attesi con l'aliquota di un'IVA diversa da quella messa in riga.
  --   Con due aliquote positive in catalogo il difetto e' gia' possibile oggi.
  (SELECT id           FROM iva_scelta) AS iva_id,
  (SELECT aliquota_iva FROM iva_scelta) AS iva_aliquota
  FROM tmp_rc_pb pb;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL
      AND iva_id IS NOT NULL
      AND iva_aliquota > 0
   FROM tmp_rc_refs),
  '3. Riferimenti minimi disponibili (con IVA > 0 + emittente fiscale)'
);

-- ============================================================
-- 4) Setup preventivo DRAFT (totali iniziali = 0)
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): la testata e' quella del builder (sopra),
--   non piu' un INSERT a mano: qui non e' il caso sotto test.
CREATE TEMP TABLE tmp_rc_prev AS
SELECT p.id, p.uid, p.numero
  FROM vendite.preventivi p
 WHERE p.id = (SELECT preventivo_id FROM tmp_rc_pb);

SELECT ok(
  (SELECT totale_imponibile = 0 AND totale_iva = 0 AND totale_documento = 0
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rc_prev)),
  '4. Setup preventivo DRAFT con totali = 0'
);

-- ============================================================
-- 5) Insert riga senza sconto: trigger aggiorna totali
--    qta=10, prezzo=100, sconto=0, IVA da refs
--    imponibile atteso: 10 * 100 = 1000
-- ============================================================
CREATE TEMP TABLE tmp_rc_riga1 AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, qta_operativa, quantita,
    prezzo_unitario, sconto_percentuale, iva_id,
    attivo, ordine, meta
  )
  SELECT
    p.id, r.articolo_id, 10, 10, 100.00, 0, r.iva_id,
    true, 1, jsonb_build_object('test_scope', 'pgtap_ricalcola')
  FROM tmp_rc_prev p, tmp_rc_refs r
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT totale_imponibile = 1000.00
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rc_prev)),
  '5. Trigger ricalcolo: imponibile = 1000 dopo insert riga (qta=10 * prezzo=100)'
);

-- ============================================================
-- 6) Insert riga con sconto 20%: ricalcolo corretto
--    qta=5, prezzo=200, sconto=20% -> importo_riga = 5*200*0.8 = 800
--    totale imponibile atteso: 1000 + 800 = 1800
-- ============================================================
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, ordine, meta
)
SELECT
  p.id, r.articolo_id, 5, 5, 200.00, 20, r.iva_id,
  true, 2, jsonb_build_object('test_scope', 'pgtap_ricalcola')
FROM tmp_rc_prev p, tmp_rc_refs r;

SELECT ok(
  (SELECT totale_imponibile = 1800.00
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rc_prev)),
  '6. Ricalcolo con sconto 20%: imponibile = 1800 (1000 + 800)'
);

-- ============================================================
-- 7) Verifica IVA calcolata
--    totale_iva = 1800 * aliquota_iva / 100
-- ============================================================
SELECT ok(
  (SELECT totale_iva = ROUND(1800.00 * r.iva_aliquota / 100, 2)
   FROM vendite.preventivi p2, tmp_rc_refs r
   WHERE p2.id = (SELECT id FROM tmp_rc_prev)),
  '7. IVA calcolata correttamente su imponibile 1800'
);

-- ============================================================
-- 8) Delete riga1: totali ricalcolati (solo riga2 rimane)
--    imponibile atteso: 800 (solo riga con sconto)
-- ============================================================
DELETE FROM vendite.preventivi_righe
WHERE id = (SELECT id FROM tmp_rc_riga1);

SELECT ok(
  (SELECT totale_imponibile = 800.00
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rc_prev)),
  '8. Delete riga: imponibile ricalcolato a 800 (solo riga2)'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
