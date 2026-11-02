-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le viste SORGENTE delle righe di documento — preventivo, ordine, DDT
--   e distinta base — nella forma che la lista configurabile e i repository
--   leggono.
--   Brief: brief-db-liste-righe-documento §8.5 (D-8.5) e §8.6 (D-8.6).
--   changeSet: 20260928-17 (preventivo), -18 (ordine), -19 (DDT), -27 (BoM).
--
-- pgtap-contesto: escluso — il file legge solo il catalogo di PostgreSQL
--   (pg_class, pg_attribute, pg_get_viewdef): nessuna riga di dati, quindi un
--   contesto operatore non cambierebbe un risultato e darebbe l'impressione
--   che la RLS qui sia esercitata.
--
-- ⛔ COSA PRESIDIA. Tre cose che si perdono in silenzio:
--   · `security_invoker`: e' una reloption, non sta nel corpo, e un CREATE OR
--     REPLACE che non la ripete la azzera. Le tabelle righe sono in RLS: senza
--     il flag la vista gira come il suo owner, che ne e' esente;
--   · nessun ORDER BY nel corpo: l'ordine lo chiede chi legge (la whitelist del
--     BE). Il 20260502-13 ne aveva uno, tolto dal -17;
--   · le colonne che i consumatori leggono: il seed di ui.lista_colonna e i
--     repository nominano questi nomi. Una colonna rinominata qui farebbe
--     fallire il migrate del seed (trigger a10_valida_campo_sorgente), ma il
--     repository lo scoprirebbe solo a runtime.
-- ⚠️ NON presidia i VALORI: l'imponibile e' provato nella sede unica
--   (script/test-fn-imponibile-riga-v1); evaso e residuo dell'ordine sono la
--   stessa espressione della query Python che sostituiscono (brief §8.10).
--
-- Indice test (1..9):
--   1-3) security_invoker sulle tre viste di vendite
--   4)   nessun ORDER BY nel corpo delle quattro viste
--   5-7) le colonne di preventivo, ordine e DDT
--   8)   la distinta ha le due colonne che solo il repository aveva
--   9)   la capability di chiusura della distinta c'e' ancora
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ---- 1..3: security_invoker ------------------------------------------------
SELECT ok(
    (SELECT c.reloptions @> ARRAY['security_invoker=true'] FROM pg_class c
      WHERE c.oid = 'vendite.vw_preventivi_righe_dettaglio'::regclass),
    '1) vw_preventivi_righe_dettaglio: security_invoker (preventivi_righe e'' in RLS)');
SELECT ok(
    (SELECT c.reloptions @> ARRAY['security_invoker=true'] FROM pg_class c
      WHERE c.oid = 'vendite.vw_ordini_righe_dettaglio'::regclass),
    '2) vw_ordini_righe_dettaglio: security_invoker (ordini_righe e fulfillment in RLS)');
SELECT ok(
    (SELECT c.reloptions @> ARRAY['security_invoker=true'] FROM pg_class c
      WHERE c.oid = 'vendite.vw_ddt_righe_dettaglio'::regclass),
    '3) vw_ddt_righe_dettaglio: security_invoker (ddt_righe e'' in RLS)');

-- ---- 4: nessun ORDER BY ------------------------------------------------------
-- ⚠️ Si guarda il livello ESTERNO: pg_get_viewdef lo stampa in fondo. Un
--    ORDER BY dentro una sottoquery (string_agg, LIMIT 1) sarebbe legittimo.
SELECT is(
    (SELECT count(*)::integer FROM unnest(ARRAY[
        'vendite.vw_preventivi_righe_dettaglio'::regclass,
        'vendite.vw_ordini_righe_dettaglio'::regclass,
        'vendite.vw_ddt_righe_dettaglio'::regclass,
        'catalogo.vw_articoli_componenti_dettaglio'::regclass]) v
      WHERE pg_get_viewdef(v) ~* '\mORDER\s+BY\M[^()]*$'),
    0,
    '4) nessuna delle quattro viste ordina nel corpo');

-- ---- 5..7: le colonne dei consumatori ----------------------------------------
-- ⭐ `columns_are` e non una serie di has_column: pinna l'insieme INTERO, cosi'
--    anche una colonna in piu' o in meno e' un rosso che qualcuno deve leggere.
SELECT columns_are('vendite', 'vw_preventivi_righe_dettaglio', ARRAY[
    'id', 'preventivo_id', 'ordine', 'attivo', 'articolo_id', 'articolo_codice',
    'articolo_descrizione', 'descrizione', 'quantita', 'qta_operativa',
    'factor_to_base', 'uom_operativa_id', 'uom_codice', 'prezzo_unitario',
    'sconto_percentuale', 'iva_id', 'iva_codice', 'iva_descrizione', 'iva_aliquota',
    'importo_riga', 'imponibile_riga_full', 'meta', 'data_insert', 'data_update',
    'data_consegna_richiesta_cliente', 'stato_approvazione_prezzo',
    'pratica_approvazione_prezzo_id', 'is_composito_caso_a'],
    '5) righe preventivo: le colonne del repository, piu'' le quattro in coda');

SELECT columns_are('vendite', 'vw_ordini_righe_dettaglio', ARRAY[
    'id', 'ordine_id', 'riga_nr', 'attivo', 'articolo_id', 'articolo_codice',
    'articolo_descrizione', 'descrizione', 'quantita', 'qta_operativa',
    'factor_to_base', 'uom_operativa_id', 'uom_codice', 'prezzo_unitario',
    'sconto_percentuale', 'iva_id', 'iva_codice', 'iva_descrizione', 'iva_aliquota',
    'importo_riga', 'imponibile_riga_full', 'qta_evasa_operativa',
    'qta_residua_operativa', 'meta', 'data_insert', 'data_update',
    'data_consegna_richiesta_cliente', 'data_consegna_confermata',
    'is_composito_caso_a', 'data_consegna_confermata_blocco'],
    -- rev 2026-10-11 (20261012-07, brief-db-date-consegna-righe-in-blocco D-7):
    --   + data_consegna_confermata_blocco, il motivo per cui la data
    --   confermata della riga non si cambia (NULL = si cambia).
    '6) righe ordine: le colonne del repository, evaso e residuo compresi, piu'' il blocco della data confermata');

SELECT columns_are('vendite', 'vw_ddt_righe_dettaglio', ARRAY[
    'id', 'ddt_id', 'riga_nr', 'attivo', 'articolo_id', 'articolo_codice',
    'articolo_descrizione', 'descrizione', 'quantita', 'qta_operativa',
    'factor_to_base', 'uom_operativa_id', 'uom_codice', 'prezzo_unitario',
    'sconto_percentuale', 'iva_id', 'iva_codice', 'iva_descrizione', 'iva_aliquota',
    'importo_riga', 'imponibile_riga_full', 'meta', 'data_insert', 'data_update',
    'is_composito_caso_a',
    -- rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, 20261011-19): la riga
    -- evasa e il motivo per cui la sua quantita' evasa non si corregge ora.
    'evasa', 'correggi_qta_evasa_blocco'],
    '7) righe DDT: le colonne del repository');

-- ---- 8..9: la distinta base -------------------------------------------------
-- rev 2026-10-02: determina_qta_padre ritirata dalla distinta (20261002-60): la
-- vista porta l'esposizione e NON piu' i due flag senza effetto.
SELECT ok(
    (SELECT count(*) FILTER (WHERE attname = 'esposizione_in_fattura') = 1
        AND count(*) FILTER (WHERE attname IN ('determina_qta_padre', 'partecipa_qta')) = 0
       FROM pg_attribute
      WHERE attrelid = 'catalogo.vw_articoli_componenti_dettaglio'::regclass
        AND NOT attisdropped),
    '8) distinta: esposizione_in_fattura si, partecipa_qta e determina_qta_padre no (ritirate 2026-10-02)');

SELECT ok(
    (SELECT count(*) = 4 FROM pg_attribute
      WHERE attrelid = 'catalogo.vw_articoli_componenti_dettaglio'::regclass
        AND attname IN ('puo_chiudersi', 'data_min_chiusura',
                        'data_default_chiusura', 'motivo_non_chiudibile')
        AND NOT attisdropped),
    '9) distinta: la capability di chiusura resta nella vista, sede unica');

SELECT * FROM finish();
ROLLBACK;
