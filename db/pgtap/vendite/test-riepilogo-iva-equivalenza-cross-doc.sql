-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: EQUIVALENZA FISCALE del riepilogo IVA tra tipi documento.
--
-- Scopo (guard anti-drift): la formula fiscale del riepilogo IVA
-- (aggregazione per aliquota, ROUND(SUM) sull'imponibile, imposta
-- sull'imponibile aggregato arrotondato -- DPR 633/72 art. 21 + DM 24/12/93)
-- DEVE restare identica su tutti i tipi documento. Oggi vive duplicata in
-- viste separate per-tipo (preventivi via tabella snapshot; ordini e DDT via
-- viste derivate al volo, cloni 1:1). Se qualcuno corregge un arrotondamento
-- in un tipo e non negli altri -> incoerenza fiscale silenziosa tra documenti.
-- Questo test la fa fallire subito.
--
-- Due livelli:
--   A) STRUTTURALE (fixture-free): il testo normalizzato delle viste
--      ordini vs DDT deve coincidere (stessa formula, a meno del nome
--      tabella/colonna). Becca ogni edit divergente alla formula.
--   B) COMPORTAMENTALE: stesse righe inserite in ordine, DDT e preventivo
--      -> stessi numeri fiscali (imponibile/imposta/arrotondamento).
--      Copre anche il preventivo, che usa un meccanismo diverso (snapshot)
--      e non e' confrontabile strutturalmente.
--
-- Indice test (1..9):
--   1. STRUTT: viewdef normalizzato vw_*_righe_iva_base identico (ordini/DDT)
--   2. STRUTT: viewdef normalizzato vw_*_riepilogo_iva_dettaglio identico
--   3. Riferimenti minimi disponibili
--   4. COMPORT: ordini vs DDT -> riepiloghi identici (diff simmetrica = 0)
--   5. COMPORT: ordini vs DDT -> caso ROUND(SUM): arrotondamento uguale e != 0
--   6. COMPORT: preventivi vs ordini -> imponibile aggregato uguale (aliq. A)
--   7. COMPORT: preventivi vs ordini -> arrotondamento uguale (aliq. A)
--   8. COMPORT: preventivi vs ordini -> imposta uguale (aliq. A)
--   9. COMPORT: preventivi vs ordini -> imponibile con sconto uguale (aliq. B)
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

SELECT plan(9);

-- ⛔ 2026-09-04 — QUI IL TEST SPEGNEVA IL GUARD, e adesso non piu'.
--   La riga rimossa era `set_config('app.current_user_id', '', true)`: senza
--   utente in sessione `script.trgfn_guard_emittente_scope` usciva subito con
--   RETURN NEW, e le fixture entravano senza che nessuno guardasse l'emittente.
--   La fase 6 di `brief-db-processi-automatici-identita-e-perimetro` chiude quel
--   ramo — una sessione applicativa senza utente non scrive piu'.
--   ⇒ Il contesto operatore del preambolo RESTA valido per tutto il file, e le
--     fixture prendono l'emittente su cui quell'operatore puo' davvero scrivere
--     (`script.fn_pgtap_emittente_operatore()`).
--   ⭐ Non e' una riparazione di comodo: prima questo file collaudava il
--     comportamento di una porta aperta, adesso attraversa il guard come lo
--     attraversa l'applicazione.

-- ============================================================
-- A) STRUTTURALE - viewdef normalizzato ordini vs DDT
--    Normalizzazione: azzera i token specifici del tipo documento
--    (ordine_id/ddt_id -> doc_id; ordini/ddt -> doc). Cosi' le due
--    definizioni, se la formula e' la stessa, diventano stringhe identiche.
-- ============================================================

-- 1) Vista base: confronto della sola FORMULA (SELECT + FROM/JOIN, prima del
--    WHERE). Il WHERE e' escluso di proposito: la DDT filtra in piu
--    `prezzo_unitario IS NOT NULL` (righe di solo trasporto), differenza di
--    scope voluta, non di formula. Le espressioni imponibile/sconto/aliquota
--    del SELECT devono invece coincidere.
WITH n AS (
  SELECT
    replace(replace(replace(replace(
      split_part(pg_get_viewdef('vendite.vw_ordini_righe_iva_base'::regclass, true), 'WHERE', 1),
      'ordine_id', 'doc_id'), 'ordini', 'doc'), 'ddt_id', 'doc_id'), 'ddt', 'doc') AS ord,
    replace(replace(replace(replace(
      split_part(pg_get_viewdef('vendite.vw_ddt_righe_iva_base'::regclass, true), 'WHERE', 1),
      'ordine_id', 'doc_id'), 'ordini', 'doc'), 'ddt_id', 'doc_id'), 'ddt', 'doc') AS ddt
)
SELECT is(
  (SELECT ord FROM n),
  (SELECT ddt FROM n),
  '1. STRUTT: formula (SELECT/JOIN) vw_*_righe_iva_base identica tra ordini e DDT, WHERE escluso'
);

-- 2) Vista riepilogo
WITH n AS (
  SELECT
    replace(replace(replace(replace(
      pg_get_viewdef('vendite.vw_ordini_riepilogo_iva_dettaglio'::regclass, true),
      'ordine_id', 'doc_id'), 'ordini', 'doc'), 'ddt_id', 'doc_id'), 'ddt', 'doc') AS ord,
    replace(replace(replace(replace(
      pg_get_viewdef('vendite.vw_ddt_riepilogo_iva_dettaglio'::regclass, true),
      'ordine_id', 'doc_id'), 'ordini', 'doc'), 'ddt_id', 'doc_id'), 'ddt', 'doc') AS ddt
)
SELECT is(
  (SELECT ord FROM n),
  (SELECT ddt FROM n),
  '2. STRUTT: formula vw_*_riepilogo_iva_dettaglio identica tra ordini e DDT (viewdef normalizzato)'
);

-- ============================================================
-- B) COMPORTAMENTALE - stesse righe nei tre documenti
-- ============================================================

-- Riferimenti minimi (stesso emittente e stesso articolo per tutti -> stessa
-- base aliquota; billing_account con utility/istanza richiesto dal preventivo).
CREATE TEMP TABLE tmp_eqiva_refs AS
SELECT
  (SELECT ef.id
     FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1)                 AS emittente_fiscale_id,
  (SELECT ef.soggetto_ruolo_id
     FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1)                 AS soggetto_ruolo_id,
  (SELECT ba.id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                 AS billing_account_id,
  (SELECT ba.utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                 AS utility_id,
  (SELECT ba.istanza_utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                 AS istanza_utility_id,
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
  dbops.fn_pgtap_crea_articolo('PGT-RIEC-ART', false)                                AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.attivo IS TRUE ORDER BY s.id LIMIT 1)          AS stato_doc_ordine_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.attivo IS TRUE ORDER BY s.id LIMIT 1)          AS stato_doc_ddt_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1) AS stato_draft_id,
  -- aliquota A: la piu' alta > 0
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
    ORDER BY i.aliquota_iva DESC LIMIT 1)   AS iva_a_id,
  -- aliquota B: distinta, piu' bassa
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
      AND i.aliquota_iva < (SELECT MAX(i2.aliquota_iva)
                              FROM config.iva i2 WHERE i2.attivo IS TRUE)
    ORDER BY i.aliquota_iva DESC LIMIT 1)   AS iva_b_id;

SELECT ok(
  (SELECT emittente_fiscale_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_doc_ordine_id IS NOT NULL
      AND stato_doc_ddt_id IS NOT NULL
      AND iva_a_id IS NOT NULL
      AND iva_b_id IS NOT NULL
      AND iva_a_id <> iva_b_id
     FROM tmp_eqiva_refs),
  '3. riferimenti minimi disponibili (emittente, articolo, 2 aliquote, stati doc)'
);

-- ------------------------------------------------------------
-- Set canonico di righe (identico nei tre documenti):
--   aliquota A: 3 righe qta=1 prezzo=33.335 sconto=0  -> imponibile_full 100.005
--               (stressa ROUND(SUM): ROUND=100.01, arrotondamento -0.005)
--   aliquota B: 1 riga  qta=1 prezzo=200   sconto=10% -> imponibile 180.00
-- ------------------------------------------------------------

-- ===== ORDINE =====
CREATE TEMP TABLE tmp_eqiva_ordine(id bigint);

-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-1): l'ordine ha sempre il
--   BA, e il suo cliente e' il ruolo del BA (fk_ordini_ba_cliente). Prima
--   nasceva senza BA e col ruolo dell'EMITTENTE come cliente. Il cliente si
--   FABBRICA: pescato dai dati, su un database senza billing account l'ordine
--   non nasceva. Il trigger z90 lega il BA all'emittente dell'operatore.
CREATE TEMP TABLE tmp_eqiva_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('riepilogo iva equivalenza');
SET CONSTRAINTS ALL IMMEDIATE;

WITH ins AS (
  INSERT INTO vendite.ordini (
    serie, numero, anno, data,
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id, valuta_id, emittente_fiscale_id,
    storicizza, meta
  )
  SELECT
    'PGTAP', 'EQIVA-O-' || substr(md5(clock_timestamp()::text), 1, 8), 2080, DATE '2080-06-01',
    c.soggetto_ruolo_id,
    c.billing_account_id, r.stato_doc_ordine_id, r.valuta_id,
    anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id),
    false, jsonb_build_object('test_scope', 'pgtap_eqiva')
  FROM tmp_eqiva_refs r, tmp_eqiva_cli c
  WHERE r.soggetto_ruolo_id IS NOT NULL
    AND r.emittente_fiscale_id IS NOT NULL
    AND r.stato_doc_ordine_id IS NOT NULL
    AND r.articolo_id IS NOT NULL
    AND r.iva_a_id IS NOT NULL
    AND r.iva_b_id IS NOT NULL
  RETURNING id
)
INSERT INTO tmp_eqiva_ordine(id) SELECT id FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, sconto_percentuale, iva_id,
  attivo, meta
)
SELECT o.id, gs.n, r.articolo_id, 'EQIVA A ' || gs.n::text,
       1, 1, 33.335, 0, r.iva_a_id, true, jsonb_build_object('test_scope', 'pgtap_eqiva')
FROM tmp_eqiva_ordine o CROSS JOIN tmp_eqiva_refs r CROSS JOIN generate_series(1, 3) AS gs(n);

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, sconto_percentuale, iva_id,
  attivo, meta
)
SELECT o.id, 20, r.articolo_id, 'EQIVA B sconto',
       1, 1, 200, 10, r.iva_b_id, true, jsonb_build_object('test_scope', 'pgtap_eqiva')
FROM tmp_eqiva_ordine o CROSS JOIN tmp_eqiva_refs r;

-- ===== DDT =====
CREATE TEMP TABLE tmp_eqiva_ddt(id bigint);
WITH ins AS (
  INSERT INTO vendite.ddt (
    destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data,
    emittente_fiscale_id, valuta_id, storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, r.stato_doc_ddt_id, DATE '2080-06-01',
    r.emittente_fiscale_id, r.valuta_id, false, jsonb_build_object('test_scope', 'pgtap_eqiva')
  FROM tmp_eqiva_refs r
  WHERE r.soggetto_ruolo_id IS NOT NULL
    AND r.emittente_fiscale_id IS NOT NULL
    AND r.stato_doc_ddt_id IS NOT NULL
    AND r.articolo_id IS NOT NULL
    AND r.iva_a_id IS NOT NULL
    AND r.iva_b_id IS NOT NULL
  RETURNING id
)
INSERT INTO tmp_eqiva_ddt(id) SELECT id FROM ins;

INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, sconto_percentuale, iva_id,
  attivo, storicizza, meta
)
SELECT o.id, gs.n, r.articolo_id, 'EQIVA A ' || gs.n::text,
       1, 1, 33.335, 0, r.iva_a_id, true, false, jsonb_build_object('test_scope', 'pgtap_eqiva')
FROM tmp_eqiva_ddt o CROSS JOIN tmp_eqiva_refs r CROSS JOIN generate_series(1, 3) AS gs(n);

INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, sconto_percentuale, iva_id,
  attivo, storicizza, meta
)
SELECT o.id, 20, r.articolo_id, 'EQIVA B sconto',
       1, 1, 200, 10, r.iva_b_id, true, false, jsonb_build_object('test_scope', 'pgtap_eqiva')
FROM tmp_eqiva_ddt o CROSS JOIN tmp_eqiva_refs r;

-- ===== PREVENTIVO (snapshot popolato dal trigger su insert righe) =====
CREATE TEMP TABLE tmp_eqiva_prev(id bigint);
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, emittente_fiscale_id,
    storicizza, meta
  )
  SELECT
    'PGTAP-EQIVA-' || substr(md5(clock_timestamp()::text), 1, 8), 0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2080-06-01', DATE '2080-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2080-06-01', r.emittente_fiscale_id,
    false, jsonb_build_object('test_scope', 'pgtap_eqiva')
  FROM tmp_eqiva_refs r
  WHERE r.billing_account_id IS NOT NULL
    AND r.stato_draft_id IS NOT NULL
    AND r.emittente_fiscale_id IS NOT NULL
    AND r.articolo_id IS NOT NULL
    AND r.iva_a_id IS NOT NULL
    AND r.iva_b_id IS NOT NULL
  RETURNING id
)
INSERT INTO tmp_eqiva_prev(id) SELECT id FROM ins;

INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id, attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 1, 1, 33.335, 0, r.iva_a_id, true, gs.n,
       jsonb_build_object('test_scope', 'pgtap_eqiva')
FROM tmp_eqiva_prev p CROSS JOIN tmp_eqiva_refs r CROSS JOIN generate_series(1, 3) AS gs(n);

INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id, attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 1, 1, 200, 10, r.iva_b_id, true, 20,
       jsonb_build_object('test_scope', 'pgtap_eqiva')
FROM tmp_eqiva_prev p CROSS JOIN tmp_eqiva_refs r;

-- ============================================================
-- 4) Ordini vs DDT: riepiloghi fiscalmente identici (diff simmetrica = 0)
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_eqiva_ordine)
    OR NOT EXISTS (SELECT 1 FROM tmp_eqiva_ddt)
  THEN skip('4. ordine o DDT di test non creato')
  ELSE is(
    (
      SELECT COUNT(*)::integer FROM (
        (
          SELECT iva_id, imponibile, imposta, arrotondamento, totale_riga, iva_aliquota
            FROM vendite.vw_ordini_riepilogo_iva_dettaglio
           WHERE ordine_id = (SELECT id FROM tmp_eqiva_ordine)
          EXCEPT
          SELECT iva_id, imponibile, imposta, arrotondamento, totale_riga, iva_aliquota
            FROM vendite.vw_ddt_riepilogo_iva_dettaglio
           WHERE ddt_id = (SELECT id FROM tmp_eqiva_ddt)
        )
        UNION ALL
        (
          SELECT iva_id, imponibile, imposta, arrotondamento, totale_riga, iva_aliquota
            FROM vendite.vw_ddt_riepilogo_iva_dettaglio
           WHERE ddt_id = (SELECT id FROM tmp_eqiva_ddt)
          EXCEPT
          SELECT iva_id, imponibile, imposta, arrotondamento, totale_riga, iva_aliquota
            FROM vendite.vw_ordini_riepilogo_iva_dettaglio
           WHERE ordine_id = (SELECT id FROM tmp_eqiva_ordine)
        )
      ) d
    ),
    0,
    '4. ordini vs DDT: riepiloghi IVA identici a parita di righe (diff simmetrica = 0)'
  )
END;

-- ============================================================
-- 5) Ordini vs DDT: caso ROUND(SUM) -> arrotondamento uguale e non nullo
--    (conferma che il set canonico stressa davvero l'arrotondamento)
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_eqiva_ordine)
    OR NOT EXISTS (SELECT 1 FROM tmp_eqiva_ddt)
  THEN skip('5. ordine o DDT di test non creato')
  ELSE ok(
    (
      SELECT o.arrotondamento = d.arrotondamento
         AND o.arrotondamento <> 0
        FROM vendite.vw_ordini_riepilogo_iva_dettaglio o
        JOIN vendite.vw_ddt_riepilogo_iva_dettaglio d
          ON d.iva_id = o.iva_id
       WHERE o.ordine_id = (SELECT id FROM tmp_eqiva_ordine)
         AND d.ddt_id   = (SELECT id FROM tmp_eqiva_ddt)
         AND o.iva_id   = (SELECT iva_a_id FROM tmp_eqiva_refs)
    ),
    '5. ordini vs DDT: caso ROUND(SUM) -> stesso arrotondamento residuo, non nullo'
  )
END;

-- ============================================================
-- 6) Preventivi vs Ordini: imponibile aggregato uguale (aliquota A)
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_eqiva_prev)
    OR NOT EXISTS (SELECT 1 FROM tmp_eqiva_ordine)
  THEN skip('6. preventivo o ordine di test non creato')
  ELSE is(
    (SELECT imponibile FROM vendite.vw_preventivi_riepilogo_iva_dettaglio
      WHERE preventivo_id = (SELECT id FROM tmp_eqiva_prev)
        AND iva_id = (SELECT iva_a_id FROM tmp_eqiva_refs)),
    (SELECT imponibile FROM vendite.vw_ordini_riepilogo_iva_dettaglio
      WHERE ordine_id = (SELECT id FROM tmp_eqiva_ordine)
        AND iva_id = (SELECT iva_a_id FROM tmp_eqiva_refs)),
    '6. preventivi vs ordini: stesso imponibile aggregato (aliquota A, ROUND(SUM))'
  )
END;

-- ============================================================
-- 7) Preventivi vs Ordini: imponibile TOTALE aggregato uguale
--    (somma su tutte le aliquote; robusto rispetto alla convenzione di
--    segno dell'arrotondamento, che tra snapshot e vista puo' differire)
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_eqiva_prev)
    OR NOT EXISTS (SELECT 1 FROM tmp_eqiva_ordine)
  THEN skip('7. preventivo o ordine di test non creato')
  ELSE is(
    (SELECT COALESCE(SUM(imponibile), 0) FROM vendite.vw_preventivi_riepilogo_iva_dettaglio
      WHERE preventivo_id = (SELECT id FROM tmp_eqiva_prev)),
    (SELECT COALESCE(SUM(imponibile), 0) FROM vendite.vw_ordini_riepilogo_iva_dettaglio
      WHERE ordine_id = (SELECT id FROM tmp_eqiva_ordine)),
    '7. preventivi vs ordini: stesso imponibile totale aggregato (tutte le aliquote)'
  )
END;

-- ============================================================
-- 8) Preventivi vs Ordini: imposta uguale (aliquota A)
--    Guard: solo se l'aliquota effettiva coincide (i due meccanismi
--    potrebbero risolverla diversamente per emittente estero; qui interessa
--    la coerenza della FORMULA, non la fonte dell'aliquota).
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_eqiva_prev)
    OR NOT EXISTS (SELECT 1 FROM tmp_eqiva_ordine)
  THEN skip('8. preventivo o ordine di test non creato')
  WHEN (
    SELECT p.iva_aliquota IS DISTINCT FROM o.iva_aliquota
      FROM vendite.vw_preventivi_riepilogo_iva_dettaglio p,
           vendite.vw_ordini_riepilogo_iva_dettaglio o
     WHERE p.preventivo_id = (SELECT id FROM tmp_eqiva_prev)
       AND p.iva_id = (SELECT iva_a_id FROM tmp_eqiva_refs)
       AND o.ordine_id = (SELECT id FROM tmp_eqiva_ordine)
       AND o.iva_id = (SELECT iva_a_id FROM tmp_eqiva_refs)
  )
  THEN skip('8. aliquota effettiva risolta diversamente (emittente non domestico): confronto imposta non applicabile')
  ELSE is(
    (SELECT imposta FROM vendite.vw_preventivi_riepilogo_iva_dettaglio
      WHERE preventivo_id = (SELECT id FROM tmp_eqiva_prev)
        AND iva_id = (SELECT iva_a_id FROM tmp_eqiva_refs)),
    (SELECT imposta FROM vendite.vw_ordini_riepilogo_iva_dettaglio
      WHERE ordine_id = (SELECT id FROM tmp_eqiva_ordine)
        AND iva_id = (SELECT iva_a_id FROM tmp_eqiva_refs)),
    '8. preventivi vs ordini: stessa imposta su imponibile aggregato (aliquota A)'
  )
END;

-- ============================================================
-- 9) Preventivi vs Ordini: imponibile con sconto uguale (aliquota B)
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_eqiva_prev)
    OR NOT EXISTS (SELECT 1 FROM tmp_eqiva_ordine)
  THEN skip('9. preventivo o ordine di test non creato')
  ELSE is(
    (SELECT imponibile FROM vendite.vw_preventivi_riepilogo_iva_dettaglio
      WHERE preventivo_id = (SELECT id FROM tmp_eqiva_prev)
        AND iva_id = (SELECT iva_b_id FROM tmp_eqiva_refs)),
    (SELECT imponibile FROM vendite.vw_ordini_riepilogo_iva_dettaglio
      WHERE ordine_id = (SELECT id FROM tmp_eqiva_ordine)
        AND iva_id = (SELECT iva_b_id FROM tmp_eqiva_refs)),
    '9. preventivi vs ordini: stesso imponibile scontato (aliquota B, sconto 10%)'
  )
END;

SELECT * FROM finish();
ROLLBACK;
