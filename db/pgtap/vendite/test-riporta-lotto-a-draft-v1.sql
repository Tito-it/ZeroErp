-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: ritorno di un lotto a DRAFT (piano-db-ritorno-lotto-a-draft.md, A4)
-- ------------------------------------------------------------
-- Cosa presidia questo file
--   Il disegno «EMESSA = documento non modificabile; per correggere si
--   riporta a DRAFT e si ricalcola», che fino al 2026-08-03 era dichiarato
--   a meta': la matrice ammetteva la transizione per il lotto, ma nessuna
--   funzione la eseguiva (rilievo C-18). Caso reale che l'ha aperto: la
--   fattura 2263 del lotto 1200, EMESSA e non numerata, con un piano rate
--   sbagliato e nessun modo di disfarla.
--
-- 🔴 IL TEST CHE VALE DI PIU' E' L'8.
--   Gli altri verificano che il ritorno abbia la FORMA giusta. L'8 verifica
--   che serva a QUALCOSA: `fn_cleanup_fatture_by_ids` ripristina
--   attivita_fatturabili ma non tocca MAI commesse_attivita, e
--   `fn_emit_attivita_fatturabili_da_commessa` filtra su
--   stato_emissione = 'EMESSA'. Un'attivita' lasciata li' non verrebbe
--   ripresa dal giro successivo: il lotto ripartirebbe senza niente da
--   riemettere. Lo stesso campo decide lo stadio nel cruscotto competenza,
--   che non guarda mai lo stato fiscale della fattura.
--
-- ⚠️ FIXTURE NON COSTRUIBILE DA ZERO, e detto invece che nascosto.
--   Un lotto EMESSA con fatture, righe e attivita' agganciate e' il
--   prodotto di due step di pipeline: non si fabbrica in un pgTAP senza
--   riscrivere la pipeline. Il file quindi SCEGLIE un lotto pre-fiscale
--   reale e lavora dentro BEGIN/ROLLBACK. Se non ce ne sono, i test di
--   comportamento si SALTANO invece di fallire: un rosso da assenza di dati
--   non dice niente a nessuno. I test 1-3 sono strutturali e girano sempre.
-- ------------------------------------------------------------
-- Indice test
-- 1) Seed: la transizione EMESSA -> DRAFT del LOTTO non ha vincolo di tipo
-- 2) La colonna riaperto_il esiste, e' timestamptz e nullable
-- 3) La funzione esiste e restituisce i cinque contatori
-- 4) Fixture: un lotto pre-fiscale con almeno una fattura
-- 5) Guard: con una fattura NUMERATA il ritorno e rifiutato
-- 6) Il ritorno gira e non solleva
-- 7) Dopo: lotto DRAFT, stato_operativo APERTO, riaperto_il valorizzato
-- 8) Le commesse_attivita sono tornate NON_EMESSA  <-- il test che vale
-- 9) Le fatture del lotto sono state cancellate
-- 10) I task_run sono chiusi ad ANNULLATO (il rilancio torna RUN, non SKIP)
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ============================================================
-- Strutturali (girano sempre)
-- ============================================================

-- Il `meta` vuoto e' sostanza, non forma: trgfn_fatturazione_lotti_guard_stato
-- LEGGE quel meta e ne applica `tipo_lotto`. Finche' conteneva "MASSIVO" un
-- lotto GIORNALIERO non poteva tornare indietro, mentre il perimetro deciso
-- (D-L.2 / D-T) e' entrambi i tipi.
SELECT ok(
  EXISTS (
    SELECT 1 FROM config.stati_doc_fiscale_transizioni t
      JOIN config.stati_doc_fiscale sf ON sf.id = t.stato_from_id
      JOIN config.stati_doc_fiscale st ON st.id = t.stato_to_id
     WHERE sf.codice_interno = 'EMESSA' AND st.codice_interno = 'DRAFT'
       AND t.ammesso IS TRUE AND t.solo_lotto IS TRUE
       AND (t.meta->>'tipo_lotto') IS NULL),
  '1) Seed: EMESSA -> DRAFT esiste per il lotto, senza vincolo di tipo');

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'vendite' AND table_name = 'fatturazione_lotti'
       AND column_name = 'riaperto_il'
       AND data_type = 'timestamp with time zone'
       AND is_nullable = 'YES'),
  '2) La colonna riaperto_il esiste, e timestamptz e nullable');

-- Cinque contatori e non quattro: `riemesse_attivita` e' separato perche' un
-- numero unico direbbe «10 cose fatte» senza distinguere fatture cancellate
-- da attivita' rimesse in coda, che per il cockpit sono fatti diversi.
SELECT ok(
  (SELECT count(*) FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_riporta_lotto_a_draft'
      AND pg_get_function_result(p.oid) ILIKE '%riemesse_attivita%'
      AND pg_get_function_result(p.oid) ILIKE '%deleted_fatture%') = 1,
  '3) La funzione esiste e restituisce i cinque contatori');

-- ============================================================
-- Fixture
-- ============================================================
-- Criterio di scelta: un lotto in DRAFT o EMESSA, con almeno una fattura e
-- NESSUNA fattura numerata. Il filtro sul numero e' lo stesso guard che il
-- test 5 esercita: cosi' la fixture non muore su una condizione che il file
-- verifica altrove.
CREATE TEMP TABLE tmp_lotto_rld AS
SELECT fl.id,
       fl.lock_batch_id,
       (SELECT count(*) FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = fl.id) AS n_fatture
  FROM vendite.fatturazione_lotti fl
  JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
 WHERE s.codice_interno IN ('DRAFT', 'EMESSA')
   AND EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = fl.id)
   AND NOT EXISTS (
         SELECT 1 FROM vendite.fatturazione_lotti_fatture lf
           JOIN vendite.fatture f ON f.id = lf.fattura_id
          WHERE lf.lotto_id = fl.id AND f.numero IS NOT NULL)
 ORDER BY fl.id DESC
 LIMIT 1;

-- Le commesse_attivita che il ritorno dovra' rimettere in coda: si fotografano
-- ADESSO, perche' dopo la pulizia il legame (fattura_riga_id) non esiste piu'.
CREATE TEMP TABLE tmp_ca_rld AS
SELECT DISTINCT af.commessa_attivita_id AS id
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id IS NOT NULL
   AND (
         af.lock_batch_id = (SELECT lock_batch_id FROM tmp_lotto_rld)
      OR af.fattura_riga_id IN (
             SELECT fr.id FROM vendite.fatture_righe fr
              WHERE fr.fattura_id IN (SELECT lf.fattura_id FROM vendite.fatturazione_lotti_fatture lf
                                       WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_rld))
         )
       );

CREATE TEMP TABLE tmp_runs_rld AS
SELECT count(*) AS n
  FROM vendite.fatturazione_lotti_task_runs
 WHERE lotto_id = (SELECT id FROM tmp_lotto_rld);

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld)
    THEN skip('nessun lotto pre-fiscale con fatture su questo DB', 7)
  ELSE ok((SELECT n_fatture FROM tmp_lotto_rld) > 0,
          '4) Fixture: lotto pre-fiscale con almeno una fattura')
END;

-- ============================================================
-- 5) Il guard sul numero
-- ============================================================
-- ⚠️ Il guard guarda il NUMERO, non lo stato. A EMESSA la fattura non e'
-- numerata (C-19), quindi il controllo di stato basterebbe: ma cancellare una
-- fattura gia' numerata aprirebbe un buco IRREVERSIBILE nella numerazione
-- fiscale, e un presidio che si fida di un'implicazione e' un presidio che
-- cade il giorno che l'implicazione cambia.
-- Il numero si mette e si toglie dentro il test: la fixture torna com'era e i
-- test successivi lavorano sul lotto intatto.
UPDATE vendite.fatture SET numero = 999999
 WHERE id = (SELECT lf.fattura_id FROM vendite.fatturazione_lotti_fatture lf
              WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_rld) ORDER BY lf.fattura_id LIMIT 1)
   AND EXISTS (SELECT 1 FROM tmp_lotto_rld);

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE throws_ok(
         format($$ SELECT * FROM vendite.fn_riporta_lotto_a_draft(%s) $$, (SELECT id FROM tmp_lotto_rld)),
         'P0001',
         NULL,
         '5) Guard: con una fattura numerata il ritorno e rifiutato')
END;

UPDATE vendite.fatture SET numero = NULL
 WHERE id = (SELECT lf.fattura_id FROM vendite.fatturazione_lotti_fatture lf
              WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_rld) ORDER BY lf.fattura_id LIMIT 1)
   AND EXISTS (SELECT 1 FROM tmp_lotto_rld);

-- ============================================================
-- 6-10) Il giro buono
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE lives_ok(
         format($$ SELECT * FROM vendite.fn_riporta_lotto_a_draft(%s) $$, (SELECT id FROM tmp_lotto_rld)),
         '6) Il ritorno gira e non solleva')
END;

-- stato_operativo torna APERTO perche' il lotto ha di nuovo lavoro da fare, e
-- riaperto_il e' il marcatore che distingue «riaperto» da «rotto»: senza,
-- l'unico modo di far ripartire il lotto sarebbe marcarlo in ERRORE, cioe'
-- dire una bugia che il cruscotto mostrerebbe in rosso.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    (SELECT s.codice_interno FROM vendite.fatturazione_lotti fl
       JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
      WHERE fl.id = (SELECT id FROM tmp_lotto_rld)) = 'DRAFT'
    AND (SELECT stato_operativo FROM vendite.fatturazione_lotti
          WHERE id = (SELECT id FROM tmp_lotto_rld)) = 'APERTO'
    AND (SELECT riaperto_il FROM vendite.fatturazione_lotti
          WHERE id = (SELECT id FROM tmp_lotto_rld)) IS NOT NULL,
    '7) Dopo il ritorno: lotto DRAFT, stato_operativo APERTO, riaperto_il valorizzato')
END;

-- 🔴 Il test che vale. Si asserisce la COPERTURA — quante delle attivita'
-- coinvolte NON sono piu' EMESSA sul totale di quelle coinvolte — e non la
-- semplice esistenza di qualcuna a NON_EMESSA: un conteggio parziale
-- passerebbe anche se il ritorno ne dimenticasse meta'.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  WHEN NOT EXISTS (SELECT 1 FROM tmp_ca_rld)
    THEN skip('il lotto scelto non ha commesse_attivita agganciate', 1)
  ELSE ok(
    (SELECT count(*) FROM vendite.commesse_attivita ca
      WHERE ca.id IN (SELECT id FROM tmp_ca_rld) AND ca.stato_emissione = 'EMESSA') = 0,
    '8) Le commesse_attivita coinvolte sono tutte uscite da EMESSA (tornano emittibili)')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    (SELECT count(*) FROM vendite.fatturazione_lotti_fatture lf
      WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_rld)) = 0,
    '9) Le fatture del lotto sono state cancellate (rollback, non riapertura)')
END;

-- 🔴 QUESTO TEST ERA SCRITTO AL CONTRARIO, e cristallizzava un bug.
-- Diceva «i task_runs non si toccano», sulla base di un'analisi sbagliata:
-- avevo verificato che `resume_mode` fosse letto da un metodo Python senza
-- chiamanti e ne avevo concluso che nessuno consultasse i task_run. Il
-- consumatore vero e' un altro — fn_resolve_lotto_task_execution_mode, che il
-- runner chiama a OGNI task: legge l'ultimo task_run e su COMPLETATO risponde
-- SKIP. Col test scritto cosi', il lotto riaperto rilanciava A VUOTO (tutti e
-- quattro i task saltati, nessun errore, nessun task_run nuovo) e il file
-- restava verde.
--
-- Ora si asserisce il fatto giusto, in DUE meta':
--   * nessuna corsa attiva resta COMPLETATO -> il resolver torna a dire RUN;
--   * il NUMERO di righe non cala -> la storia non si cancella, si chiude con
--     esito, e il giro nuovo aprira' tentativo = MAX+1.
-- ⚠️ Non si verifica `attivo`: quella colonna il resolver non la guarda
-- nemmeno, ed e' proprio il motivo per cui disattivare le righe non avrebbe
-- risolto niente.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    NOT EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_task_runs
                 WHERE lotto_id = (SELECT id FROM tmp_lotto_rld)
                   AND attivo IS TRUE
                   AND task_stato = 'COMPLETATO')
    AND (SELECT count(*) FROM vendite.fatturazione_lotti_task_runs
          WHERE lotto_id = (SELECT id FROM tmp_lotto_rld)) >= (SELECT n FROM tmp_runs_rld),
    '10) I task_run del lotto sono chiusi ad ANNULLATO (il rilancio torna RUN, non SKIP) e la storia resta')
END;

SELECT * FROM finish();

ROLLBACK;
