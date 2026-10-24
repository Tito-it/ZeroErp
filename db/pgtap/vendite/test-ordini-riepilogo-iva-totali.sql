-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: riepilogo IVA e totali ordini vendita
--
-- Indice test (1..18):
--   1.  View base righe IVA ordine presente
--   2.  View riepilogo IVA ordine presente
--   3.  Funzione fn_ricalcola_totali_ordine presente
--   4.  Trigger statement-level su ordini_righe presenti (ins/upd/dlt)
--   5.  Il ricalcolo sul cambio di emittente e' ritirato (rev 2026-10-09)
--   6.  Riferimenti minimi disponibili per test funzionali
--   7.  Funzione su ordine senza righe -> totali zero
--   8.  Stessa IVA -> una sola riga riepilogo
--   9.  Centesimi: ROUND(SUM) e non SUM(ROUND)
--   10. Riga inattiva esclusa dal riepilogo
--   11. IVA diverse -> piu righe riepilogo
--   12. Funzione aggiorna la testata sommando il riepilogo
--   13. Trigger righe UPDATE ricalcola totali testata
--   14. Trigger righe DELETE registrato con transition table
--   15. L'emittente dell'ordine e' bloccato fuori bozza (rev 2026-10-09)
--   16. BoM: la view base non legge ordini_righe_componenti
--   17. La view riepilogo non espone id tecnico derivato
--   18. Guard funzione: p_ordine_id NULL -> errore
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

SELECT plan(18);

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
  'vw_ordini_righe_iva_base',
  '1. view vendite.vw_ordini_righe_iva_base presente'
);

-- ============================================================
-- 2) View riepilogo presente
-- ============================================================
SELECT has_view(
  'vendite',
  'vw_ordini_riepilogo_iva_dettaglio',
  '2. view vendite.vw_ordini_riepilogo_iva_dettaglio presente'
);

-- ============================================================
-- 3) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'vendite'
       AND p.proname = 'fn_ricalcola_totali_ordine'
  ),
  '3. fn_ricalcola_totali_ordine presente'
);

-- ============================================================
-- 4) Trigger statement-level su ordini_righe
-- ============================================================
SELECT is(
  (
    SELECT COUNT(*)::integer
      FROM pg_trigger t
      JOIN pg_class c ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'vendite'
       AND c.relname = 'ordini_righe'
       AND t.tgname IN (
         'trg_ordini_righe_z90_ricalcola_totali_ins',
         'trg_ordini_righe_z90_ricalcola_totali_upd',
         'trg_ordini_righe_z90_ricalcola_totali_dlt'
       )
       AND NOT t.tgisinternal
  ),
  3,
  '4. trigger ricalcolo ordini_righe presenti (ins/upd/dlt)'
);

-- ============================================================
-- 5) Nessun ricalcolo «sul cambio di emittente»: l'emittente non cambia
-- ============================================================
-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, §9.8): trg_ordini_z90_
--   ricalcola_totali_upd ricalcolava i totali dopo un cambio di emittente
--   (20260605-05). Con il BA obbligatorio e un emittente per BA quel cambio
--   non ha piu' un caso legittimo, e fuori bozza lo vieta il lock dichiarato
--   (test 15): il trigger e' ritirato (20261009-89).
SELECT ok(
  NOT EXISTS (
    SELECT 1
      FROM pg_trigger t
     WHERE t.tgrelid = 'vendite.ordini'::regclass
       AND t.tgname = 'trg_ordini_z90_ricalcola_totali_upd'
       AND NOT t.tgisinternal
  ),
  '5. il ricalcolo sul cambio di emittente e'' ritirato: l''emittente dell''ordine non cambia'
);

-- ============================================================
-- Setup riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_ordiva_refs AS
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
ef AS (
  SELECT ef1.id AS ef1_id,
         ef1.soggetto_ruolo_id,
         (
           SELECT ef2.id
             FROM anagrafiche.emittenti_fiscali ef2
            WHERE ef2.attivo IS TRUE
              AND ef2.id <> ef1.id
            ORDER BY ef2.id
            LIMIT 1
         ) AS ef2_id
    FROM anagrafiche.emittenti_fiscali ef1
   WHERE ef1.attivo IS TRUE
   ORDER BY ef1.id
   LIMIT 1
)
SELECT
  (SELECT soggetto_ruolo_id FROM ef) AS soggetto_ruolo_id,
  (SELECT ef1_id FROM ef)            AS emittente_fiscale_id,
  (SELECT ef2_id FROM ef)            AS emittente_fiscale_id_alt,
  (SELECT s.id
     FROM config.stati_doc_ordini s
    WHERE s.attivo IS TRUE
    ORDER BY s.id LIMIT 1)           AS stato_doc_ordine_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1)           AS valuta_id,
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
  dbops.fn_pgtap_crea_articolo('PGT-ORIT-ART', false)                         AS articolo_id,
  -- La UoM dell'articolo costruito: la prima attiva per id, come in
  -- dbops.fn_pgtap_crea_articolo.
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo ORDER BY u.id LIMIT 1) AS uom_operativa_id,
  (SELECT id FROM iva1)              AS iva1_id,
  (SELECT aliquota_iva FROM iva1)    AS iva1_aliquota,
  (SELECT id FROM iva2)              AS iva2_id,
  (SELECT aliquota_iva FROM iva2)    AS iva2_aliquota;

SELECT ok(
  (
    SELECT soggetto_ruolo_id IS NOT NULL
       AND emittente_fiscale_id IS NOT NULL
       AND stato_doc_ordine_id IS NOT NULL
       AND articolo_id IS NOT NULL
       AND uom_operativa_id IS NOT NULL
       AND iva1_id IS NOT NULL
      FROM tmp_ordiva_refs
  ),
  '6. riferimenti minimi disponibili per test funzionali'
);

CREATE TEMP TABLE tmp_ordiva_ordine(id bigint);

-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-1): l'ordine ha sempre il
--   billing account, e il suo cliente e' il ruolo del BA. Prima nasceva col BA
--   NULL e col ruolo dell'emittente come cliente. Il cliente si fabbrica: il
--   trigger z90 lega il suo BA all'emittente dell'operatore in sessione, che
--   e' quello dell'ordine (il guard di scope lo pretende).
CREATE TEMP TABLE tmp_ordiva_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('ordini riepilogo iva');
SET CONSTRAINTS ALL IMMEDIATE;

WITH ins AS (
  INSERT INTO vendite.ordini (
    serie, numero, anno, data,
    soggetto_ruolo_id, billing_account_id,
    stato_doc_ordine_id, valuta_id, emittente_fiscale_id,
    storicizza, meta
  )
  SELECT
    'PGTAP',
    'ORDIVA-' || substr(md5(clock_timestamp()::text), 1, 10),
    2080,
    DATE '2080-06-01',
    (SELECT c.soggetto_ruolo_id FROM tmp_ordiva_cli c),
    (SELECT c.billing_account_id FROM tmp_ordiva_cli c),
    r.stato_doc_ordine_id,
    r.valuta_id,
    anagrafiche.fn_get_emittente_fiscale_pk((SELECT c.billing_account_id FROM tmp_ordiva_cli c)),
    false,
    jsonb_build_object('test_scope', 'pgtap_ordini_riepilogo_iva')
  FROM tmp_ordiva_refs r
  WHERE r.soggetto_ruolo_id IS NOT NULL
    AND r.emittente_fiscale_id IS NOT NULL
    AND r.stato_doc_ordine_id IS NOT NULL
    AND r.articolo_id IS NOT NULL
    AND r.uom_operativa_id IS NOT NULL
    AND r.iva1_id IS NOT NULL
  RETURNING id
)
INSERT INTO tmp_ordiva_ordine(id)
SELECT id
  FROM ins;

-- ============================================================
-- 7) Funzione su ordine senza righe -> totali zero
-- ============================================================
CREATE TEMP TABLE tmp_ordiva_zero(
  ordine_id bigint,
  imponibile_tot numeric,
  sconto_tot numeric,
  iva_tot numeric,
  totale_doc numeric
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM tmp_ordiva_ordine) THEN
    INSERT INTO tmp_ordiva_zero
    SELECT * FROM vendite.fn_ricalcola_totali_ordine(
      (SELECT id FROM tmp_ordiva_ordine)
    );
  END IF;
END;
$$;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ordiva_ordine)
  THEN skip('7. riferimenti insufficienti: ordine test non creato')
  ELSE ok(
    (SELECT imponibile_tot = 0 AND sconto_tot = 0 AND iva_tot = 0 AND totale_doc = 0
       FROM tmp_ordiva_zero),
    '7. fn_ricalcola_totali_ordine: ordine senza righe -> totali zero'
  )
END;

-- ============================================================
-- Inserisce tre righe stessa IVA: 3 * 0.333 = 0.999 -> ROUND(SUM) = 1.00
-- ============================================================
CREATE TEMP TABLE tmp_ordiva_righe(id bigint, riga_nr integer);

WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, uom_operativa_id, quantita,
    prezzo_unitario, sconto_percentuale, iva_id,
    attivo, meta
  )
  SELECT
    o.id,
    gs.riga_nr,
    r.articolo_id,
    'PGTAP IVA stessa aliquota ' || gs.riga_nr::text,
    1,
    r.uom_operativa_id,
    1,
    0.333,
    0,
    r.iva1_id,
    true,
    jsonb_build_object('test_scope', 'pgtap_ordini_riepilogo_iva')
  FROM tmp_ordiva_ordine o
  CROSS JOIN tmp_ordiva_refs r
  CROSS JOIN generate_series(1, 3) AS gs(riga_nr)
  RETURNING id, riga_nr
)
INSERT INTO tmp_ordiva_righe(id, riga_nr)
SELECT id, riga_nr
  FROM ins;

-- ============================================================
-- 8) Stessa IVA -> una riga riepilogo
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ordiva_ordine)
  THEN skip('8. riferimenti insufficienti: ordine test non creato')
  ELSE is(
    (SELECT COUNT(*)::integer
       FROM vendite.vw_ordini_riepilogo_iva_dettaglio
      WHERE ordine_id = (SELECT id FROM tmp_ordiva_ordine)),
    1,
    '8. stessa IVA su piu righe -> una riga riepilogo'
  )
END;

-- ============================================================
-- 9) Centesimi: ROUND(SUM), non SUM(ROUND)
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ordiva_ordine)
  THEN skip('9. riferimenti insufficienti: ordine test non creato')
  ELSE is(
    (SELECT imponibile
       FROM vendite.vw_ordini_riepilogo_iva_dettaglio
      WHERE ordine_id = (SELECT id FROM tmp_ordiva_ordine)
      LIMIT 1),
    1.00::numeric,
    '9. centesimi: 3 * 0.333 -> imponibile aggregato ROUND(SUM)=1.00'
  )
END;

-- ============================================================
-- 10) Riga inattiva esclusa
-- ============================================================
INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, uom_operativa_id, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, meta
)
SELECT
  o.id, 90, r.articolo_id, 'PGTAP IVA riga inattiva',
  1, r.uom_operativa_id, 1, 9999, 0, r.iva1_id,
  false, jsonb_build_object('test_scope', 'pgtap_ordini_riepilogo_iva')
FROM tmp_ordiva_ordine o
CROSS JOIN tmp_ordiva_refs r;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ordiva_ordine)
  THEN skip('10. riferimenti insufficienti: ordine test non creato')
  ELSE is(
    (SELECT imponibile
       FROM vendite.vw_ordini_riepilogo_iva_dettaglio
      WHERE ordine_id = (SELECT id FROM tmp_ordiva_ordine)
      LIMIT 1),
    1.00::numeric,
    '10. riga inattiva esclusa dal riepilogo IVA'
  )
END;

-- ============================================================
-- 11) IVA diverse -> piu righe riepilogo
-- ============================================================
INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, uom_operativa_id, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, meta
)
SELECT
  o.id, 91, r.articolo_id, 'PGTAP IVA diversa',
  1, r.uom_operativa_id, 1, 10, 0, r.iva2_id,
  true, jsonb_build_object('test_scope', 'pgtap_ordini_riepilogo_iva')
FROM tmp_ordiva_ordine o
CROSS JOIN tmp_ordiva_refs r
WHERE r.iva2_id IS NOT NULL;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ordiva_ordine)
  THEN skip('11. riferimenti insufficienti: ordine test non creato')
  WHEN (SELECT iva2_id IS NULL FROM tmp_ordiva_refs)
  THEN skip('11. una sola aliquota IVA disponibile nei dati di test')
  ELSE is(
    (SELECT COUNT(*)::integer
       FROM vendite.vw_ordini_riepilogo_iva_dettaglio
      WHERE ordine_id = (SELECT id FROM tmp_ordiva_ordine)),
    2,
    '11. IVA diverse -> piu righe riepilogo'
  )
END;

-- ============================================================
-- 12) Funzione aggiorna testata sommando il riepilogo
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ordiva_ordine)
  THEN skip('12. riferimenti insufficienti: ordine test non creato')
  ELSE ok(
    (
      SELECT o.imponibile_tot = COALESCE(SUM(r.imponibile), 0)
         AND o.iva_tot        = COALESCE(SUM(r.imposta), 0)
         AND o.totale_doc     = COALESCE(SUM(r.totale_riga), 0)
        FROM vendite.ordini o
        LEFT JOIN vendite.vw_ordini_riepilogo_iva_dettaglio r
          ON r.ordine_id = o.id
       WHERE o.id = (SELECT id FROM tmp_ordiva_ordine)
       GROUP BY o.id, o.imponibile_tot, o.iva_tot, o.totale_doc
    ),
    '12. fn/trigger aggiornano testata sommando il riepilogo IVA'
  )
END;

-- ============================================================
-- 13) Trigger righe UPDATE ricalcola totali
-- ============================================================
UPDATE vendite.ordini
   SET imponibile_tot = -999,
       iva_tot = -999,
       totale_doc = -999
 WHERE id = (SELECT id FROM tmp_ordiva_ordine);

UPDATE vendite.ordini_righe
   SET prezzo_unitario = 1.333
 WHERE id = (SELECT id FROM tmp_ordiva_righe WHERE riga_nr = 1);

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ordiva_ordine)
  THEN skip('13. riferimenti insufficienti: ordine test non creato')
  ELSE ok(
    (
      SELECT o.imponibile_tot = COALESCE(SUM(r.imponibile), 0)
         AND o.iva_tot        = COALESCE(SUM(r.imposta), 0)
         AND o.totale_doc     = COALESCE(SUM(r.totale_riga), 0)
         AND o.imponibile_tot <> -999
        FROM vendite.ordini o
        LEFT JOIN vendite.vw_ordini_riepilogo_iva_dettaglio r
          ON r.ordine_id = o.id
       WHERE o.id = (SELECT id FROM tmp_ordiva_ordine)
       GROUP BY o.id, o.imponibile_tot, o.iva_tot, o.totale_doc
    ),
    '13. trigger UPDATE ordini_righe ricalcola i totali testata'
  )
END;

-- ============================================================
-- 14) Trigger righe DELETE registrato con transition table
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
      FROM pg_trigger t
     WHERE t.tgrelid = 'vendite.ordini_righe'::regclass
       AND t.tgname = 'trg_ordini_righe_z90_ricalcola_totali_dlt'
       AND NOT t.tgisinternal
       AND pg_get_triggerdef(t.oid) ILIKE '%AFTER DELETE%'
       AND pg_get_triggerdef(t.oid) ILIKE '%OLD TABLE AS old_rows%'
  ),
  '14. trigger DELETE ordini_righe registrato con transition table old_rows'
);

-- ============================================================
-- 15) L'emittente dell'ordine fuori bozza e' bloccato, dichiarato
-- ============================================================
-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, §9.8): prima questo passo
--   spostava l'ordine su un altro emittente (da super admin) per collaudare il
--   ricalcolo dei totali. Il cambio non ha piu' un caso legittimo: in bozza lo
--   lega al BA il guard emittente <-> BA, fuori bozza lo vieta il lock
--   trg_ordini_a05_lock_fuori_bozza_upd (E_DOC_EMITTENTE_FUORI_BOZZA). Il
--   comportamento lo prova test-esecutivi-ba-coppia-v1; qui il montaggio.
SELECT ok(
  EXISTS (
    SELECT 1
      FROM pg_trigger t
     WHERE t.tgrelid = 'vendite.ordini'::regclass
       AND t.tgname = 'trg_ordini_a05_lock_fuori_bozza_upd'
       AND NOT t.tgisinternal
       AND 'emittente_fiscale_id' = ANY (dbops.fn_trigger_argomenti(t.tgargs))
  ),
  '15. l''emittente dell''ordine e'' bloccato fuori bozza (BB di testata)'
);

-- ============================================================
-- 16) BoM: la view base non legge direttamente i componenti
-- ============================================================
SELECT ok(
  pg_get_viewdef('vendite.vw_ordini_righe_iva_base'::regclass, true)
    NOT ILIKE '%ordini_righe_componenti%',
  '16. BoM: vw_ordini_righe_iva_base non legge ordini_righe_componenti, quindi evita doppio conteggio'
);

-- ============================================================
-- 17) Nessun id tecnico nel riepilogo derivato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
      FROM information_schema.columns
     WHERE table_schema = 'vendite'
       AND table_name = 'vw_ordini_riepilogo_iva_dettaglio'
       AND column_name = 'id'
  ),
  '17. vw_ordini_riepilogo_iva_dettaglio non espone id tecnico'
);

-- ============================================================
-- 18) Guard funzione parametro nullo
-- ============================================================
SELECT throws_like(
  $$ SELECT * FROM vendite.fn_ricalcola_totali_ordine(NULL) $$,
  '%Parametro non valido%',
  '18. fn_ricalcola_totali_ordine: p_ordine_id NULL -> errore'
);

SELECT * FROM finish();
ROLLBACK;
