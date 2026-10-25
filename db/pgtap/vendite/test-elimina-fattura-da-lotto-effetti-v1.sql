-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): CURATO — pescava il billing account «il primo per id» e moriva sulla commessa (billing_account_id nullo), zero asserzioni. Ora il mondo si costruisce: due commesse emittibili di DUE clienti (dbops.fn_pgtap_crea_commessa), il lotto DRAFT massivo (dbops.fn_pgtap_crea_lotto), le due fatture nel lotto con riga, lucchetto e aggancio da dbops.fn_pgtap_fattura_attivita (p_lotto_id). Niente resta a mano. ⚠️ Lo stato_esecuzione 'COMPLETED' che la vecchia fixture scriveva sull'attivita' non lo scrive il builder, e a mano dopo l'aggancio il guard lo rifiuta («Riga gia' fatturata»): la clausola stato_esecuzione IS NULL del 6 oggi parte gia' vera (debito del builder, dichiarato nel rapporto).
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
-- ⚠️ FIXTURE COSTRUITA, non scelta (rev 2026-10-25)
--   Commesse, righe di commessa, lotto, attivita', fatture e righe vengono dai
--   builder di dbops e dalle madri che chiamano. Un test che SCEGLIE un
--   billing account o un lotto reale muore o salta su un DB ricostruito da
--   zero, cioe' proprio in CI: e' la forma classica del verde per sottrazione.
--
-- ⚠️ DUE FATTURE NELLO STESSO LOTTO = DUE CLIENTI. La testata viene dalla
--   madre `fn_get_or_create_fattura_header`, che e' un GET-or-create: due
--   attivita' dello stesso billing account, stesso tipo documento e stessa
--   valuta ricadono per costruzione sulla STESSA fattura. Il lotto e' quindi
--   MASSIVO (senza billing account) e le due commesse sono di due clienti: le
--   fatture sono due per la via vera, sullo stesso lock_batch_id — che e'
--   cio' che la regola C-22 mette alla prova. Fino al 2026-10-25 le due
--   testate dello stesso cliente si inserivano a mano.
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
-- 0) Il mondo, e i riferimenti che ne vengono
-- ============================================================
-- Due commesse emittibili, una riga di commessa approvata ciascuna e la
-- sorgente ROOT (il pull la pretende): due clienti dell'azienda di chi agisce.
-- ⚠️ Due righe di commessa DISTINTE: uq_attivita_fatturabili_commessa_attivita
--   e' 1:1, quindi due attivita' non possono condividerne una.
CREATE TEMP TABLE tmp_comm_ef AS
SELECT 'A'::text AS slot, c.*
  FROM dbops.fn_pgtap_crea_commessa('elimina fattura A', 'PRONTA_FATTURAZIONE',
                                    p_con_sorgente_root => true) c;

INSERT INTO tmp_comm_ef
SELECT 'B', c.*
  FROM dbops.fn_pgtap_crea_commessa('elimina fattura B', 'PRONTA_FATTURAZIONE',
                                    p_con_sorgente_root => true) c;

CREATE TEMP TABLE tmp_refs_ef AS
SELECT
  (SELECT id FROM config.stati_doc_fiscale
    WHERE upper(btrim(codice_interno)) = 'DRAFT' ORDER BY id LIMIT 1) AS stato_draft_id,
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  ca.articolo_id,
  ca.uom_id,
  ca.tipo_doc_fiscale_id,
  -- la riga di commessa del builder non porta la valuta: catalogo, col suo ORDER BY
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  c.stato_commessa_id,
  c.emittente_soggetto_ruolo_id AS emittente_sr_id,
  -- ⚠️ Il registro dev'essere compatibile con l'emittente del mondo.
  script.fn_pgtap_registro_fattura(c.emittente_soggetto_ruolo_id) AS registro_id
  FROM tmp_comm_ef c
  JOIN vendite.commesse_attivita ca ON ca.id = c.attivita_id
 WHERE c.slot = 'A';

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
      AND r.emittente_sr_id IS NOT NULL
     FROM tmp_refs_ef r),
  '1) riferimenti minimi presenti (anagrafiche, catalogo, registro, emittente)'
);

-- ============================================================
-- Fixture: il lotto, DUE fatture, DUE attivita' agganciate
-- ============================================================
CREATE TEMP TABLE tmp_ca_ef AS
SELECT c.slot, c.attivita_id FROM tmp_comm_ef c;

-- Il lotto, in DRAFT, massivo, col tipo documento delle righe di commessa
-- (il pull lo confronta). Il lock_batch_id lo decide la madre.
CREATE TEMP TABLE tmp_lotto_ef AS
SELECT l.lotto_id AS id, l.lock_batch_id
  FROM tmp_refs_ef r,
       dbops.fn_pgtap_crea_lotto('elimina fattura', 'DRAFT', r.billing_account_id,
                                 r.tipo_doc_fiscale_id) l;

-- Le DUE fatture, entrambe DRAFT e collegate al lotto: per ciascuna il pull col
-- marchio del lotto (la riga di commessa va a EMESSA: e' cio' che rende
-- SIGNIFICATIVE le asserzioni 5, 7 e 9), la testata della madre, la riga, il
-- lucchetto sul lock_batch_id del lotto e l'aggancio.
CREATE TEMP TABLE tmp_fatt_ef AS
SELECT 'A'::text AS slot, f.*
  FROM dbops.fn_pgtap_fattura_attivita('elimina fattura A',
         ARRAY[(SELECT attivita_id FROM tmp_ca_ef WHERE slot = 'A')], (SELECT id FROM tmp_lotto_ef)) f;

INSERT INTO tmp_fatt_ef
SELECT 'B', f.*
  FROM dbops.fn_pgtap_fattura_attivita('elimina fattura B',
         ARRAY[(SELECT attivita_id FROM tmp_ca_ef WHERE slot = 'B')], (SELECT id FROM tmp_lotto_ef)) f;

CREATE TEMP TABLE tmp_fatture_ef AS
SELECT f.slot, f.fattura_id, f.fattura_riga_id AS riga_id FROM tmp_fatt_ef f;

CREATE TEMP TABLE tmp_af_ef AS
SELECT f.slot, f.attivita_fatturabile_id AS attivita_id FROM tmp_fatt_ef f;

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
-- ⚠️ rev 2026-10-25: lo stato_esecuzione l'attivita' lo ha gia' NULL (il
--   builder non scrive il 'COMPLETED' della pipeline): quella clausola non
--   misura il ripristino finche' il builder non lo sa fare.
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
