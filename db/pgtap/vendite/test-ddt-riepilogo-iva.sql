-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: riepilogo IVA DDT vendita (viste vw_ddt_righe_iva_base ->
--       vw_ddt_riepilogo_iva_dettaglio). Clone lettura-pura delle omologhe
--       ordini: NIENTE trigger/ricalcolo di testata (i DDT non hanno totali
--       di testata), quindi rispetto al test ordini plan(18) qui restano solo
--       i casi shape + formula + esclusioni, piu' i due DDT-specifici
--       (riga prezzo NULL esclusa; DDT non valorizzato -> 0 righe).
--
-- Indice test (1..13):
--   1.  View base righe IVA DDT presente
--   2.  View riepilogo IVA DDT presente
--   3.  Riferimenti minimi disponibili
--   4.  Stessa IVA su piu righe -> una sola riga riepilogo
--   5.  Centesimi: ROUND(SUM) e non SUM(ROUND) -> 3 * 0.333 = 1.00
--   6.  Riga inattiva esclusa dal riepilogo
--   7.  Riga con prezzo_unitario NULL esclusa (DDT non valorizzato)
--   8.  IVA diverse -> piu righe riepilogo
--   9.  Sconto riga applicato all'imponibile aggregato
--   10. Imposta = ROUND(imponibile * aliquota_effettiva / 100) via fn_get_aliquota_iva
--   11. DDT interamente non valorizzato -> 0 righe riepilogo
--   12. La view riepilogo non espone id tecnico
--   13. BoM: la view base non legge ddt_righe_componenti
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): le due testate in bozza da
--   dbops.fn_pgtap_crea_ddt (VENDITA, p_data) sul cliente di dbops.fn_pgtap_crea_mondo_cliente:
--   curata la pesca del «primo emittente attivo» (destinatario = l'emittente stesso, senza BA).
--   Le righe prezzate e non prezzate restano a mano: sono il caso.
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

SELECT plan(13);

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
-- 1) View base presente
-- ============================================================
SELECT has_view(
  'vendite',
  'vw_ddt_righe_iva_base',
  '1. view vendite.vw_ddt_righe_iva_base presente'
);

-- ============================================================
-- 2) View riepilogo presente
-- ============================================================
SELECT has_view(
  'vendite',
  'vw_ddt_riepilogo_iva_dettaglio',
  '2. view vendite.vw_ddt_riepilogo_iva_dettaglio presente'
);

-- ============================================================
-- Setup riferimenti minimi
-- ============================================================
-- ⛔ rev 2026-10-25 (giro D-4): il cliente e l'emittente si COSTRUISCONO. Prima
--   l'emittente era «il primo emittente attivo per id», e il destinatario il suo
--   stesso soggetto: pescato, e verde solo dove il primo emittente e' quello
--   dell'operatore. Il mondo riusa l'azienda di chi agisce (contesto aperto).
CREATE TEMP TABLE tmp_ddtiva_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP riepilogo IVA DDT');

CREATE TEMP TABLE tmp_ddtiva_refs AS
WITH iva1 AS (
  SELECT i.id, i.aliquota_iva
    FROM config.iva i
   WHERE i.attivo IS TRUE
   ORDER BY i.id
   LIMIT 1
),
iva2 AS (
  SELECT i.id, i.aliquota_iva
    FROM config.iva i, iva1
   WHERE i.attivo IS TRUE
     AND i.id <> iva1.id
     AND i.aliquota_iva IS DISTINCT FROM iva1.aliquota_iva
   ORDER BY i.id
   LIMIT 1
),
m AS (
  SELECT * FROM tmp_ddtiva_mondo
)
SELECT
  (SELECT cliente_soggetto_ruolo_id FROM m) AS soggetto_ruolo_id,
  (SELECT billing_account_id FROM m)        AS billing_account_id,
  (SELECT emittente_fiscale_id FROM m)      AS emittente_fiscale_id,
  -- stato dell'emittente (per aliquota effettiva via fn_get_aliquota_iva)
  (SELECT s.stato_id
     FROM m
     JOIN anagrafiche.emittenti_fiscali ef1 ON ef1.id = m.emittente_fiscale_id
     JOIN anagrafiche.soggetti_ruoli sr     ON sr.id = ef1.soggetto_ruolo_id
     JOIN anagrafiche.soggetti s            ON s.id = sr.soggetto_id
  )                                   AS stato_emittente_id,
  (SELECT s.id
     FROM config.stati_doc_ddt s
    WHERE s.attivo IS TRUE
    ORDER BY s.id LIMIT 1)            AS stato_doc_ddt_id,
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
  dbops.fn_pgtap_crea_articolo('PGT-DRI-ART', false)                          AS articolo_id,
  (SELECT id FROM iva1)               AS iva1_id,
  (SELECT aliquota_iva FROM iva1)     AS iva1_aliquota,
  (SELECT id FROM iva2)               AS iva2_id,
  (SELECT aliquota_iva FROM iva2)     AS iva2_aliquota;

SELECT ok(
  (
    SELECT soggetto_ruolo_id IS NOT NULL
       AND emittente_fiscale_id IS NOT NULL
       AND stato_doc_ddt_id IS NOT NULL
       AND articolo_id IS NOT NULL
       AND iva1_id IS NOT NULL
      FROM tmp_ddtiva_refs
  ),
  '3. riferimenti minimi disponibili per test funzionali'
);

-- ============================================================
-- Crea DDT di test (l'emittente e' quello dell'operatore, dal builder)
-- ============================================================
CREATE TEMP TABLE tmp_ddtiva_ddt(id bigint);

-- La testata in bozza dal builder (causale VENDITA, indirizzi), alla sua data.
INSERT INTO tmp_ddtiva_ddt(id)
SELECT dbops.fn_pgtap_crea_ddt(r.billing_account_id, r.soggetto_ruolo_id, 'VENDITA',
                               p_data => DATE '2080-06-01')
  FROM tmp_ddtiva_refs r
 WHERE r.soggetto_ruolo_id IS NOT NULL
   AND r.emittente_fiscale_id IS NOT NULL
   AND r.stato_doc_ddt_id IS NOT NULL
   AND r.articolo_id IS NOT NULL
   AND r.iva1_id IS NOT NULL;

-- ============================================================
-- Inserisce tre righe stessa IVA: 3 * 0.333 = 0.999 -> ROUND(SUM) = 1.00
-- ============================================================
INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, storicizza, meta
)
SELECT
  o.id, gs.riga_nr, r.articolo_id,
  'PGTAP DDT IVA stessa aliquota ' || gs.riga_nr::text,
  1, 1,
  0.333, 0, r.iva1_id,
  true, false, jsonb_build_object('test_scope', 'pgtap_ddt_riepilogo_iva')
FROM tmp_ddtiva_ddt o
CROSS JOIN tmp_ddtiva_refs r
CROSS JOIN generate_series(1, 3) AS gs(riga_nr);

-- ============================================================
-- 4) Stessa IVA -> una riga riepilogo
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ddtiva_ddt)
  THEN skip('4. riferimenti insufficienti: DDT test non creato')
  ELSE is(
    (SELECT COUNT(*)::integer
       FROM vendite.vw_ddt_riepilogo_iva_dettaglio
      WHERE ddt_id = (SELECT id FROM tmp_ddtiva_ddt)),
    1,
    '4. stessa IVA su piu righe -> una riga riepilogo'
  )
END;

-- ============================================================
-- 5) Centesimi: ROUND(SUM), non SUM(ROUND)
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ddtiva_ddt)
  THEN skip('5. riferimenti insufficienti: DDT test non creato')
  ELSE is(
    (SELECT imponibile
       FROM vendite.vw_ddt_riepilogo_iva_dettaglio
      WHERE ddt_id = (SELECT id FROM tmp_ddtiva_ddt)
      LIMIT 1),
    1.00::numeric,
    '5. centesimi: 3 * 0.333 -> imponibile aggregato ROUND(SUM)=1.00'
  )
END;

-- ============================================================
-- 6) Riga inattiva esclusa
-- ============================================================
INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, storicizza, meta
)
SELECT
  o.id, 90, r.articolo_id, 'PGTAP DDT IVA riga inattiva',
  1, 1, 9999, 0, r.iva1_id,
  false, false, jsonb_build_object('test_scope', 'pgtap_ddt_riepilogo_iva')
FROM tmp_ddtiva_ddt o
CROSS JOIN tmp_ddtiva_refs r;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ddtiva_ddt)
  THEN skip('6. riferimenti insufficienti: DDT test non creato')
  ELSE is(
    (SELECT imponibile
       FROM vendite.vw_ddt_riepilogo_iva_dettaglio
      WHERE ddt_id = (SELECT id FROM tmp_ddtiva_ddt)
      LIMIT 1),
    1.00::numeric,
    '6. riga inattiva esclusa dal riepilogo IVA'
  )
END;

-- ============================================================
-- 7) Riga con prezzo_unitario NULL esclusa (DDT non valorizzato)
--    Deve restare 1 solo gruppo (iva1) e imponibile invariato 1.00.
-- ============================================================
INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, storicizza, meta
)
SELECT
  o.id, 91, r.articolo_id, 'PGTAP DDT IVA riga non valorizzata',
  1, 1, NULL, NULL, NULL,
  true, false, jsonb_build_object('test_scope', 'pgtap_ddt_riepilogo_iva')
FROM tmp_ddtiva_ddt o
CROSS JOIN tmp_ddtiva_refs r;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ddtiva_ddt)
  THEN skip('7. riferimenti insufficienti: DDT test non creato')
  ELSE is(
    (SELECT COUNT(*)::integer || ':' || COALESCE(MAX(imponibile)::text, 'NULL')
       FROM vendite.vw_ddt_riepilogo_iva_dettaglio
      WHERE ddt_id = (SELECT id FROM tmp_ddtiva_ddt)),
    '1:1.00',
    '7. riga con prezzo_unitario NULL esclusa (1 gruppo, imponibile invariato 1.00)'
  )
END;

-- ============================================================
-- 8/9/10) IVA diversa con sconto: 100 * (1 - 10%) = 90.00
--    imposta = ROUND(90 * aliquota_effettiva(iva2, stato_emittente) / 100)
-- ============================================================
INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, storicizza, meta
)
SELECT
  o.id, 92, r.articolo_id, 'PGTAP DDT IVA diversa con sconto',
  1, 1, 100, 10, r.iva2_id,
  true, false, jsonb_build_object('test_scope', 'pgtap_ddt_riepilogo_iva')
FROM tmp_ddtiva_ddt o
CROSS JOIN tmp_ddtiva_refs r
WHERE r.iva2_id IS NOT NULL;

-- 8) IVA diverse -> piu righe riepilogo
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ddtiva_ddt)
  THEN skip('8. riferimenti insufficienti: DDT test non creato')
  WHEN (SELECT iva2_id IS NULL FROM tmp_ddtiva_refs)
  THEN skip('8. una sola aliquota IVA disponibile nei dati di test')
  ELSE is(
    (SELECT COUNT(*)::integer
       FROM vendite.vw_ddt_riepilogo_iva_dettaglio
      WHERE ddt_id = (SELECT id FROM tmp_ddtiva_ddt)),
    2,
    '8. IVA diverse -> piu righe riepilogo'
  )
END;

-- 9) Sconto riga applicato all'imponibile aggregato
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ddtiva_ddt)
  THEN skip('9. riferimenti insufficienti: DDT test non creato')
  WHEN (SELECT iva2_id IS NULL FROM tmp_ddtiva_refs)
  THEN skip('9. una sola aliquota IVA disponibile nei dati di test')
  ELSE is(
    (SELECT imponibile
       FROM vendite.vw_ddt_riepilogo_iva_dettaglio
      WHERE ddt_id = (SELECT id FROM tmp_ddtiva_ddt)
        AND iva_id = (SELECT iva2_id FROM tmp_ddtiva_refs)),
    90.00::numeric,
    '9. sconto 10% su 100 -> imponibile aggregato 90.00'
  )
END;

-- 10) Imposta calcolata su aliquota effettiva (fn_get_aliquota_iva)
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ddtiva_ddt)
  THEN skip('10. riferimenti insufficienti: DDT test non creato')
  WHEN (SELECT iva2_id IS NULL FROM tmp_ddtiva_refs)
  THEN skip('10. una sola aliquota IVA disponibile nei dati di test')
  ELSE is(
    (SELECT imposta
       FROM vendite.vw_ddt_riepilogo_iva_dettaglio
      WHERE ddt_id = (SELECT id FROM tmp_ddtiva_ddt)
        AND iva_id = (SELECT iva2_id FROM tmp_ddtiva_refs)),
    (SELECT ROUND(90.00 * config.fn_get_aliquota_iva(
                    r.iva2_id, r.stato_emittente_id) / 100, 2)
       FROM tmp_ddtiva_refs r),
    '10. imposta = ROUND(imponibile * aliquota_effettiva / 100) via fn_get_aliquota_iva'
  )
END;

-- ============================================================
-- 11) DDT interamente non valorizzato -> 0 righe riepilogo
-- ============================================================
CREATE TEMP TABLE tmp_ddtiva_novalore(id bigint);

INSERT INTO tmp_ddtiva_novalore(id)
SELECT dbops.fn_pgtap_crea_ddt(r.billing_account_id, r.soggetto_ruolo_id, 'VENDITA',
                               p_data => DATE '2080-06-02')
  FROM tmp_ddtiva_refs r
 WHERE r.emittente_fiscale_id IS NOT NULL
   AND r.stato_doc_ddt_id IS NOT NULL;

INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, storicizza, meta
)
SELECT
  o.id, gs.riga_nr, r.articolo_id,
  'PGTAP DDT solo trasporto ' || gs.riga_nr::text,
  1, 1, NULL, NULL, NULL,
  true, false, jsonb_build_object('test_scope', 'pgtap_ddt_riepilogo_iva', 'case', 'novalore')
FROM tmp_ddtiva_novalore o
CROSS JOIN tmp_ddtiva_refs r
CROSS JOIN generate_series(1, 2) AS gs(riga_nr);

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ddtiva_novalore)
  THEN skip('11. riferimenti insufficienti: DDT non valorizzato non creato')
  ELSE is(
    (SELECT COUNT(*)::integer
       FROM vendite.vw_ddt_riepilogo_iva_dettaglio
      WHERE ddt_id = (SELECT id FROM tmp_ddtiva_novalore)),
    0,
    '11. DDT interamente non valorizzato -> 0 righe riepilogo'
  )
END;

-- ============================================================
-- 12) Nessun id tecnico nel riepilogo derivato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
      FROM information_schema.columns
     WHERE table_schema = 'vendite'
       AND table_name = 'vw_ddt_riepilogo_iva_dettaglio'
       AND column_name = 'id'
  ),
  '12. vw_ddt_riepilogo_iva_dettaglio non espone id tecnico'
);

-- ============================================================
-- 13) BoM: la view base non legge direttamente i componenti
-- ============================================================
SELECT ok(
  pg_get_viewdef('vendite.vw_ddt_righe_iva_base'::regclass, true)
    NOT ILIKE '%ddt_righe_componenti%',
  '13. BoM: vw_ddt_righe_iva_base non legge ddt_righe_componenti, quindi evita doppio conteggio'
);

SELECT * FROM finish();
ROLLBACK;
