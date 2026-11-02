-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la coda di stampa dice CHE COSA stampare, non solo quale fattura
--   (brief-db-modelli-documento-standard §9; changeSet 20261020-28 … -31)
-- ------------------------------------------------------------
-- Elenco test (plan 14):
--  Accodamento (Q-1, Q-2: ex_fatture_stampa_coda_vivo)
--   1) accoda col tipo FATTURA_VENDITA: una riga per fattura, col tipo scritto
--   2) accoda col tipo DDT_VENDITA: due tipi per la stessa fattura convivono
--   3) riaccoda FATTURA_VENDITA: 0 nuove (idempotente sul suo tipo)
--   4) accoda col tipo NULL mentre le righe tipate sono vive: 0 nuove
--   5) le righe vive sono ancora quattro, nessuna col tipo NULL
--   6) F1 chiusa (FATTO), riaccoda col tipo NULL: 1 nuova, solo F1 (F2 ha
--      ancora righe tipate vive)
--   7) accoda FATTURA_VENDITA con la riga NULL viva su F1: 0 nuove
--   8) INSERT diretto in conflitto con la riga NULL viva -> 23P01 (il vincolo
--      regge anche senza la funzione)
--  Override (Q-3)
--   9) override coerente (lo standard della fattura, col suo tipo) passa
--  10) override con un tipo diverso da quello del modello -> 23503
--  11) override senza tipo -> 23514
--  12) override col modello di un'altra sorgente -> 23503
--  Firma
--  13) tipo <= 0 -> E_PARAMETRO_INVALIDO
--  14) la firma vecchia (bigint) non esiste piu'
--
-- Scopo:
--  - provare sui casi COSTRUITI la regola delle righe vive: una riga per
--    (fattura, tipo), e una riga col tipo NULL esclude le altre. Il NULL vuol
--    dire «qualunque tipo il DB risolva», quindi accanto a una riga tipata
--    sarebbe la stessa stampa (o un AMBIGUO).
--  - ⚠️ Il rifiuto AMBIGUO col tipo NULL e due candidati non si ripete qui: lo
--    prova test-documenti-template-standard-v1 (20). Questo file prova la coda,
--    e per la coda basta che il tipo esista (FK): i tipi e i modelli sono quelli
--    del seed, cercati per codice_interno.
--  - Gira come l'applicazione (zeroerp_app + contesto operatore, RLS attiva):
--    accodare e chiudere una riga sono scritture dell'applicazione.
-- ------------------------------------------------------------

BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture: un lotto DRAFT con due fatture DRAFT (F1, F2)
-- ============================================================
CREATE TEMP TABLE _cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('stampa coda tipo') c;

CREATE TEMP TABLE _rif AS
SELECT m.soggetto_ruolo_id                                   AS emittente_sr_id,
       c.billing_account_id,
       script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id) AS registro_id,
       config.fn_get_natura_doc_fiscale_id('FATTURA')        AS natura_fattura_id,
       (SELECT t.id FROM config.tipi_doc_fiscale t
         WHERE t.codice_interno = 'BACKOFFICE')              AS tipo_doc_fiscale_id,
       (SELECT s.id FROM config.stati_doc_fiscale s
         WHERE s.codice_interno = 'DRAFT')                   AS stato_draft_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'FATTURA')                 AS sorg_fattura,
       (SELECT o.id FROM documenti.tipi_documento_output o
         WHERE o.codice_interno = 'FATTURA_VENDITA')         AS tipo_fv,
       (SELECT o.id FROM documenti.tipi_documento_output o
         WHERE o.codice_interno = 'DDT_VENDITA')             AS tipo_ddt,
       -- I modelli dell'override: gli standard del seed (sorgente FATTURA e DDT).
       (SELECT t.id FROM documenti.template_documenti t
          JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id
         WHERE t.standard AND s.codice_interno = 'FATTURA'
           AND t.codice_interno = 'fattura_vendita')         AS std_fattura,
       (SELECT t.id FROM documenti.template_documenti t
          JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id
         WHERE t.standard AND s.codice_interno = 'DDT_VENDITA'
           AND t.codice_interno = 'ddt_vendita')             AS std_ddt
  FROM _mondo m, _cli c;

CREATE TEMP TABLE _lotto AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti
        (codice, tipo_doc_fiscale_id, competenza_mese,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id, meta)
    SELECT 'PGTAP-CODA-TIPO-' || r.emittente_sr_id, r.tipo_doc_fiscale_id,
           date_trunc('month', script.fn_data_operativa())::date, r.emittente_sr_id,
           r.stato_draft_id, jsonb_build_object('test_scope', 'pgtap_stampa_coda_tipo')
      FROM _rif r
    RETURNING id
)
SELECT id FROM ins;

-- Le fatture, nello STESSO stato del lotto (fn_guard_lotto_fatture_stato_coerente).
CREATE TEMP TABLE _fatture AS
WITH ins AS (
    INSERT INTO vendite.fatture
        (registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
         tasso_cambio, natura_doc_id, stato_doc_fiscale_id, meta)
    SELECT r.registro_id, script.fn_data_operativa(), r.emittente_sr_id, r.billing_account_id,
           1, r.natura_fattura_id, r.stato_draft_id,
           jsonb_build_object('test_scope', 'pgtap_stampa_coda_tipo', 'n', n)
      FROM _rif r, generate_series(1, 2) n
    RETURNING id, (meta->>'n')::int AS n
)
SELECT 'F' || n AS fattura, id FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id)
SELECT l.id, f.id FROM _lotto l, _fatture f;

-- Le righe vive del lotto, lette sempre allo stesso modo.
CREATE TEMP VIEW _vive AS
SELECT f.fattura, c.tipo_documento_output_id AS tipo
  FROM vendite.fatture_stampa_coda c
  JOIN _fatture f ON f.id = c.sorgente_id
 WHERE c.stato IN ('PENDING', 'IN_CORSO');

-- ============================================================
-- Accodamento
-- ============================================================
SELECT is(
  (SELECT vendite.fn_accoda_stampe_lotto(l.id, r.tipo_fv) FROM _lotto l, _rif r),
  2,
  '1) accoda col tipo FATTURA_VENDITA: una riga per fattura');

SELECT is(
  (SELECT vendite.fn_accoda_stampe_lotto(l.id, r.tipo_ddt) FROM _lotto l, _rif r),
  2,
  '2) accoda col tipo DDT_VENDITA: due tipi per la stessa fattura convivono');

SELECT is(
  (SELECT vendite.fn_accoda_stampe_lotto(l.id, r.tipo_fv) FROM _lotto l, _rif r),
  0,
  '3) riaccoda FATTURA_VENDITA: nessuna riga nuova');

SELECT is(
  (SELECT vendite.fn_accoda_stampe_lotto(l.id) FROM _lotto l),
  0,
  '4) col tipo NULL, accanto a righe tipate vive: nessuna riga nuova');

SELECT is(
  (SELECT string_agg(v.fattura || ':' || coalesce(o.codice_interno, 'NULL'), ' '
                     ORDER BY v.fattura, o.codice_interno)
     FROM _vive v LEFT JOIN documenti.tipi_documento_output o ON o.id = v.tipo),
  'F1:DDT_VENDITA F1:FATTURA_VENDITA F2:DDT_VENDITA F2:FATTURA_VENDITA',
  '5) le righe vive sono quattro, ognuna col suo tipo, nessuna col tipo NULL');

-- F1 ha finito di stampare: le sue righe escono dal vincolo.
UPDATE vendite.fatture_stampa_coda c SET stato = 'FATTO'
  FROM _fatture f
 WHERE f.id = c.sorgente_id AND f.fattura = 'F1';

SELECT is(
  (SELECT vendite.fn_accoda_stampe_lotto(l.id) FROM _lotto l),
  1,
  '6) F1 chiusa, riaccoda col tipo NULL: una riga nuova, solo F1');

SELECT is(
  (SELECT vendite.fn_accoda_stampe_lotto(l.id, r.tipo_fv) FROM _lotto l, _rif r),
  0,
  '7) col tipo FATTURA_VENDITA, accanto alla riga NULL viva di F1: nessuna riga nuova');

SELECT throws_ok(
  $$INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, tipo_documento_output_id)
    SELECT r.sorg_fattura, f.id, f.id::text, r.tipo_ddt
      FROM _rif r, _fatture f WHERE f.fattura = 'F1'$$,
  '23P01', NULL,
  '8) un INSERT diretto accanto alla riga NULL viva: il vincolo lo rifiuta');

-- ============================================================
-- Override: il modello esatto, legato al tipo e alla sorgente
-- ============================================================
-- Righe terminali (FATTO): non toccano il vincolo delle righe vive, cosi' il
-- test guarda solo il legame dell'override.
SELECT lives_ok(
  $$INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, template_documento_id,
         tipo_documento_output_id, stato)
    SELECT r.sorg_fattura, f.id, f.id::text, r.std_fattura, r.tipo_fv, 'FATTO'
      FROM _rif r, _fatture f WHERE f.fattura = 'F2'$$,
  '9) override coerente: lo standard della fattura, col suo tipo');

SELECT throws_ok(
  $$INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, template_documento_id,
         tipo_documento_output_id, stato)
    SELECT r.sorg_fattura, f.id, f.id::text, r.std_fattura, r.tipo_ddt, 'FATTO'
      FROM _rif r, _fatture f WHERE f.fattura = 'F2'$$,
  '23503', NULL,
  '10) override con un tipo diverso da quello del modello: FK composta');

SELECT throws_ok(
  $$INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, template_documento_id, stato)
    SELECT r.sorg_fattura, f.id, f.id::text, r.std_fattura, 'FATTO'
      FROM _rif r, _fatture f WHERE f.fattura = 'F2'$$,
  '23514', NULL,
  '11) override senza tipo: CHECK');

SELECT throws_ok(
  $$INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, template_documento_id,
         tipo_documento_output_id, stato)
    SELECT r.sorg_fattura, f.id, f.id::text, r.std_ddt, r.tipo_ddt, 'FATTO'
      FROM _rif r, _fatture f WHERE f.fattura = 'F2'$$,
  '23503', NULL,
  '12) override col modello di un''altra sorgente (DDT): FK composta');

-- ============================================================
-- Firma
-- ============================================================
SELECT throws_like(
  $$SELECT vendite.fn_accoda_stampe_lotto((SELECT id FROM _lotto), 0)$$,
  '%Parametro non valido%',
  '13) tipo <= 0: parametro non valido');

SELECT hasnt_function('vendite', 'fn_accoda_stampe_lotto', ARRAY['bigint'],
  '14) la firma di prima (bigint) non esiste piu'': nessun overload');

SELECT * FROM finish();
ROLLBACK;
