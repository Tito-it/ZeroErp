-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la DATA DEL DOCUMENTO — cantiere numerazione-data-documento (2026-08-25)
--       script.fn_data_operativa · vendite.fn_calcola_data_documento
--       vendite.fn_imposta_data_documento_lotto
--       vendite.trgfn_fatture_guard_data_numerata
-- ------------------------------------------------------------
-- Indice test (1..15)
--  1) fixture: due registri di prova (OGGI e FINE_MESE_COMPETENZA) + una fattura
--  2) fn_data_operativa risponde nel fuso DELL'AZIENDA, non in quello di sessione
--  3) fn_data_operativa: parametro VUOTO -> solleva
--  4) fn_data_operativa: fuso NON riconosciuto -> solleva, e la frase nomina il valore
--  5) fn_data_operativa: parametro ASSENTE -> solleva
--  6) fn_calcola_data_documento, politica OGGI
--  7) fn_calcola_data_documento, politica FINE_MESE_COMPETENZA -> ultimo del mese
--  8) la data DICHIARATA sul lotto vince su ENTRAMBE le politiche
--  9) FINE_MESE_COMPETENZA senza competenza -> solleva (nessun ripiego su oggi)
-- 10) fn_imposta_data_documento_lotto: scrive la data e RIGENERA il piano rate
-- 11) ... e la prima rata si e' davvero spostata
-- 12) fn_imposta_data_documento_lotto: le fatture gia' numerate si SALTANO
-- 13) DB-14: cambiare la data di una fattura NUMERATA -> rifiutato (P0001)
-- 14) DB-14: ... e la frase nomina il NUMERO del documento
-- 15) DB-14: su una fattura NON numerata la data si cambia
-- ------------------------------------------------------------
-- Scopo:
--  - la data di un documento non e' piu' `current_date` catturato alla
--    generazione della bozza nel fuso di chi chiama, ma una REGOLA: la politica
--    del registro, che la data dichiarata sul lotto puo' scavalcare;
--  - dichiararla su un lotto rigenera i piani rate, perche' le scadenze si
--    calcolano da `fatture.data` e il guard D-K non se ne accorgerebbe (verifica
--    la SOMMA delle rate, che non cambia);
--  - da quando un documento ha un numero, la sua data non si tocca piu'.
--
-- ⚠️ QUESTO FILE NON PROVA IL CANCELLO DI MONOTONIA: quello vive in
--   fn_get_next_progressivo ed e' collaudato in test-registri-progressivi.sql.
--   Qui si prova solo la sua ANTICAMERA dentro fn_imposta_data_documento_lotto.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, che qui non arriva mai (si chiude in ROLLBACK): senza,
--   il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS
-- attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ La sessione si forza in UTC APPOSTA: e' il fuso in cui si connette Django
--   (USE_TZ senza TIME_ZONE in DATABASES), cioe' quello che produceva il
--   difetto. Se fn_data_operativa leggesse il fuso della sessione invece di
--   quello dell'azienda, il test 2 lo vedrebbe.
SET LOCAL TimeZone = 'UTC';

SELECT plan(15);

-- ============================================================
-- 1) Fixture
-- ============================================================
CREATE TEMP TABLE tmp_ddoc_refs AS
SELECT (SELECT a.id  FROM vendite.attivita_fatturabili a ORDER BY a.id LIMIT 1) AS attivita_id,
       -- ⚠️ Solo lotti in DRAFT: la fattura nasce in DRAFT e il guard DEFERRED
       --   di coerenza pretende che il lotto sia nello stesso stato.
       (SELECT fl.id FROM vendite.fatturazione_lotti fl
          JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
         WHERE s.codice_interno = 'DRAFT'
         ORDER BY fl.id DESC LIMIT 1)                                           AS lotto_id;

-- Due registri di prova, uno per politica. ⭐ Si creano invece di usare quelli
-- di catalogo: cosi' il test non dipende dal seed, che e' una DECISIONE di
-- configurazione e puo' cambiare senza che questo file debba accorgersene.
CREATE TEMP TABLE tmp_ddoc_reg AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, reset_policy, attivo, politica_data_documento, meta)
  VALUES ('RDD_OGGI',    'Registro prova OGGI',     'ANNUALE', true, 'OGGI',
          jsonb_build_object('test_scope', 'pgtap_data_documento')),
         ('RDD_FINEMESE','Registro prova fine mese','ANNUALE', true, 'FINE_MESE_COMPETENZA',
          jsonb_build_object('test_scope', 'pgtap_data_documento'))
  RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice = 'RDD_OGGI')     AS reg_oggi,
       max(id) FILTER (WHERE codice = 'RDD_FINEMESE') AS reg_finemese
  FROM ins;

-- La fattura si crea con il creatore applicativo, che la mette in DRAFT: cosi'
-- la fixture attraversa la stessa porta del giro reale.
CREATE TEMP TABLE tmp_ddoc_f AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id    FROM tmp_ddoc_refs),
         (SELECT attivita_id FROM tmp_ddoc_refs)) AS id;

SELECT ok(
  (SELECT reg_oggi FROM tmp_ddoc_reg) IS NOT NULL
  AND (SELECT reg_finemese FROM tmp_ddoc_reg) IS NOT NULL
  AND (SELECT id FROM tmp_ddoc_f) IS NOT NULL,
  '1) Fixture: due registri di prova e una fattura in DRAFT');

-- ============================================================
-- 2..5) script.fn_data_operativa
-- ============================================================
-- ⭐ La sessione e' in UTC (vedi il preambolo). La funzione deve rispondere la
--   data nel fuso dell'AZIENDA: se rispondesse quella di sessione, questo
--   confronto fallirebbe ogni volta che le due date divergono — cioe' fra la
--   mezzanotte e le 02:00 di Roma, che e' esattamente la finestra in cui il
--   difetto si manifestava.
SELECT is(
  script.fn_data_operativa(),
  (now() AT TIME ZONE (SELECT default_value FROM config.parameters
                        WHERE code = 'SYSTEM_FUSO_ORARIO'))::date,
  '2) fn_data_operativa risponde nel fuso dell''azienda, non in quello di sessione');

-- ⚠️ I tre rami di guasto si provano uno alla volta e si RIPRISTINA subito: il
--   DEFAULT di vendite.fatture.data chiama questa funzione, quindi lasciare il
--   parametro rotto farebbe fallire qualunque INSERT successiva della fixture.
UPDATE config.parameters SET default_value = '' WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_ok(
  $$ SELECT script.fn_data_operativa() $$,
  'P0001', NULL,
  '3) fn_data_operativa: parametro VUOTO -> solleva (nessun ripiego a UTC)');

UPDATE config.parameters SET default_value = 'Europe/Roma' WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_like(
  $$ SELECT script.fn_data_operativa() $$,
  '%Europe/Roma%',
  '4) fn_data_operativa: fuso non riconosciuto -> solleva, e la frase nomina il valore');

DELETE FROM config.parameters WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_ok(
  $$ SELECT script.fn_data_operativa() $$,
  'P0001', NULL,
  '5) fn_data_operativa: parametro ASSENTE -> solleva');

-- Ripristino: da qui in poi la funzione deve tornare a rispondere.
INSERT INTO config.parameters (id, code, default_value, description)
VALUES (54, 'SYSTEM_FUSO_ORARIO', 'Europe/Rome', 'ripristino fixture pgTAP')
ON CONFLICT (id) DO UPDATE SET default_value = 'Europe/Rome';

-- ============================================================
-- 6..9) vendite.fn_calcola_data_documento
-- ============================================================
SELECT is(
  vendite.fn_calcola_data_documento(
      (SELECT reg_oggi FROM tmp_ddoc_reg), date '2026-07-01'),
  script.fn_data_operativa(),
  '6) politica OGGI -> la data operativa (la competenza non c''entra)');

SELECT is(
  vendite.fn_calcola_data_documento(
      (SELECT reg_finemese FROM tmp_ddoc_reg), date '2026-07-01'),
  date '2026-07-31',
  '7) politica FINE_MESE_COMPETENZA: competenza 2026-07 -> 31/07/2026');

-- ⭐ La dichiarazione vince su ENTRAMBE, ed e' il senso della decisione «una
--   data sola per l'intero atto»: un lotto puo' contenere documenti di registri
--   con politiche diverse, e la data dichiarata deve valere per tutti.
SELECT is(
  ARRAY[
    vendite.fn_calcola_data_documento(
        (SELECT reg_oggi FROM tmp_ddoc_reg),     date '2026-07-01', date '2026-08-10'),
    vendite.fn_calcola_data_documento(
        (SELECT reg_finemese FROM tmp_ddoc_reg), date '2026-07-01', date '2026-08-10')
  ],
  ARRAY[date '2026-08-10', date '2026-08-10'],
  '8) la data DICHIARATA vince su entrambe le politiche');

-- ⛔ Nessun ripiego su oggi: una data plausibile e sbagliata su un documento
--   fiscale non la nota nessuno, e quando la si nota il numero e' gia' stato
--   consumato.
SELECT throws_ok(
  format($$ SELECT vendite.fn_calcola_data_documento(%s, NULL) $$,
         (SELECT reg_finemese FROM tmp_ddoc_reg)),
  'P0001', NULL,
  '9) FINE_MESE_COMPETENZA senza competenza -> solleva, non ripiega su oggi');

-- ============================================================
-- 10..12) vendite.fn_imposta_data_documento_lotto
-- ============================================================
-- La fattura ha bisogno di un piano rate perche' il punto 4 della madre abbia
-- qualcosa da rigenerare: termine + totale, poi il generatore.
UPDATE vendite.fatture
   SET termine_pagamento_id = (SELECT tp.id FROM config.termini_pagamento tp
                                WHERE tp.attivo IS TRUE ORDER BY tp.id LIMIT 1),
       totale_a_pagare = 120.00,
       data = date '2026-08-25'
 WHERE id = (SELECT id FROM tmp_ddoc_f);

SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_ddoc_f));

CREATE TEMP TABLE tmp_ddoc_prima AS
SELECT min(s.data_scadenza) AS prima_rata
  FROM vendite.fatture_scadenze s WHERE s.fattura_id = (SELECT id FROM tmp_ddoc_f);

-- ⚠️ La data dichiarata e' nel FUTURO rispetto al pavimento del sezionale: la
--   madre ha un guard sul minimo, e una data bassa verrebbe rifiutata per una
--   ragione che non e' quella che questo test vuole misurare.
CREATE TEMP TABLE tmp_ddoc_esito AS
SELECT * FROM vendite.fn_imposta_data_documento_lotto(
                (SELECT lotto_id FROM tmp_ddoc_refs), date '2027-06-15');

SELECT is(
  (SELECT f.data FROM vendite.fatture f WHERE f.id = (SELECT id FROM tmp_ddoc_f)),
  date '2027-06-15',
  '10) fn_imposta_data_documento_lotto scrive la data sulla fattura non numerata');

-- ⭐ IL PUNTO 4: le scadenze si calcolano da f.data, e il guard D-K verifica la
--   SOMMA delle rate — che non cambia. Se la rigenerazione saltasse, il
--   documento passerebbe con scadenze calcolate su una data che non porta piu':
--   un difetto che non solleva niente. Questo e' l'unico posto in cui si vede.
SELECT isnt(
  (SELECT min(s.data_scadenza) FROM vendite.fatture_scadenze s
    WHERE s.fattura_id = (SELECT id FROM tmp_ddoc_f)),
  (SELECT prima_rata FROM tmp_ddoc_prima),
  '11) ... e il piano rate e'' stato RIGENERATO: la prima rata si e'' spostata');

-- Adesso la fattura diventa numerata: la madre deve saltarla e contarla, non
-- fallire. ⚠️ Il caso «lotto numerato a meta'» esiste nei dati veri.
UPDATE vendite.fatture
   SET numero = 999001, anno = 2027, serie = 'PGT'
 WHERE id = (SELECT id FROM tmp_ddoc_f);

SELECT is(
  (SELECT saltate_numerate FROM vendite.fn_imposta_data_documento_lotto(
             (SELECT lotto_id FROM tmp_ddoc_refs), date '2027-07-20')),
  1,
  '12) le fatture gia'' numerate si SALTANO e si contano (il lotto non fallisce)');

-- ============================================================
-- 13..15) DB-14: la data di una fattura numerata e' immutabile
-- ============================================================
SELECT throws_ok(
  format($$ UPDATE vendite.fatture SET data = date '2027-01-01' WHERE id = %s $$,
         (SELECT id FROM tmp_ddoc_f)),
  'P0001', NULL,
  '13) cambiare la data di una fattura NUMERATA -> rifiutato');

-- ⚠️ `throws_like` perche' la frase e' la posta in gioco: deve dire CHE COSA
--   blocca (il numero), non «colonna non modificabile».
SELECT throws_like(
  format($$ UPDATE vendite.fatture SET data = date '2027-01-01' WHERE id = %s $$,
         (SELECT id FROM tmp_ddoc_f)),
  '%999001%',
  '14) ... e la frase nomina il NUMERO del documento');

-- Controprova: senza numero la data si cambia. ⭐ Serve a distinguere «il guard
--   funziona» da «il guard blocca tutto», che sarebbe verde uguale sul test 13.
UPDATE vendite.fatture SET numero = NULL, anno = NULL, serie = NULL
 WHERE id = (SELECT id FROM tmp_ddoc_f);
UPDATE vendite.fatture SET data = date '2027-01-01'
 WHERE id = (SELECT id FROM tmp_ddoc_f);

SELECT is(
  (SELECT f.data FROM vendite.fatture f WHERE f.id = (SELECT id FROM tmp_ddoc_f)),
  date '2027-01-01',
  '15) su una fattura NON numerata la data si cambia (il guard non blocca tutto)');

SELECT * FROM finish();

ROLLBACK;
