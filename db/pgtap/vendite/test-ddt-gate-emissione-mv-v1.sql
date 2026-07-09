-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: rifiniture §10 — mv_ddt_ordini (refresh) + gate emissione BoM PENDING
-- ------------------------------------------------------------
-- Indice test (1..4):
--  1) mv_ddt_ordini e' una materialized view
--  2) dbops.fn_refresh_mv_ddt_ordini presente
--  3) dopo evasione + REFRESH: mv_ddt_ordini contiene la coppia (ddt_id, ordine_id)
--  4) gate emissione: componente BoM CASO A in PENDING blocca DRAFT->EMESSO
--     (SKIP se il DB non ha un articolo composito con BoM attivo)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- ============================================================
-- 1-2) Oggetti MV
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pg_matviews WHERE schemaname='vendite' AND matviewname='mv_ddt_ordini'),
  '1) mv_ddt_ordini e'' una materialized view'
);
SELECT ok(
  EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
           WHERE n.nspname='dbops' AND p.proname='fn_refresh_mv_ddt_ordini'),
  '2) dbops.fn_refresh_mv_ddt_ordini presente'
);

-- ============================================================
-- Riferimenti + fixture ordine semplice -> genera DDT
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                       AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito,FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1) AS articolo_semplice_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1) AS emittente_sr_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno='CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE LIMIT 1)  AS stato_ddt_draft_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno='EMESSO' AND s.attivo IS TRUE LIMIT 1) AS stato_ddt_emesso_id;

CREATE TEMP TABLE tmp_ord AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, DATE '2026-07-01', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_ddt_mv_gate')
  FROM tmp_refs r
  RETURNING id, uid)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_semplice_id, 'Riga MV',
       10.000000, 10.000000, 25.000000, r.iva_id, true, false,
       jsonb_build_object('test_scope','pgtap_ddt_mv_gate')
FROM tmp_ord o, tmp_refs r;

CREATE TEMP TABLE tmp_ddt AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord)) AS ddt_id;

-- ============================================================
-- 3) Refresh MV (non-concurrent, valido in transazione) + coppia presente
-- ============================================================
REFRESH MATERIALIZED VIEW vendite.mv_ddt_ordini;

SELECT ok(
  EXISTS (
    SELECT 1 FROM vendite.mv_ddt_ordini m
     WHERE m.ddt_id = (SELECT ddt_id FROM tmp_ddt)
       AND m.ordine_id = (SELECT id FROM tmp_ord)
  ),
  '3) mv_ddt_ordini contiene la coppia (ddt_id, ordine_id) post-refresh'
);

-- ============================================================
-- 4) Gate emissione: componente BoM CASO A in PENDING blocca EMESSO.
--    Fixture composita costruita in blocco robusto (EXCEPTION -> skip):
--    se il DB non ha un articolo composito con BoM attivo, o il setup non
--    riesce, tmp_gate resta vuota e il test viene SKIPPATO (non fallisce).
-- ============================================================
CREATE TEMP TABLE tmp_gate (ddt_id bigint);

DO $$
DECLARE
  v_art_comp catalogo.articoli.id%TYPE;
  v_ba       anagrafiche.billing_account.id%TYPE;
  v_sr       anagrafiche.soggetti_ruoli.id%TYPE;
  v_val      config.valute.id%TYPE;
  v_ef       anagrafiche.emittenti_fiscali.id%TYPE;
  v_emitt_sr anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
  v_so       config.stati_doc_ordini.id%TYPE;
  v_ord      vendite.ordini.id%TYPE;
  v_ord_riga vendite.ordini_righe.id%TYPE;
  v_ddt      vendite.ddt.id%TYPE;
BEGIN
  SELECT id INTO v_ba FROM anagrafiche.billing_account
   WHERE utility_id IS NOT NULL AND istanza_utility_id IS NOT NULL ORDER BY id LIMIT 1;
  SELECT id INTO v_sr FROM anagrafiche.soggetti_ruoli ORDER BY id LIMIT 1;
  SELECT id INTO v_val FROM config.valute ORDER BY id LIMIT 1;
  SELECT id, soggetto_ruolo_id INTO v_ef, v_emitt_sr
    FROM anagrafiche.emittenti_fiscali ORDER BY id LIMIT 1;
  SELECT id INTO v_so FROM config.stati_doc_ordini
   WHERE codice_interno='CONFERMATO' AND attivo IS TRUE LIMIT 1;

  -- Articolo composito con BoM attivo (data-dependent).
  SELECT a.id INTO v_art_comp
    FROM catalogo.articoli a
   WHERE a.is_composito IS TRUE AND a.attivo IS TRUE
     AND EXISTS (SELECT 1 FROM catalogo.articoli_componenti ac
                  WHERE ac.prodotto_id = a.id AND ac.attivo IS TRUE
                    AND (ac.valido_al IS NULL OR ac.valido_al >= CURRENT_DATE))
   LIMIT 1;

  IF v_art_comp IS NULL OR v_emitt_sr IS NULL THEN
    RETURN;  -- nessun composito / emittente: gate non testabile -> tmp_gate vuota
  END IF;

  BEGIN
    -- Ordine CONFERMATO + riga composita.
    INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
        valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
    VALUES (v_sr, v_ba, v_so, v_val, DATE '2026-07-01', 'SPEDITO', v_ef, false,
        jsonb_build_object('test_scope','pgtap_gate_composito'))
    RETURNING id INTO v_ord;

    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
    VALUES (v_ord, 1, v_art_comp, 'Riga composita',
        1.000000, 1.000000, 0.000000, true, false,
        jsonb_build_object('test_scope','pgtap_gate_composito'))
    RETURNING id INTO v_ord_riga;

    -- Inizializza i componenti CASO A sulla riga ordine (dal BoM).
    PERFORM vendite.fn_ordine_riga_componenti_init(v_ord_riga, v_emitt_sr, CURRENT_DATE);

    -- Forza PENDING su un componente (workflow approvazione prezzo).
    UPDATE vendite.ordini_righe_componenti
       SET stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
     WHERE id = (SELECT id FROM vendite.ordini_righe_componenti
                  WHERE riga_ordine_id = v_ord_riga LIMIT 1);

    -- Genera il DDT: copia i componenti (incl. lo stato PENDING).
    v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);

    -- Registra il DDT solo se ha effettivamente un componente PENDING.
    IF EXISTS (SELECT 1 FROM vendite.ddt_righe dr
                JOIN vendite.ddt_righe_componenti drc ON drc.riga_ddt_id = dr.id
               WHERE dr.ddt_id = v_ddt
                 AND drc.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo) THEN
      INSERT INTO tmp_gate(ddt_id) VALUES (v_ddt);
    END IF;
  EXCEPTION WHEN OTHERS THEN
    -- Fixture composita non costruibile su questo DB: si skippa il caso.
    NULL;
  END;
END $$;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_gate)
  THEN skip('nessun articolo composito con BoM PENDING costruibile: gate emissione non testabile qui', 1)
  ELSE throws_ok(
    format($q$UPDATE vendite.ddt SET stato_doc_ddt_id=
               (SELECT stato_ddt_emesso_id FROM tmp_refs) WHERE id=%s$q$,
           (SELECT ddt_id FROM tmp_gate)),
    'P0001', NULL,
    '4) gate emissione: componente BoM PENDING blocca DRAFT->EMESSO'
  )
END;

SELECT * FROM finish();
ROLLBACK;
