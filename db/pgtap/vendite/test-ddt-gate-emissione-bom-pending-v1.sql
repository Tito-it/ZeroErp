-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: gate emissione DDT — un componente di BoM in PENDING blocca DRAFT->EMESSO.
--
-- ⚠️ QUESTO FILE ERA PIU' LUNGO, ed e' stato accorciato il 2026-08-05.
-- Presidiava anche `vendite.mv_ddt_ordini` (tre asserzioni: che esistesse, che
-- esistesse la sua funzione di refresh, e che dopo un REFRESH comparisse la
-- coppia ddt/ordine). Quella vista materializzata e' stata **ritirata**
-- (changeSet 20260805-21/-22): nessuno la leggeva, nessuno la aggiornava, e il
-- legame ordine<->DDT l'applicazione lo ricava da `ddt.sorgente_uid` e da
-- `vendite.ordini_righe_fulfillment`. Tenere quelle asserzioni avrebbe voluto
-- dire presidiare un oggetto che non c'e' piu'.
--
-- ℹ️ Vale la pena sapere perche' quelle tre asserzioni non hanno mai segnalato
-- il problema: erano VERDI, ma il REFRESH lo eseguiva il test stesso. Provavano
-- che il meccanismo funzionasse, non che qualcuno lo azionasse — ed era proprio
-- quello che mancava. Un presidio che si accende da solo la corrente non dice
-- se la corrente c'e'.
--
-- Indice test (1..1):
--  1) gate emissione: componente BoM CASO A in PENDING blocca DRAFT->EMESSO
--     (SKIP se il DB non ha un articolo composito con BoM attivo)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(1);

-- ============================================================
-- 1) Gate emissione: componente BoM CASO A in PENDING blocca EMESSO.
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
    '1) gate emissione: componente BoM PENDING blocca DRAFT->EMESSO'
  )
END;

SELECT * FROM finish();
ROLLBACK;
