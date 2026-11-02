-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: i parametri d'importo hanno un valore di sistema, e la riga
--   dell'emittente per l'utility e' un override (brief-db-modelli-documento-
--   standard §10.3 K-7, D-7; §2 Q-6 … Q-8; changeSet 20261020-99, 20261021-01 … -03)
-- ------------------------------------------------------------
-- Elenco test (plan 12):
--  Struttura
--   1) config.utilities ha i due parametri di sistema, NOT NULL
--  Il BB (anagrafiche.fn_parametri_importo_utility)
--   2) emittente nuovo, nessuna riga: il valore di sistema dell'utility, non personalizzata
--   3) le soglie senza la riga sono NULL («nessun minimo», Q-7)
--   4) la policy generale dell'emittente (rounding_policy) vale per il metodo
--   5) la riga dell'emittente vince su tutto, ed e' personalizzata
--   6) un'utility che non esiste: zero righe
--  Q-8: un emittente nuovo porta una fattura al ricalcolo dei totali
--   7) fn_ricalcola_totali_fattura senza la riga dell'emittente non solleva
--   8) il totale e' arrotondato coi decimali di sistema
--   9) la fattura senza utility: E_CONFIG_MANCANTE, come prima
--  Il lookup delle utility di un BA
--  10) mostra i parametri effettivi, non NULL
--  R-3: la riga si arrotonda con la stessa catena (vendite.fn_parametri_importo_riga)
--  11) riga senza regole dell'articolo: i parametri dell'emittente (0 decimali), non il 2 fisso
--  12) riga senza regole su una fattura senza utility: E_CONFIG_MANCANTE
--
-- Scopo:
--  - provare sui casi COSTRUITI la regola di D-7: sistema, poi policy generale
--    dell'emittente (solo per il metodo), poi la riga dell'emittente;
--  - ⭐ Q-8 e' il presidio che avrebbe visto il buco prima dello smoke:
--    dbops.fn_pgtap_crea_fattura scrive la riga dell'emittente a mano, quindi i
--    test che la usano non lo vedono. Qui la fattura si costruisce senza.
--  - Gira come l'applicazione (zeroerp_app + contesto operatore).
-- ------------------------------------------------------------

BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

CREATE TEMP TABLE _cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('parametri importo') c;

CREATE TEMP TABLE _rif AS
SELECT m.soggetto_ruolo_id                                   AS emittente_sr_id,
       m.emittente_fiscale_id,
       c.billing_account_id,
       c.utility_id,
       u.arrotondamento_importi_dec                          AS dec_sistema,
       u.metodo_arrotondamento_importi                       AS metodo_sistema,
       script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id) AS registro_id,
       config.fn_get_natura_doc_fiscale_id('FATTURA')        AS natura_fattura_id,
       (SELECT s.id FROM config.stati_doc_fiscale s
         WHERE s.codice_interno = 'DRAFT')                   AS stato_draft_id,
       -- ⛔ catalogo SCELTO, con il suo ORDER BY (come dbops.fn_pgtap_crea_fattura)
       (SELECT t.id FROM config.tipi_doc_fiscale t
         WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)       AS tipo_doc_fiscale_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id
  FROM _mondo m, _cli c
  JOIN config.utilities u ON u.id = c.utility_id;

-- ============================================================
-- Struttura
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM information_schema.columns
    WHERE table_schema = 'config' AND table_name = 'utilities'
      AND column_name IN ('arrotondamento_importi_dec', 'metodo_arrotondamento_importi')
      AND is_nullable = 'NO'),
  2,
  '1) config.utilities ha i due parametri di sistema, NOT NULL');

-- ============================================================
-- Il BB
-- ============================================================
SELECT is(
  (SELECT row(p.arrotondamento_importi_dec, p.metodo_arrotondamento_importi, p.personalizzata)::text
     FROM _rif r, anagrafiche.fn_parametri_importo_utility(r.emittente_sr_id, r.utility_id) p),
  (SELECT row(dec_sistema, metodo_sistema, false)::text FROM _rif),
  '2) emittente nuovo, nessuna riga: il valore di sistema dell''utility');

SELECT is(
  (SELECT row(p.minimo_soglia_min, p.minimo_soglia_max)::text
     FROM _rif r, anagrafiche.fn_parametri_importo_utility(r.emittente_sr_id, r.utility_id) p),
  row(NULL::numeric, NULL::numeric)::text,
  '3) senza la riga le soglie sono NULL: nessun minimo');

-- La policy generale dell'emittente: un metodo diverso da quello di sistema.
UPDATE anagrafiche.emittenti_fiscali ef
   SET rounding_policy = CASE WHEN r.metodo_sistema = 'UP' THEN 'DOWN' ELSE 'UP' END
  FROM _rif r
 WHERE ef.id = r.emittente_fiscale_id;

SELECT is(
  (SELECT p.metodo_arrotondamento_importi::text
     FROM _rif r, anagrafiche.fn_parametri_importo_utility(r.emittente_sr_id, r.utility_id) p),
  (SELECT CASE WHEN metodo_sistema = 'UP' THEN 'DOWN' ELSE 'UP' END FROM _rif),
  '4) la policy generale dell''emittente vale per il metodo');

INSERT INTO anagrafiche.emittenti_fiscali_utilities
    (emittente_soggetto_ruolo_id, utility_id, arrotondamento_importi_dec,
     metodo_arrotondamento_importi, minimo_soglia_min, minimo_soglia_max, attivo)
SELECT r.emittente_sr_id, r.utility_id, 0, 'HALF_DOWN', 10, 100, true FROM _rif r;

SELECT is(
  (SELECT row(p.arrotondamento_importi_dec, p.metodo_arrotondamento_importi,
              p.minimo_soglia_min, p.minimo_soglia_max, p.personalizzata)::text
     FROM _rif r, anagrafiche.fn_parametri_importo_utility(r.emittente_sr_id, r.utility_id) p),
  row(0::smallint, 'HALF_DOWN'::varchar, 10::numeric(20,8), 100::numeric(20,8), true)::text,
  '5) la riga dell''emittente vince su tutto, ed e'' personalizzata');

SELECT is(
  (SELECT count(*)::int
     FROM _rif r, anagrafiche.fn_parametri_importo_utility(r.emittente_sr_id, -1) p),
  0,
  '6) un''utility che non esiste: zero righe');

-- Si torna allo stato «emittente nuovo»: senza riga, senza policy generale.
DELETE FROM anagrafiche.emittenti_fiscali_utilities e
 USING _rif r
 WHERE e.emittente_soggetto_ruolo_id = r.emittente_sr_id AND e.utility_id = r.utility_id;
UPDATE anagrafiche.emittenti_fiscali ef SET rounding_policy = NULL
  FROM _rif r WHERE ef.id = r.emittente_fiscale_id;

-- ============================================================
-- Q-8: la fattura di un emittente nuovo arriva al ricalcolo
-- ============================================================
CREATE TEMP TABLE _fatture AS
WITH ins AS (
    INSERT INTO vendite.fatture
        (registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
         tasso_cambio, natura_doc_id, stato_doc_fiscale_id, tipo_doc_fiscale_id,
         valuta_id, utility_id, meta)
    SELECT r.registro_id, script.fn_data_operativa(), r.emittente_sr_id, r.billing_account_id,
           1, r.natura_fattura_id, r.stato_draft_id, r.tipo_doc_fiscale_id, r.valuta_id,
           CASE WHEN n = 1 THEN r.utility_id END,
           jsonb_build_object('test_scope', 'pgtap_parametri_importo', 'n', n)
      FROM _rif r, generate_series(1, 2) n
    RETURNING id, (meta->>'n')::int AS n
)
SELECT CASE n WHEN 1 THEN 'CON_UTILITY' ELSE 'SENZA_UTILITY' END AS caso, id FROM ins;

-- Un riepilogo con un importo a tre decimali: il totale lo deve arrotondare.
INSERT INTO vendite.fatture_riepiloghi_iva (fattura_id, imponibile, imposta, arrotondamento)
SELECT id, 10.005, 0, 0 FROM _fatture WHERE caso = 'CON_UTILITY';

SELECT lives_ok(
  $$SELECT vendite.fn_ricalcola_totali_fattura((SELECT id FROM _fatture WHERE caso = 'CON_UTILITY'))$$,
  '7) senza la riga dell''emittente il ricalcolo dei totali non solleva');

-- 10.005 coi parametri di sistema dell'utility; il valore atteso si calcola
-- con il BB unico dell'arrotondamento, cosi' il test non ricopia la formula.
SELECT is(
  (SELECT f.totale_a_pagare
     FROM vendite.fatture f
    WHERE f.id = (SELECT id FROM _fatture WHERE caso = 'CON_UTILITY')),
  (SELECT script.fn_arrotonda_importo(10.005, dec_sistema, metodo_sistema)::numeric(18,6) FROM _rif),
  '8) il totale e'' arrotondato coi parametri di sistema dell''utility');

SELECT throws_like(
  $$SELECT vendite.fn_ricalcola_totali_fattura((SELECT id FROM _fatture WHERE caso = 'SENZA_UTILITY'))$$,
  '%Configurazione mancante%',
  '9) la fattura senza utility: E_CONFIG_MANCANTE, come prima');

-- ============================================================
-- Il lookup delle utility di un BA
-- ============================================================
-- La matrice ruoli-utility si costruisce: l'utility del BA ammessa per il
-- cliente e per l'emittente (sullo scratch, come in CI, la matrice e' vuota).
INSERT INTO config.utilities_tipi_ruolo (utility_id, tipo_ruolo_id)
SELECT r.utility_id, tr.id
  FROM _rif r, config.tipi_ruoli tr
 WHERE tr.codice_interno IN ('CL', 'EF')
   AND NOT EXISTS (SELECT 1 FROM config.utilities_tipi_ruolo x
                    WHERE x.utility_id = r.utility_id AND x.tipo_ruolo_id = tr.id
                      AND x.attivo);

-- ⚠️ Non a vuoto: il lookup deve dare almeno una riga, e nessuna con NULL.
SELECT is(
  (SELECT row(count(*) > 0,
              count(*) FILTER (WHERE l.arrotondamento_importi_dec IS NULL
                                  OR l.metodo_arrotondamento_importi IS NULL))::text
     FROM _rif r, anagrafiche.fn_lookup_utilities_per_ba(r.billing_account_id, 'CL') l),
  row(true, 0::bigint)::text,
  '10) il lookup delle utility di un BA mostra i parametri effettivi, mai NULL');

-- ============================================================
-- R-3: l'importo di riga segue la stessa catena del totale
-- ============================================================
-- L'emittente arrotonda a 0 decimali per questa utility; la riga non ha
-- articolo, quindi nessuna regola dell'articolo: vale la sua.
INSERT INTO anagrafiche.emittenti_fiscali_utilities
    (emittente_soggetto_ruolo_id, utility_id, arrotondamento_importi_dec,
     metodo_arrotondamento_importi, attivo)
SELECT r.emittente_sr_id, r.utility_id, 0, 'HALF_UP', true FROM _rif r;

CREATE TEMP TABLE _riga AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                     prezzo_unitario, competenza_dal, competenza_al)
  SELECT id, 1, 'Riga di prova', 1, 10.6, script.fn_data_operativa(), script.fn_data_operativa()
    FROM _fatture WHERE caso = 'CON_UTILITY'
  RETURNING imponibile_riga)
SELECT imponibile_riga FROM ins;

SELECT is(
  (SELECT imponibile_riga FROM _riga),
  11::numeric,
  '11) riga senza regole dell''articolo: i parametri dell''emittente (0 decimali), non il 2 fisso');

SELECT throws_like(
  $$INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                       prezzo_unitario, competenza_dal, competenza_al)
    SELECT id, 1, 'Riga di prova', 1, 10.6, script.fn_data_operativa(), script.fn_data_operativa()
      FROM _fatture WHERE caso = 'SENZA_UTILITY'$$,
  '%Configurazione mancante%',
  '12) riga senza regole su una fattura senza utility: E_CONFIG_MANCANTE');

SELECT * FROM finish();
ROLLBACK;
