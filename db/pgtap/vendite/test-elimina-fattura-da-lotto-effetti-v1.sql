-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: gli EFFETTI di «Elimina dal lotto» su un lotto con DUE fatture
--       (brief-db-lavoro-che-non-torna-indietro, lotto L4 / D-3, §3.2)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Togliere una fattura da un lotto deve rimettere in coda il lavoro di
--   QUELLA fattura, e non toccare quello delle altre. Sono due proprieta'
--   opposte, e un solo test non basta a tenerle insieme: una correzione
--   sbagliata soddisfa la prima e rompe la seconda in silenzio.
--
-- ⛔ PERCHE' ESISTE, e non e' «un test in piu'»
--   Fra il 2026-07-28 e il 2026-08-26 «Elimina dal lotto» non liberava
--   NIENTE. La chiave esterna fk_attivita_fatturabili_fattura_riga era
--   ON DELETE SET NULL e NOT DEFERRABLE: l'azione referenziale scattava a
--   fine istruzione del DELETE sulle righe, e il ripristino — che stava a
--   valle — trovava il puntatore gia' azzerato. L'attivita' restava
--   `fatturato = true` e la sua commessa_attivita su 'EMESSA': due porte
--   chiuse invece di una, senza un errore.
--
--   ⚠️ E c'era gia' un file che costruiva il caso giusto
--   (test-fatturazione-reset-lotto-draft) e asseriva su `deleted_fatture`,
--   cioe' su una colonna A SINISTRA di quella che si era rotta. Il verde non
--   era la prova. Da li' quel file ha guadagnato quattro asserzioni; questo
--   aggiunge il caso che li' non c'era: la SECONDA fattura.
--
-- ⭐ LA REGOLA CHE QUESTO FILE PRESIDIA SI CHIAMA C-22
--   `fn_elimina_fattura_da_lotto` passa alla primitiva `p_lock_batch_id =
--   NULL`, e non il lock_batch_id del lotto. Passando quello, il ramo di
--   batch libererebbe TUTTE le attivita' del lotto — anche quelle delle
--   fatture che restano. Il test 8 e il test 9 sono l'unico posto in cui
--   quella scelta viene verificata invece che dichiarata.
--
-- ⚠️ FIXTURE COSTRUITA, non scelta
--   Commessa, righe di commessa, lotto, attivita', fatture e righe sono
--   INSERITE da questo file. Solo i riferimenti anagrafici/di catalogo
--   (billing account, articolo, unita' di misura, tipo documento, valuta,
--   registro) si scelgono dall'esistente, come fanno gli altri file di
--   questa famiglia. Un test che SCEGLIE un lotto reale salta su un DB
--   ricostruito da zero, cioe' proprio in CI, ed e' la forma classica del
--   verde per sottrazione.
--
-- ⚠️ LE DUE FATTURE SI INSERISCONO DIRETTAMENTE, e non con
--   `fn_get_or_create_fattura_header`. Quella funzione e' un GET-or-create:
--   due attivita' dello stesso billing account, stesso tipo documento e
--   stessa valuta ricadono per costruzione sulla STESSA fattura, che e'
--   esattamente cio' che questo file non deve avere. Il soggetto qui e'
--   l'effetto dell'eliminazione, non la creazione della testata — quella ha
--   i suoi test.
--
-- ⚠️ La mutazione gira in un'ISTRUZIONE SEPARATA e il suo esito e'
--   materializzato in una temp: dentro la stessa istruzione dell'asserzione,
--   la snapshot leggerebbe lo stato PRIMA delle scritture e il rosso
--   accuserebbe la funzione invece del test.
--
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Fixture: due fatture DRAFT nel lotto, due attivita agganciate, due CA EMESSA
-- 3) Contatori: una fattura e una riga cancellate
-- 4) 🔴 Contatore: updated_attivita = 1, UNA sola (regola C-22)
-- 5) 🔴 Contatore: riemesse_attivita = 1, UNA sola
-- 6) 🔴 L attivita della fattura TOLTA e tornata libera
-- 7) 🔴 La sua commessa_attivita e tornata NON_EMESSA
-- 8) ⛔ L attivita dell ALTRA fattura e ANCORA agganciata
-- 9) ⛔ La commessa_attivita dell ALTRA fattura e ANCORA EMESSA
-- 10) L altra fattura e la sua riga esistono ancora
-- 11) Il lotto non e stato toccato, e l altra fattura e ancora collegata
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_cost_ef AS
SELECT 'pgtap_elimina_fattura_effetti'::text AS test_scope,
       uuidv7()                              AS lock_batch_id,
       script.fn_pgtap_emittente_sr_operatore() AS emittente_sr_id;

CREATE TEMP TABLE tmp_refs_ef AS
-- Il billing account si sceglie UNA volta: utility e istanza vengono da li'.
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
  -- ⚠️ Il registro dev'essere compatibile con l'emittente del contesto:
  --   uno legato a un ALTRO emittente farebbe fallire l'INSERT sul guard di
  --   scope, e il rosso parlerebbe di permessi invece che del soggetto.
  script.fn_pgtap_registro_fattura((SELECT emittente_sr_id FROM tmp_cost_ef))            AS registro_id;

SELECT ok(
  (SELECT r.stato_draft_id IS NOT NULL
      AND r.billing_account_id IS NOT NULL
      AND r.utility_id IS NOT NULL
      AND r.istanza_utility_id IS NOT NULL
      AND r.articolo_id IS NOT NULL
      AND r.uom_id IS NOT NULL
      AND r.tipo_doc_fiscale_id IS NOT NULL
      AND r.valuta_id IS NOT NULL
      AND r.stato_commessa_id IS NOT NULL
      AND r.registro_id IS NOT NULL
      AND (SELECT emittente_sr_id FROM tmp_cost_ef) IS NOT NULL
     FROM tmp_refs_ef r),
  '1) riferimenti minimi presenti (anagrafiche, catalogo, registro, emittente)'
);

-- ============================================================
-- Fixture: una commessa, DUE righe di commessa, DUE attivita'
-- ============================================================
CREATE TEMP TABLE tmp_commessa_ef AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-EF-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id,
         (SELECT emittente_sr_id FROM tmp_cost_ef), r.stato_commessa_id
    FROM tmp_refs_ef r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ca_ef (slot text PRIMARY KEY, attivita_id bigint);

-- ⚠️ Due righe di commessa DISTINTE: uq_attivita_fatturabili_commessa_attivita
--   e' 1:1, quindi due attivita' non possono condividerne una.
-- ⚠️ Nascono gia' EMESSA: e' lo stato che la pipeline lascia dopo
--   l'emissione, ed e' cio' che rende SIGNIFICATIVE le asserzioni 5, 7 e 9.
--   Lasciandole NON_EMESSA, `riemesse_attivita` varrebbe 0 con la correzione
--   e senza: verde per sottrazione.
WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_commessa_ef),
         'PGTAP-EF-SEG-A-' || substr(md5(clock_timestamp()::text), 1, 12),
         r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
         date_trunc('month', script.fn_data_operativa())::date,
         date_trunc('month', script.fn_data_operativa())::date,
         (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
         r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
         'BOZZA', 'EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_commessa_ef))::text
    FROM tmp_refs_ef r
  RETURNING id)
INSERT INTO tmp_ca_ef SELECT 'A', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_commessa_ef),
         'PGTAP-EF-SEG-B-' || substr(md5(clock_timestamp()::text), 1, 12),
         r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
         date_trunc('month', script.fn_data_operativa())::date,
         date_trunc('month', script.fn_data_operativa())::date,
         (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
         r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
         'BOZZA', 'EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_commessa_ef))::text
    FROM tmp_refs_ef r
  RETURNING id)
INSERT INTO tmp_ca_ef SELECT 'B', id FROM ins;

-- Il lotto, in DRAFT, con il suo lock_batch_id
CREATE TEMP TABLE tmp_lotto_ef AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      lock_batch_id, competenza_mese, tipo_doc_fiscale_id, utility_id,
      billing_account_id, stato_doc_fiscale_id, emittente_soggetto_ruolo_id)
  SELECT (SELECT lock_batch_id FROM tmp_cost_ef),
         date_trunc('month', script.fn_data_operativa())::date,
         r.tipo_doc_fiscale_id, r.utility_id, r.billing_account_id,
         r.stato_draft_id, (SELECT emittente_sr_id FROM tmp_cost_ef)
    FROM tmp_refs_ef r
  RETURNING id, lock_batch_id)
SELECT * FROM ins;

-- Le DUE fatture, entrambe DRAFT e collegate al lotto
CREATE TEMP TABLE tmp_fatture_ef (slot text PRIMARY KEY, fattura_id bigint, riga_id bigint);

WITH ins AS (
  INSERT INTO vendite.fatture (registro_id, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id, tipo_doc_fiscale_id,
                               valuta_id, stato_doc_fiscale_id, data)
  SELECT r.registro_id, (SELECT emittente_sr_id FROM tmp_cost_ef),
         r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
         r.valuta_id, r.stato_draft_id, script.fn_data_operativa()
    FROM tmp_refs_ef r
  RETURNING id)
INSERT INTO tmp_fatture_ef(slot, fattura_id) SELECT 'A', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.fatture (registro_id, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id, tipo_doc_fiscale_id,
                               valuta_id, stato_doc_fiscale_id, data)
  SELECT r.registro_id, (SELECT emittente_sr_id FROM tmp_cost_ef),
         r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
         r.valuta_id, r.stato_draft_id, script.fn_data_operativa()
    FROM tmp_refs_ef r
  RETURNING id)
INSERT INTO tmp_fatture_ef(slot, fattura_id) SELECT 'B', id FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT (SELECT id FROM tmp_lotto_ef), f.fattura_id, (SELECT stato_draft_id FROM tmp_refs_ef)
  FROM tmp_fatture_ef f;

-- Una riga per fattura. Due istruzioni: un INSERT non sta in un LATERAL.
WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione,
                                     qta, prezzo_unitario, imponibile_riga, competenza_dal, competenza_al)
  SELECT f.fattura_id, 1, 'Riga PGTAP EF A', 1, 10, 10, script.fn_data_operativa(), script.fn_data_operativa()
    FROM tmp_fatture_ef f WHERE f.slot = 'A'
  RETURNING id)
UPDATE tmp_fatture_ef t SET riga_id = (SELECT id FROM ins) WHERE t.slot = 'A';

WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione,
                                     qta, prezzo_unitario, imponibile_riga, competenza_dal, competenza_al)
  SELECT f.fattura_id, 1, 'Riga PGTAP EF B', 1, 10, 10, script.fn_data_operativa(), script.fn_data_operativa()
    FROM tmp_fatture_ef f WHERE f.slot = 'B'
  RETURNING id)
UPDATE tmp_fatture_ef t SET riga_id = (SELECT id FROM ins) WHERE t.slot = 'B';

-- Le DUE attivita', ciascuna agganciata alla riga della SUA fattura e
-- lucchettata sul lock_batch_id del lotto: e' lo stato che la pipeline lascia.
CREATE TEMP TABLE tmp_af_ef (slot text PRIMARY KEY, attivita_id bigint);

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
         1, true, false, r.tipo_doc_fiscale_id, r.valuta_id,
         (SELECT id FROM tmp_commessa_ef),
         (SELECT attivita_id FROM tmp_ca_ef WHERE slot = 'A'),
         r.uom_id, 10,
         true, (SELECT lock_batch_id FROM tmp_lotto_ef),
         (SELECT riga_id FROM tmp_fatture_ef WHERE slot = 'A'),
         'COMPLETED',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ef))
    FROM tmp_refs_ef r
  RETURNING id)
INSERT INTO tmp_af_ef SELECT 'A', id FROM ins;

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
         1, true, false, r.tipo_doc_fiscale_id, r.valuta_id,
         (SELECT id FROM tmp_commessa_ef),
         (SELECT attivita_id FROM tmp_ca_ef WHERE slot = 'B'),
         r.uom_id, 10,
         true, (SELECT lock_batch_id FROM tmp_lotto_ef),
         (SELECT riga_id FROM tmp_fatture_ef WHERE slot = 'B'),
         'COMPLETED',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ef))
    FROM tmp_refs_ef r
  RETURNING id)
INSERT INTO tmp_af_ef SELECT 'B', id FROM ins;

SELECT ok(
  (SELECT count(*) = 2 FROM tmp_fatture_ef WHERE fattura_id IS NOT NULL AND riga_id IS NOT NULL)
  AND (SELECT count(*) = 2 FROM tmp_af_ef)
  AND (SELECT count(*) = 2
         FROM vendite.attivita_fatturabili a
         JOIN tmp_af_ef t ON t.attivita_id = a.id
        WHERE a.fattura_riga_id IS NOT NULL AND a.fatturato IS TRUE)
  AND (SELECT count(*) = 2
         FROM vendite.commesse_attivita ca
         JOIN tmp_ca_ef t ON t.attivita_id = ca.id
        WHERE ca.stato_emissione = 'EMESSA'),
  '2) fixture: due fatture DRAFT nel lotto, due attivita agganciate, due CA EMESSA'
);

-- ============================================================
-- La mutazione: si toglie la fattura A, e SOLO quella
-- ============================================================
-- ⚠️ Istruzione separata dalle asserzioni: l'esito si materializza.
CREATE TEMP TABLE tmp_esito_ef AS
SELECT *
  FROM vendite.fn_elimina_fattura_da_lotto(
         p_lotto_id   => (SELECT id FROM tmp_lotto_ef),
         p_fattura_id => (SELECT fattura_id FROM tmp_fatture_ef WHERE slot = 'A'));

SELECT ok(
  (SELECT deleted_fatture = 1 AND deleted_righe = 1 FROM tmp_esito_ef),
  '3) una fattura e una riga cancellate'
);

-- ============================================================
-- 4-5) I contatori dicono UNO, non due e non zero
-- ============================================================
-- ⛔ «Due» sarebbe la violazione della regola C-22: vorrebbe dire che si e'
--   passato il lock_batch_id del lotto e si e' liberato anche il lavoro delle
--   altre fatture. «Zero» e' il difetto corretto il 2026-08-26.
SELECT is(
  (SELECT updated_attivita FROM tmp_esito_ef), 1,
  '4) updated_attivita = 1: liberata UNA attivita, non zero e non entrambe'
);

SELECT is(
  (SELECT riemesse_attivita FROM tmp_esito_ef), 1,
  '5) riemesse_attivita = 1: riportata in coda UNA riga di commessa'
);

-- ============================================================
-- 6-7) Il lavoro della fattura TOLTA e tornato disponibile
-- ============================================================
SELECT ok(
  (SELECT a.fatturato IS FALSE
      AND a.fattura_riga_id IS NULL
      AND COALESCE(a.lock_in_fatturazione, false) IS FALSE
      AND a.lock_batch_id IS NULL
      AND a.stato_esecuzione IS NULL
     FROM vendite.attivita_fatturabili a
    WHERE a.id = (SELECT attivita_id FROM tmp_af_ef WHERE slot = 'A')),
  '6) l attivita della fattura tolta e tornata libera'
);

SELECT is(
  (SELECT ca.stato_emissione
     FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT attivita_id FROM tmp_ca_ef WHERE slot = 'A')),
  'NON_EMESSA'::character varying,
  '7) la commessa_attivita della fattura tolta e tornata NON_EMESSA'
);

-- ============================================================
-- 8-9) ⛔ Il lavoro dell ALTRA fattura NON e stato toccato — regola C-22
-- ============================================================
-- ⛔ Se questi due diventano rossi, qualcuno ha «corretto» l eliminazione
--   passando il lock_batch_id del lotto: il ripristino funzionerebbe, e
--   insieme scaricherebbe il lavoro delle fatture che restano. Sarebbe un
--   difetto peggiore di quello che si voleva chiudere, e invisibile.
SELECT ok(
  (SELECT a.fatturato IS TRUE
      AND a.fattura_riga_id = (SELECT riga_id FROM tmp_fatture_ef WHERE slot = 'B')
      AND a.lock_in_fatturazione IS TRUE
      AND a.lock_batch_id = (SELECT lock_batch_id FROM tmp_lotto_ef)
     FROM vendite.attivita_fatturabili a
    WHERE a.id = (SELECT attivita_id FROM tmp_af_ef WHERE slot = 'B')),
  '8) l attivita dell ALTRA fattura e ancora agganciata e lucchettata (C-22)'
);

SELECT is(
  (SELECT ca.stato_emissione
     FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT attivita_id FROM tmp_ca_ef WHERE slot = 'B')),
  'EMESSA'::character varying,
  '9) la commessa_attivita dell ALTRA fattura e ancora EMESSA (C-22)'
);

-- ============================================================
-- 10-11) E il resto del lotto e intatto
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM vendite.fatture f
           WHERE f.id = (SELECT fattura_id FROM tmp_fatture_ef WHERE slot = 'B'))
  AND EXISTS (SELECT 1 FROM vendite.fatture_righe r
               WHERE r.id = (SELECT riga_id FROM tmp_fatture_ef WHERE slot = 'B'))
  AND NOT EXISTS (SELECT 1 FROM vendite.fatture f
                   WHERE f.id = (SELECT fattura_id FROM tmp_fatture_ef WHERE slot = 'A')),
  '10) l altra fattura e la sua riga esistono ancora; quella tolta no'
);

SELECT ok(
  EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_fatture lf
           WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_ef)
             AND lf.fattura_id = (SELECT fattura_id FROM tmp_fatture_ef WHERE slot = 'B'))
  AND NOT EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_fatture lf
                   WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_ef)
                     AND lf.fattura_id = (SELECT fattura_id FROM tmp_fatture_ef WHERE slot = 'A'))
  AND (SELECT l.stato_doc_fiscale_id = (SELECT stato_draft_id FROM tmp_refs_ef)
         FROM vendite.fatturazione_lotti l
        WHERE l.id = (SELECT id FROM tmp_lotto_ef)),
  '11) il lotto e ancora DRAFT e collegato alla sola fattura rimasta'
);

SELECT * FROM finish();

ROLLBACK;
