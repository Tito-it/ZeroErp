-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: config.stati_doc_fiscale.applica_lotto contro la matrice delle
--       transizioni (config.stati_doc_fiscale_transizioni)
-- ------------------------------------------------------------
-- Elenco test (plan 4):
-- 1) riferimenti minimi presenti: le due tabelle e le colonne lette (fixture non muta)
-- 2) ⭐ ogni stato di ARRIVO di una transizione ammessa ai lotti (solo_fattura = f)
--    ha applica_lotto = true — il flag dice cio' che la matrice permette
-- 3) ogni stato di PARTENZA di una transizione ammessa ai lotti ha applica_lotto = true
--    (un lotto deve poterci stare per poterne uscire)
-- 4) il caso che ha fatto nascere il test: ANNULLATA e' raggiungibile da un lotto
--    (DRAFT -> ANNULLATA ammessa, solo_fattura = f) E ha applica_lotto = true
--
-- Scopo:
--  - `applica_lotto` significa «stato valido per vendite.fatturazione_lotti»
--    (manuale del catalogo). Ma il guard `trgfn_fatturazione_lotti_guard_stato`
--    lo legge SOLO alla prima assegnazione: le transizioni passano dalla matrice
--    (`ammesso`, `solo_fattura`, `meta->>'tipo_lotto'`). Quindi il flag e la
--    matrice sono DUE sedi che dicono la stessa cosa, e niente le teneva
--    d'accordo: il 12-09-2026 il BE ha segnalato che ANNULLATA aveva
--    `applica_lotto = f` («stato non valido per un lotto») mentre DRAFT -> ANNULLATA
--    e' ammessa ai lotti massivi e giornalieri (D-T). Non bloccava nulla —
--    proprio perche' il guard non lo rilegge — ma il modello diceva il falso.
--  - Corretto nel CSV (80_data/sql/config/stati_doc_fiscale.csv, riga 7); questo
--    file e' il presidio: la prossima riga della matrice che porta un lotto in
--    uno stato con il flag a false e' rossa qui, non in una segnalazione in chat.
--  - ⛔ Il test NON pretende il contrario (flag true => raggiungibile): uno stato
--    puo' essere valido per un lotto senza che la matrice ce lo porti ancora
--    (REGISTRATA). La regola e' a un verso solo.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: il file legge solo due cataloghi, ma il preambolo e' lo
--   stesso per tutti — un file senza BEGIN e' un file che il guardrail respinge.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il test gira come `zeroerp_app`. I due cataloghi
--   non hanno RLS, ma la veste si dichiara comunque: e' il contratto del runner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: nessuna scrittura qui, ma la riga e' obbligatoria
--   (guardrail_pgtap_preambolo) e innocua.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- ============================================================
-- 1) Riferimenti minimi: se una colonna sparisse, i test 2-4 sarebbero verdi
--    per sottrazione (zero righe = zero violazioni). Qui si pretende che le
--    colonne lette ESISTANO, cosi' un rinomina fa rosso per il motivo giusto.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM information_schema.columns
      WHERE (table_schema, table_name, column_name) IN (
            ('config', 'stati_doc_fiscale', 'applica_lotto'),
            ('config', 'stati_doc_fiscale', 'codice_interno'),
            ('config', 'stati_doc_fiscale_transizioni', 'ammesso'),
            ('config', 'stati_doc_fiscale_transizioni', 'solo_fattura'),
            ('config', 'stati_doc_fiscale_transizioni', 'stato_from_id'),
            ('config', 'stati_doc_fiscale_transizioni', 'stato_to_id'))),
    6,
    '1) le sei colonne lette dai test esistono (fixture non muta)'
);

-- ============================================================
-- 2) ⭐ Stato di arrivo ammesso ai lotti => applica_lotto = true.
--    Si elencano i codici e non si conta: un rosso deve dire QUALE stato.
-- ============================================================
SELECT is(
    (SELECT COALESCE(string_agg(DISTINCT s.codice_interno, ',' ORDER BY s.codice_interno), '')
       FROM config.stati_doc_fiscale_transizioni t
       JOIN config.stati_doc_fiscale s ON s.id = t.stato_to_id
      WHERE t.ammesso
        AND t.solo_fattura = false
        AND s.applica_lotto = false),
    '',
    '2) nessuno stato di ARRIVO di una transizione ammessa ai lotti ha applica_lotto = false'
);

-- ============================================================
-- 3) Stato di partenza ammesso ai lotti => applica_lotto = true.
-- ============================================================
SELECT is(
    (SELECT COALESCE(string_agg(DISTINCT s.codice_interno, ',' ORDER BY s.codice_interno), '')
       FROM config.stati_doc_fiscale_transizioni t
       JOIN config.stati_doc_fiscale s ON s.id = t.stato_from_id
      WHERE t.ammesso
        AND t.solo_fattura = false
        AND s.applica_lotto = false),
    '',
    '3) nessuno stato di PARTENZA di una transizione ammessa ai lotti ha applica_lotto = false'
);

-- ============================================================
-- 4) Il caso concreto, pinnato sul MODELLO (la transizione e' ammessa) e non
--    sul sintomo: se un giorno DRAFT -> ANNULLATA smettesse di essere ammessa
--    ai lotti, il test 2 resterebbe verde e questo direbbe perche'.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM config.stati_doc_fiscale_transizioni t
          JOIN config.stati_doc_fiscale sf ON sf.id = t.stato_from_id
          JOIN config.stati_doc_fiscale st ON st.id = t.stato_to_id
         WHERE sf.codice_interno = 'DRAFT'
           AND st.codice_interno = 'ANNULLATA'
           AND t.ammesso
           AND t.solo_fattura = false
           AND st.applica_lotto = true),
    '4) DRAFT -> ANNULLATA e'' ammessa ai lotti e ANNULLATA ha applica_lotto = true (segnalazione BE 12-09-2026)'
);

-- ⚠️ NIENTE cleanup in coda: ci pensa il ROLLBACK.
SELECT * FROM finish();
ROLLBACK;
