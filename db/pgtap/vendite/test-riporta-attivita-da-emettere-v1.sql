-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il verbo «Riporta da emettere»
--       (brief-db-lavoro-che-non-torna-indietro, lotto L5 / D-4)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Il verbo deve recuperare le attivita' RESIDUE e rifiutare tutto il resto,
--   e le due cose valgono insieme: un verbo che recupera anche cio' che non e'
--   un residuo non e' un recupero, e' un modo di disfare lavoro corretto.
--
-- ⛔ IL PERIMETRO NON E' «CIO' CHE LA CARD MOSTRA»
--   La casella «Emesse non fatturate» del cruscotto competenza contiene DUE
--   popolazioni strutturalmente diverse: l'attivita' emessa che sta aspettando
--   il suo lotto (transito legittimo) e quella rimasta orfana dopo che la sua
--   fattura e' stata eliminata (il residuo). Un verbo fondato sulla card
--   disferebbe emissioni corrette. Le condizioni che discriminano sono
--   `fattura_riga_id IS NULL`, il lucchetto, `stato_esecuzione = COMPLETED`
--   — ed e' la terza a separare l'orfana dal giro VIVO — e, dal 20260912-35,
--   lo stato della RIGA DI COMMESSA con il marchio del giro: libera con la
--   riga NON_EMESSA e' «gia' disponibile» (motivo 3); libera con la riga
--   EMESSA e' DIVERGENTE — in transito se il marchio e' di un lotto in gioco
--   (motivo 5), riportabile altrimenti. Quest'ultima e' provata in
--   test-af-emessa-non-lockata-reset-e-riporto-v1, che la costruisce col pull.
--   I test 3-7 provano il primo caso, i test 8-11 provano che gli altri sono
--   rifiutati, ciascuno con il proprio codice.
--   🔴 rev 2026-09-12: fino a quel giorno la LIBERA aveva la riga EMESSA, e il
--   test 9 la chiamava «gia' disponibile». Sul modello nuovo quella coppia e'
--   la divergenza — e il verbo la ACCETTAVA, riallineandola: il test 9 era
--   rosso, e il 13 passava solo perche' il 9 aveva gia' mosso la riga. La
--   fixture ora costruisce cio' che il test dichiara: la riga NON_EMESSA.
--
-- ⛔ E IL PERIMETRO NON USA `fatturato`
--   Con la colonna generata prevista dal lotto L3b, «fatturato IS TRUE AND
--   fattura_riga_id IS NULL» diventerebbe sempre falso e il verbo smetterebbe
--   di funzionare IN SILENZIO. Questo file non costruisce nessuna fixture su
--   `fatturato`: se un giorno qualcuno lo rimettesse nel perimetro, i test 3-7
--   continuerebbero a passare oggi e cadrebbero il giorno di L3b.
--
-- ⭐ LA SIMMETRIA CHECK <-> MUTAZIONE (test 13) E' IL TEST CHE VALE
--   `fn_check_*` spiega PRIMA del click, la mutazione ferma DOPO. Se le due
--   metà divergono, l'interfaccia dice «si puo' fare» e il salvataggio
--   risponde di no — oppure, peggio, l'interfaccia nasconde un'azione che
--   sarebbe passata. Il test 13 le tiene attaccate.
--
-- ⚠️ FIXTURE COSTRUITE, non scelte: commessa, righe di commessa, lotto,
--   fattura, riga e quattro attivita' in quattro stati diversi sono INSERITE
--   da questo file. Solo i riferimenti anagrafici/di catalogo si scelgono
--   dall'esistente, come negli altri file di questa famiglia.
--
-- ⚠️ Il codice di errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
--   (contratto di script.fn_log_and_raise_error), non nello SQLSTATE: si legge
--   con GET STACKED DIAGNOSTICS, come fa test-riporta-lotto-a-draft-v1.
--
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Fixture: quattro attivita nei quattro stati, tre CA EMESSA e la LIBERA NON_EMESSA
-- 3) La check non trova motivi sull attivita ORFANA
-- 4) 🔴 Il verbo gira: riportate = 1 e riemesse_attivita = 1
-- 5) 🔴 L attivita e tornata libera
-- 6) 🔴 La commessa_attivita e tornata NON_EMESSA
-- 7) 🔴 L evento di log e stato scritto, con lock_batch_id e stato precedenti
-- 8) ⛔ Rifiuto: attivita ancora dentro una fattura
-- 9) Rifiuto: attivita gia da emettere (libera, riga NON_EMESSA: niente da riportare)
-- 10) Rifiuto: attivita dentro un giro VIVO
-- 11) Rifiuto: identificativo che non si risolve
-- 12) Rifiuto: elenco vuoto (errore di chiamante, non zero righe silenziose)
-- 13) ⭐ Simmetria: la check nomina lo stesso codice che la mutazione solleva
-- 14) ⛔ Il verbo NON imposta la GUC di manutenzione
-- 15) ⛔ Un rifiuto non tocca niente: l attivita in fattura e intatta
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. ⛔ Qui non e' un dettaglio: il
-- perimetro del verbo E' la RLS su vendite.commesse_attivita.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_cost_rde AS
SELECT 'pgtap_riporta_da_emettere'::text          AS test_scope,
       uuidv7()                                   AS lock_batch_id,
       script.fn_pgtap_emittente_sr_operatore()   AS emittente_sr_id;

CREATE TEMP TABLE tmp_refs_rde AS
WITH ba AS (
  SELECT b.id, b.utility_id, b.istanza_utility_id
    FROM anagrafiche.billing_account b
   WHERE b.utility_id IS NOT NULL
     AND b.istanza_utility_id IS NOT NULL
     AND b.soggetto_ruolo_id IS NOT NULL
   ORDER BY b.id
   LIMIT 1
)
SELECT
  (SELECT id FROM config.stati_doc_fiscale
    WHERE upper(btrim(codice_interno)) = 'DRAFT' ORDER BY id LIMIT 1) AS stato_draft_id,
  (SELECT id FROM ba)                 AS billing_account_id,
  (SELECT utility_id FROM ba)         AS utility_id,
  (SELECT istanza_utility_id FROM ba) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE
    ORDER BY a.id LIMIT 1)            AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)   AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)   AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY sc.id LIMIT 1)           AS stato_commessa_id,
  script.fn_pgtap_registro_fattura((SELECT emittente_sr_id FROM tmp_cost_rde))            AS registro_id;

SELECT ok(
  (SELECT r.stato_draft_id IS NOT NULL
      AND r.billing_account_id IS NOT NULL
      AND r.articolo_id IS NOT NULL
      AND r.uom_id IS NOT NULL
      AND r.tipo_doc_fiscale_id IS NOT NULL
      AND r.valuta_id IS NOT NULL
      AND r.stato_commessa_id IS NOT NULL
      AND r.registro_id IS NOT NULL
      AND (SELECT emittente_sr_id FROM tmp_cost_rde) IS NOT NULL
     FROM tmp_refs_rde r),
  '1) riferimenti minimi presenti (anagrafiche, catalogo, registro, emittente)'
);

-- ============================================================
-- Fixture: una commessa, QUATTRO righe di commessa già EMESSA
-- ============================================================
CREATE TEMP TABLE tmp_commessa_rde AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-RDE-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id,
         (SELECT emittente_sr_id FROM tmp_cost_rde), r.stato_commessa_id
    FROM tmp_refs_rde r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ca_rde (slot text PRIMARY KEY, attivita_id bigint);

-- ⚠️ uq_attivita_fatturabili_commessa_attivita e' 1:1: una riga di commessa
--   per ciascuna attivita'. Nascono EMESSA, che e' lo stato lasciato dalla
--   pipeline dopo l'emissione — ed e' cio' che rende significativo il test 6.
DO $fx$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['ORFANA', 'IN_FATTURA', 'LIBERA', 'VIVA'] LOOP
    -- ⚠️ Un INSERT che restituisce righe sta in una CTE, non in un FROM:
    --    PostgreSQL ammette le istruzioni di scrittura solo dentro WITH.
    WITH ins AS (
      INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
      SELECT (SELECT id FROM tmp_commessa_rde),
             'PGTAP-RDE-' || s || '-' || substr(md5(clock_timestamp()::text), 1, 12),
             r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
             date_trunc('month', script.fn_data_operativa())::date,
             date_trunc('month', script.fn_data_operativa())::date,
             (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
             r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
             -- ⭐ rev 2026-09-12: la LIBERA ha la riga NON_EMESSA. E' l'unica
             --   forma in cui «gia' disponibile» esiste ancora (motivo 3): con
             --   la riga EMESSA sarebbe la divergenza, che il verbo accetta.
             'BOZZA', CASE WHEN s = 'LIBERA' THEN 'NON_EMESSA' ELSE 'EMESSA' END,
             (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_commessa_rde))::text
        FROM tmp_refs_rde r
      RETURNING id)
    INSERT INTO tmp_ca_rde(slot, attivita_id) SELECT s, ins.id FROM ins;
  END LOOP;
END
$fx$;

-- Una fattura DRAFT con una riga, per il caso IN_FATTURA
CREATE TEMP TABLE tmp_fattura_rde AS
WITH ins AS (
  INSERT INTO vendite.fatture (registro_id, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id, tipo_doc_fiscale_id,
                               valuta_id, stato_doc_fiscale_id, data)
  SELECT r.registro_id, (SELECT emittente_sr_id FROM tmp_cost_rde),
         r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
         r.valuta_id, r.stato_draft_id, script.fn_data_operativa()
    FROM tmp_refs_rde r
  RETURNING id)
SELECT id AS fattura_id FROM ins;

CREATE TEMP TABLE tmp_riga_rde AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione,
                                     qta, prezzo_unitario, imponibile_riga, competenza_dal, competenza_al)
  SELECT f.fattura_id, 1, 'Riga PGTAP RDE', 1, 10, 10, script.fn_data_operativa(), script.fn_data_operativa()
    FROM tmp_fattura_rde f
  RETURNING id)
SELECT id AS riga_id FROM ins;

-- ============================================================
-- Le QUATTRO attivita', una per stato
-- ============================================================
--   ORFANA      → residuo vero: nessuna fattura, lucchettata, COMPLETED
--   IN_FATTURA  → agganciata a una riga viva
--   LIBERA      → nessun lucchetto, riga NON_EMESSA: gia' disponibile
--   VIVA        → lucchettata ma il giro non ha finito (PENDING)
CREATE TEMP TABLE tmp_af_rde (slot text PRIMARY KEY, attivita_id bigint);

DO $fx$
DECLARE
  s          text;
  v_riga     bigint;
  v_lock     boolean;
  v_batch    uuid;
  v_stato    text;
BEGIN
  FOREACH s IN ARRAY ARRAY['ORFANA', 'IN_FATTURA', 'LIBERA', 'VIVA'] LOOP
    v_riga  := CASE WHEN s = 'IN_FATTURA' THEN (SELECT riga_id FROM tmp_riga_rde) END;
    v_lock  := (s <> 'LIBERA');
    v_batch := CASE WHEN s <> 'LIBERA' THEN (SELECT lock_batch_id FROM tmp_cost_rde) END;
    v_stato := CASE WHEN s = 'VIVA' THEN 'PENDING'
                    WHEN s = 'LIBERA' THEN NULL
                    ELSE 'COMPLETED' END;

    WITH ins AS (
      INSERT INTO vendite.attivita_fatturabili (
            articolo_id, istanza_utility_id, billing_account_id, data_attivita,
            competenza_mese, competenza_dal, competenza_al, quantita, approvato,
            sospesa, tipo_doc_fiscale_id, valuta_id, commessa_id,
            commessa_attivita_id, uom_id, prezzo_unitario, lock_in_fatturazione,
            lock_batch_id, fattura_riga_id, stato_esecuzione, meta)
        SELECT r.articolo_id, r.istanza_utility_id, r.billing_account_id, script.fn_data_operativa(),
               date_trunc('month', script.fn_data_operativa())::date,
               date_trunc('month', script.fn_data_operativa())::date,
               (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
               1, true,
               -- ⚠️ `fatturato` NON si scrive: dal 20260826-33 e' una colonna
               --    GENERATA su `fattura_riga_id`. Lo stato che la pipeline
               --    lascerebbe si ottiene valorizzando il PUNTATORE, qui sotto.
               false,
               r.tipo_doc_fiscale_id, r.valuta_id,
               (SELECT id FROM tmp_commessa_rde),
               (SELECT attivita_id FROM tmp_ca_rde WHERE slot = s),
               r.uom_id, 10,
               v_lock, v_batch, v_riga, v_stato,
               jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_rde))
          FROM tmp_refs_rde r
      RETURNING id)
    INSERT INTO tmp_af_rde(slot, attivita_id) SELECT s, ins.id FROM ins;
  END LOOP;
END
$fx$;

SELECT ok(
  (SELECT count(*) = 4 FROM tmp_af_rde)
  AND (SELECT count(*) = 3 FROM vendite.commesse_attivita ca
        JOIN tmp_ca_rde t ON t.attivita_id = ca.id
       WHERE ca.stato_emissione = 'EMESSA')
  AND (SELECT ca.stato_emissione = 'NON_EMESSA' FROM vendite.commesse_attivita ca
        WHERE ca.id = (SELECT attivita_id FROM tmp_ca_rde WHERE slot = 'LIBERA'))
  AND (SELECT a.fattura_riga_id IS NULL AND a.lock_in_fatturazione IS TRUE
          AND a.stato_esecuzione = 'COMPLETED'
         FROM vendite.attivita_fatturabili a
        WHERE a.id = (SELECT attivita_id FROM tmp_af_rde WHERE slot = 'ORFANA'))
  AND (SELECT a.fattura_riga_id IS NOT NULL
         FROM vendite.attivita_fatturabili a
        WHERE a.id = (SELECT attivita_id FROM tmp_af_rde WHERE slot = 'IN_FATTURA'))
  AND (SELECT COALESCE(a.lock_in_fatturazione, false) IS FALSE
         FROM vendite.attivita_fatturabili a
        WHERE a.id = (SELECT attivita_id FROM tmp_af_rde WHERE slot = 'LIBERA'))
  AND (SELECT a.stato_esecuzione = 'PENDING'
         FROM vendite.attivita_fatturabili a
        WHERE a.id = (SELECT attivita_id FROM tmp_af_rde WHERE slot = 'VIVA')),
  '2) fixture: quattro attivita nei quattro stati; tre commesse_attivita EMESSA e la LIBERA NON_EMESSA'
);

-- ============================================================
-- 3) La check non ha niente da ridire sull ORFANA
-- ============================================================
SELECT is(
  script.fn_check_attivita_riportabile_da_emettere(
    ARRAY[(SELECT attivita_id FROM tmp_af_rde WHERE slot = 'ORFANA')]),
  '[]'::jsonb,
  '3) la check non trova motivi sull attivita ORFANA'
);

-- ============================================================
-- Il verbo, in un ISTRUZIONE SEPARATA dalle asserzioni
-- ============================================================
-- ⚠️ Chiamandolo dentro l asserzione, la snapshot di statement leggerebbe lo
--   stato PRIMA delle scritture e il rosso accuserebbe la funzione.
CREATE TEMP TABLE tmp_esito_rde AS
SELECT *
  FROM vendite.fn_riporta_attivita_da_emettere(
         ARRAY[(SELECT attivita_id FROM tmp_af_rde WHERE slot = 'ORFANA')]);

SELECT ok(
  (SELECT riportate = 1 AND riemesse_attivita = 1 FROM tmp_esito_rde),
  '4) il verbo riporta UNA attivita e riemette UNA riga di commessa'
);

SELECT ok(
  (SELECT a.fatturato IS FALSE
      AND a.fattura_riga_id IS NULL
      AND COALESCE(a.lock_in_fatturazione, false) IS FALSE
      AND a.lock_batch_id IS NULL
      AND a.stato_esecuzione IS NULL
     FROM vendite.attivita_fatturabili a
    WHERE a.id = (SELECT attivita_id FROM tmp_af_rde WHERE slot = 'ORFANA')),
  '5) l attivita e tornata libera (timbro, legame, lucchetto, stato)'
);

SELECT is(
  (SELECT ca.stato_emissione
     FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT attivita_id FROM tmp_ca_rde WHERE slot = 'ORFANA')),
  'NON_EMESSA'::character varying,
  '6) la commessa_attivita e tornata NON_EMESSA'
);

-- ============================================================
-- 7) La traccia, e cosa deve contenere
-- ============================================================
-- ⭐ Q-2: il verbo non chiede un motivo, ma il log e OBBLIGATORIO. E deve
--   portarsi dietro cio che la primitiva azzera — il lotto di provenienza e lo
--   stato di esecuzione — altrimenti «il lavoro e sparito da un lotto» resta
--   indistinguibile da un difetto.
SELECT ok(
  EXISTS (
    SELECT 1
      FROM vendite.commesse_attivita_log l
     WHERE l.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_rde WHERE slot = 'ORFANA')
       AND l.evento = 'RIGA_RIPORTATA_DA_EMETTERE'
       AND (l.dettaglio ->> 'attivita_fatturabile_id')::bigint
           = (SELECT attivita_id FROM tmp_af_rde WHERE slot = 'ORFANA')
       AND (l.dettaglio ->> 'lock_batch_id_precedente')::uuid
           = (SELECT lock_batch_id FROM tmp_cost_rde)
       AND l.dettaglio ->> 'stato_precedente' = 'COMPLETED'
  ),
  '7) l evento RIGA_RIPORTATA_DA_EMETTERE e scritto, col lotto e lo stato precedenti'
);

-- ============================================================
-- I rifiuti: un codice DEDICATO per ciascuno
-- ============================================================
-- ⚠️ Il codice viaggia nel canale CONSTRAINT_NAME dell eccezione (contratto di
--   script.fn_log_and_raise_error), non nello SQLSTATE.
CREATE OR REPLACE FUNCTION pg_temp.rde_codice(p_ids bigint[])
RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  PERFORM * FROM vendite.fn_riporta_attivita_da_emettere(p_ids);
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

-- E il gemello sulla check, che NON solleva sui motivi di dominio: si legge
-- il codice del primo motivo. Serve al test 13.
CREATE OR REPLACE FUNCTION pg_temp.rde_codice_check(p_ids bigint[])
RETURNS text AS $$
DECLARE v_motivi jsonb; v_cod text;
BEGIN
  v_motivi := script.fn_check_attivita_riportabile_da_emettere(p_ids);
  IF jsonb_array_length(v_motivi) = 0 THEN
    RETURN 'NESSUN MOTIVO';
  END IF;
  RETURN v_motivi -> 0 ->> 'codice';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

SELECT is(
  pg_temp.rde_codice(ARRAY[(SELECT attivita_id FROM tmp_af_rde WHERE slot = 'IN_FATTURA')]),
  'E_ATTIVITA_ANCORA_IN_FATTURA',
  '8) un attivita ancora dentro una fattura e rifiutata, e col codice giusto'
);

SELECT is(
  pg_temp.rde_codice(ARRAY[(SELECT attivita_id FROM tmp_af_rde WHERE slot = 'LIBERA')]),
  'E_ATTIVITA_GIA_DA_EMETTERE',
  '9) un attivita gia disponibile (libera, riga NON_EMESSA) e rifiutata: non c e niente da riportare'
);

SELECT is(
  pg_temp.rde_codice(ARRAY[(SELECT attivita_id FROM tmp_af_rde WHERE slot = 'VIVA')]),
  'E_ATTIVITA_IN_LAVORAZIONE',
  '10) un attivita dentro un giro VIVO e rifiutata: quel lotto non si tocca'
);

-- ⚠️ Id costruito per NON risolversi: massimo esistente + 1000. Non e' una
--   scommessa sui dati — e' un valore che per costruzione non e' ancora nato.
SELECT is(
  pg_temp.rde_codice(ARRAY[(SELECT COALESCE(max(id), 0) + 1000
                              FROM vendite.attivita_fatturabili)]),
  'E_ATTIVITA_FATTURABILE_NON_TROVATA',
  '11) un identificativo che non si risolve e rifiutato'
);

-- ⛔ L elenco vuoto NON deve poter uscire come «zero righe riportate»: sarebbe
--   indistinguibile da un operazione riuscita che non ha trovato niente.
SELECT is(
  pg_temp.rde_codice(ARRAY[]::bigint[]),
  'E_ATTIVITA_RIPORTO_SELEZIONE_VUOTA',
  '12) un elenco vuoto e un errore di chiamante, non zero righe silenziose'
);

-- ============================================================
-- 13) ⭐ Le due meta non si separano
-- ============================================================
-- ⛔ Se la check e la mutazione divergessero, l interfaccia direbbe «si puo
--   fare» e il salvataggio risponderebbe di no — oppure nasconderebbe un
--   azione che sarebbe passata. Il presidio e per CASO, su tutti e tre i
--   rifiuti che hanno una riga vera dietro.
SELECT is(
  (SELECT count(*)
     FROM (VALUES ('IN_FATTURA'), ('LIBERA'), ('VIVA')) AS s(slot)
    WHERE pg_temp.rde_codice(ARRAY[(SELECT attivita_id FROM tmp_af_rde t WHERE t.slot = s.slot)])
       IS DISTINCT FROM
          pg_temp.rde_codice_check(ARRAY[(SELECT attivita_id FROM tmp_af_rde t WHERE t.slot = s.slot)])),
  0::bigint,
  '13) la check nomina lo stesso codice che la mutazione solleva, su ogni rifiuto'
);

-- ============================================================
-- 14) ⛔ Il verbo non si apre la strada da solo
-- ============================================================
-- ⛔ trgfn_attivita_fatturabili_guard_fatturato rifiuta di toccare un attivita
--   ancora agganciata, salvo GUC di manutenzione. Se questo verbo impostasse
--   quella GUC diventerebbe il modo di SCOLLEGARE UNA FATTURA VIVA, e il test 8
--   smetterebbe di significare qualcosa.
-- ⚠️ Si legge il corpo SENZA i commenti: li dentro il nome della GUC compare,
--   di proposito, proprio per spiegare perche non la si imposta.
SELECT ok(
  (SELECT regexp_replace(p.prosrc, E'--[^\n]*', '', 'g') !~ 'set_config'
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_riporta_attivita_da_emettere')
  AND (SELECT p.proconfig IS NULL
         FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'vendite' AND p.proname = 'fn_riporta_attivita_da_emettere'),
  '14) il verbo NON imposta la GUC di manutenzione'
);

-- ============================================================
-- 15) ⛔ Un rifiuto non lascia niente per strada
-- ============================================================
-- L attivita in fattura ha attraversato il verbo tre volte (test 8 e 13) ed e
-- stata rifiutata: deve essere identica a com era.
SELECT ok(
  (SELECT a.fattura_riga_id = (SELECT riga_id FROM tmp_riga_rde)
      AND a.fatturato IS TRUE
      AND a.lock_in_fatturazione IS TRUE
      AND a.lock_batch_id = (SELECT lock_batch_id FROM tmp_cost_rde)
     FROM vendite.attivita_fatturabili a
    WHERE a.id = (SELECT attivita_id FROM tmp_af_rde WHERE slot = 'IN_FATTURA'))
  AND (SELECT ca.stato_emissione = 'EMESSA'
         FROM vendite.commesse_attivita ca
        WHERE ca.id = (SELECT attivita_id FROM tmp_ca_rde WHERE slot = 'IN_FATTURA'))
  AND NOT EXISTS (
        SELECT 1 FROM vendite.commesse_attivita_log l
         WHERE l.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_rde WHERE slot = 'IN_FATTURA')
           AND l.evento = 'RIGA_RIPORTATA_DA_EMETTERE'),
  '15) l attivita rifiutata e intatta, e nessun evento di log e stato scritto per lei'
);

SELECT * FROM finish();

ROLLBACK;
