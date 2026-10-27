-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: chi annulla un lotto NON riscrive `stato_lotto`
--       (vendite.fn_annulla_lotto_da_draft)
-- ChangeSet: 20260907-08
-- Brief: brief-db-esito-gruppo-lotto §22 (il ritrovamento), §24 (la decisione)
--
-- Elenco test (plan 7, di cui 3 di servizio):
--   1) fixture: un lotto annullabile, portato a ERRORE
--   2) ⭐ dopo l'annullo `stato_lotto` e' ANCORA ERRORE
--   3) ...e l'annullo ha detto la sua dove gli compete: CHIUSO + ANNULLATA
--   4) ⭐ e su un lotto ANDATO BENE non inventa un errore che non c'e'
--   5) ⛔ il corpo della funzione non nomina piu' `stato_lotto` in scrittura
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO CHE PRESIDIA, e va letto perche' non e' ovvio.
--   Fino al 2026-09-07 l'annullo scriveva `stato_lotto = 'COMPLETATO'`. Un
--   lotto fallito e poi annullato smetteva di dire di essere fallito, e sono
--   TRE regole in una riga:
--     * `fn_set_fatturazione_lotto_stato` VIETA ERRORE -> COMPLETATO («da
--       ERRORE solo IN_ESECUZIONE»), e l'UPDATE diretto le passava dietro;
--     * la sorella `fn_riporta_lotto_a_draft` dichiara nel corpo «stato_lotto
--       NON si tocca», e l'intestazione dell'annullo invoca la simmetria con
--       lei come principio;
--     * `stato_lotto` risponde a «com'e' andata l'elaborazione»; «non e' piu'
--       in lavorazione» lo dicono gia' `stato_operativo` e
--       `stato_doc_fiscale_id`. Due domande su una colonna sola.
--
-- ⭐ IL TEST 4 E' QUELLO CHE TIENE ONESTO IL 2. Da solo, il 2 passerebbe anche
--   su una funzione che scrive SEMPRE 'ERRORE' — cioe' sullo stesso difetto
--   ribaltato. La coppia prova che l'annullo la colonna non la tocca affatto,
--   non che la scrive in un altro modo.
--
-- ⚠️ IL TEST 5 GUARDA IL TESTO, ed e' dichiarato: e' l'unico modo di dire «non
--   la scrive» invece di «oggi non l'ha scritta». Un presidio sul sorgente ha
--   per perimetro quella funzione, e va bene: la regola e' sua.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 0) Fixture — due lotti annullabili, uno rotto e uno sano
-- ============================================================
-- ⚠️ Si creano con la funzione applicativa, cosi' nascono con lo stato e i
--   riferimenti che avrebbero nel giro reale. Nessuna fattura attaccata: il
--   lotto vuoto e' annullabile dal 2026-08-01, ed e' la fixture piu' leggera
--   che esercita la stessa strada.
CREATE TEMP TABLE tmp_lotto_arw AS
SELECT vendite.fn_get_or_create_lotto(
         p_competenza_mese             => (date_trunc('month', script.fn_data_operativa()) + interval '7 month')::date,
         p_tipo_doc_fiscale_id         => (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1),
         p_utility_id                  => (SELECT ba.utility_id FROM anagrafiche.billing_account ba ORDER BY ba.id LIMIT 1),
         p_emittente_soggetto_ruolo_id => (SELECT f.emittente_soggetto_ruolo_id FROM vendite.fatture f ORDER BY f.id LIMIT 1),
         p_tipo_lotto                  => 'MASSIVO') AS id;

CREATE TEMP TABLE tmp_lotto_sano_arw AS
SELECT vendite.fn_get_or_create_lotto(
         p_competenza_mese             => (date_trunc('month', script.fn_data_operativa()) + interval '8 month')::date,
         p_tipo_doc_fiscale_id         => (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1),
         p_utility_id                  => (SELECT ba.utility_id FROM anagrafiche.billing_account ba ORDER BY ba.id LIMIT 1),
         p_emittente_soggetto_ruolo_id => (SELECT f.emittente_soggetto_ruolo_id FROM vendite.fatture f ORDER BY f.id LIMIT 1),
         p_tipo_lotto                  => 'MASSIVO') AS id;

-- ⭐ Lo stato si porta a ERRORE sotto la REGOLA UFFICIALE: se un domani la
--   macchina a stati cambiasse, questa fixture lo direbbe invece di costruire di
--   nascosto uno stato che il dominio non ammette piu'.
-- rev 2026-10-27 (brief-modello-documento-vendita §15, F-4): la regola non e' piu'
--   in vendite.fn_set_fatturazione_lotto_stato (ritirata, 20261027-07) ma nella
--   matrice config.transizioni_stati_lotto_job, che il guard
--   vendite.trgfn_fatturazione_lotti_guard_stato_job applica a ogni scrittura:
--   l'UPDATE e' la scrittura di sempre del runner, e IN_ESECUZIONE -> ERRORE e'
--   ammesso. Attese invariate.
UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'ERRORE'
 WHERE id = (SELECT id FROM tmp_lotto_arw);

SELECT is(
    (SELECT stato_lotto FROM vendite.fatturazione_lotti
      WHERE id = (SELECT id FROM tmp_lotto_arw)),
    'ERRORE',
    '1. fixture: il lotto e'' in ERRORE prima dell''annullo'
);

-- ============================================================
-- 2..3) L'annullo dice la sua dove gli compete, e SOLO li'
-- ============================================================
SELECT lives_ok(
    format($$SELECT * FROM vendite.fn_annulla_lotto_da_draft(%s)$$,
           (SELECT id FROM tmp_lotto_arw)),
    'l''annullo del lotto in errore non solleva'
);

-- ⭐ IL TEST PER CUI QUESTO FILE ESISTE. Prima del 20260907-08 qui c'era
--   'COMPLETATO': un lotto fallito smetteva di dire di esserlo, e il presidio
--   vw_lotti_chiusi_con_gruppi_in_errore si accendeva su ogni annullato che
--   aveva avuto un fallimento.
SELECT is(
    (SELECT stato_lotto FROM vendite.fatturazione_lotti
      WHERE id = (SELECT id FROM tmp_lotto_arw)),
    'ERRORE',
    '2. dopo l''annullo `stato_lotto` e'' ANCORA ERRORE: l''annullo non riscrive com''e'' andata'
);

-- ⚠️ E il verso complementare: togliere quella scrittura non doveva togliere
--   NIENT'ALTRO. L'annullo ha due colonne sue, e le scrive.
SELECT ok(
    (SELECT l.stato_operativo = 'CHIUSO' AND s.codice_interno = 'ANNULLATA'
       FROM vendite.fatturazione_lotti l
       JOIN config.stati_doc_fiscale s ON s.id = l.stato_doc_fiscale_id
      WHERE l.id = (SELECT id FROM tmp_lotto_arw)),
    '3. e l''annullo dice la sua dove gli compete: CHIUSO + ANNULLATA'
);

-- ============================================================
-- 4) ⭐ E su un lotto ANDATO BENE non inventa un errore
-- ============================================================
-- ⛔ Senza questo, il test 2 passerebbe anche su una funzione che scrive sempre
--   'ERRORE' — lo stesso difetto ribaltato. La coppia prova che la colonna non
--   viene TOCCATA, non che viene scritta in un altro modo.
-- ⚠️ Lo stato di PRIMA si cattura, non si riscrive nell'asserzione: un
--   confronto fra la colonna e se stessa passerebbe qualunque cosa faccia la
--   funzione.
DO $sano$
BEGIN
    PERFORM set_config('pgtap.stato_sano_prima',
        (SELECT stato_lotto FROM vendite.fatturazione_lotti
          WHERE id = (SELECT id FROM tmp_lotto_sano_arw)), true);

    PERFORM vendite.fn_annulla_lotto_da_draft((SELECT id FROM tmp_lotto_sano_arw));
END
$sano$;

SELECT isnt(
    current_setting('pgtap.stato_sano_prima', true), 'ERRORE',
    'il lotto sano non era in errore prima dell''annullo (guard della fixture)'
);

SELECT is(
    (SELECT stato_lotto FROM vendite.fatturazione_lotti
      WHERE id = (SELECT id FROM tmp_lotto_sano_arw)),
    current_setting('pgtap.stato_sano_prima', true),
    '4. su un lotto mai andato in errore l''annullo lascia lo stato che aveva'
);

-- ============================================================
-- 5) ⛔ «non la scrive», non «oggi non l'ha scritta»
-- ============================================================
-- ⚠️ Presidio sul TESTO della funzione, e il perimetro e' quella funzione: e'
--   l'unico modo di dire che la regola vale sempre e non solo sul caso provato
--   qui sopra. Cerca una SCRITTURA (`stato_lotto =`), non la parola: la
--   funzione puo' legittimamente LEGGERE quella colonna.
SELECT is(
    (SELECT count(*)::int
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname = 'fn_annulla_lotto_da_draft'
        AND EXISTS (
              SELECT 1
                FROM regexp_split_to_table(p.prosrc, E'\n') AS riga
               -- ⚠️ Le righe di commento si tolgono PRIMA: questo changeSet ne
               --   lascia parecchie che nominano `stato_lotto` per spiegare
               --   perche' non lo scrive piu'.
               WHERE riga !~ '^\s*--'
                 AND riga ~ 'stato_lotto\s*=')),
    0,
    '5. il corpo dell''annullo non contiene nessuna scrittura di `stato_lotto`'
);

SELECT * FROM finish();

ROLLBACK;
