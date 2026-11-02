-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: l'ANNO dentro la stringa del numero
--       vendite.famiglie_documento.anno_nel_numero_default   (20260908-11)
--       vendite.registri_fatturazione.anno_nel_numero        (20260908-12)
--       vendite.fn_assegna_numero_documento                  (20260908-13)
--       vendite.trgfn_..._set_anno_nel_numero                (20260908-14)
--       Piano: brief-db-registri-numerazione-chiave-del-contatore, sezione 11.8
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): le famiglie col codice della sorgente (DDT_VENDITA, ORDINE_VENDITA, RESO_VENDITA).
-- ------------------------------------------------------------
-- Elenco test (plan 7):
-- 1) I cinque default sono quelli dichiarati (la fattura e' l'unico false)
-- 2) ⭐⭐ DERIVATO: un sezionale ANNUALE di una famiglia che espone nasce con l'anno
-- 3) ⭐ ...e uno NESSUNA no, perche' il suo progressivo non si ripete
-- 4) ⭐ ...e la FATTURA nemmeno sotto ANNUALE: l'anno ce l'ha in colonna
-- 5) ⭐⭐ LA PROVA CHE CONTA: il numero composto PORTA l'anno
-- 6) ⭐ ...e senza la dichiarazione resta la stringa di prima (il gemello)
-- 7) ⛔ Dopo il primo numero la forma non si cambia piu', anno compreso
--
-- Scopo:
--   ⭐ L'INVARIANTE, ed e' quella degli assi dichiarati un piano piu' su:
--   tutto cio' che discrimina il CONTATORE deve poter discriminare anche la
--   STRINGA che una persona legge. Un sezionale ANNUALE azzera il
--   progressivo, quindi consegna lo stesso numero in anni diversi: il
--   database non se ne accorge — la sua unicita' porta l'anno in colonna —
--   e l'ambiguita' arriva intera alle liste, alle ricerche e a chi cita un
--   numero al telefono.
--
--   ⛔⛔ I TEST 3, 4 E 6 SONO QUELLI CHE TENGONO IN PIEDI GLI ALTRI. Un
--   risolutore rotto che accendesse l'anno SEMPRE passerebbe 1, 2, 5 e 7
--   esattamente come quello giusto, e cambierebbe la forma del numero a
--   fatture e commesse — cioe' il danno peggiore che questo cantiere puo'
--   fare. I gemelli negativi sono il presidio, non il contorno.
--
--   ⚠️ I VERBI STANNO IN ISTRUZIONI SEPARATE dalle asserzioni: la
--   numerazione scrive.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: che due documenti di anni diversi
--   collidano davvero sulla stringa. Non e' una collisione che il database
--   possa produrre — non c'e' nessun vincolo sulla sola stringa — ed e'
--   esattamente il motivo per cui il difetto era muto. Qui si prova la
--   causa: quale numero viene consegnato.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- ============================================================
-- 1) La dichiarazione del catalogo
-- ============================================================
SELECT is(
    (SELECT string_agg(f.codice_interno || '=' || f.anno_nel_numero_default::text,
                       ', ' ORDER BY f.codice_interno)
       FROM vendite.famiglie_documento f
      WHERE f.codice_interno IN ('FATTURA', 'DDT_VENDITA', 'ORDINE_VENDITA', 'RESO_VENDITA', 'COMMESSA')),
    'COMMESSA=true, DDT_VENDITA=true, FATTURA=false, ORDINE_VENDITA=true, RESO_VENDITA=true',
    '1) I cinque default sono quelli dichiarati: solo la fattura ha l''anno in colonna, non nella stringa');

-- ============================================================
-- Fixture: tre sezionali sullo stesso emittente.
-- ⚠️ La utility va valorizzata: lo slot (famiglia, emittente, «per tutte le
--    utility») e' gia' preso dal provisioning.
-- ============================================================
CREATE TEMP TABLE tmp_ann AS
WITH base AS (
  SELECT r.emittente_soggetto_ruolo_id AS sr,
         (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1) AS ut
    FROM vendite.registri_fatturazione r
   WHERE r.emittente_soggetto_ruolo_id IS NOT NULL
   ORDER BY r.id
   LIMIT 1),
a AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento,
       prefisso, lunghezza_numero, reset_policy, utility_id)
  SELECT 'PGTAP-ANN-A', 'pgTAP anno: DDT annuale', base.sr, 'DDT_VENDITA',
         'QAA', 7, 'ANNUALE', base.ut FROM base
  RETURNING id),
b AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento,
       prefisso, lunghezza_numero, reset_policy, utility_id)
  SELECT 'PGTAP-ANN-B', 'pgTAP anno: ordine continuo', base.sr, 'ORDINE_VENDITA',
         'QAB', 7, 'NESSUNA', base.ut FROM base
  RETURNING id),
c AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento,
       prefisso, lunghezza_numero, reset_policy, utility_id)
  SELECT 'PGTAP-ANN-C', 'pgTAP anno: fattura annuale', base.sr, 'FATTURA',
         'QAC', 7, 'ANNUALE', base.ut FROM base
  RETURNING id)
SELECT (SELECT id FROM a) AS reg_a, (SELECT id FROM b) AS reg_b,
       (SELECT id FROM c) AS reg_c, (SELECT sr FROM base) AS sr,
       (SELECT ut FROM base) AS ut;

-- ============================================================
-- 2/3/4) Il risolutore, e i suoi due gemelli negativi
-- ============================================================
SELECT is(
    (SELECT r.anno_nel_numero FROM vendite.registri_fatturazione r
      WHERE r.id = (SELECT reg_a FROM tmp_ann)),
    true,
    '2) Un sezionale ANNUALE di una famiglia che espone l''anno nasce con l''anno nel numero');

SELECT is(
    (SELECT r.anno_nel_numero FROM vendite.registri_fatturazione r
      WHERE r.id = (SELECT reg_b FROM tmp_ann)),
    false,
    '3) Sotto NESSUNA no: un progressivo che non riparte non si ripete, e l''anno non serve');

SELECT is(
    (SELECT r.anno_nel_numero FROM vendite.registri_fatturazione r
      WHERE r.id = (SELECT reg_c FROM tmp_ann)),
    false,
    '4) La FATTURA nemmeno sotto ANNUALE: il suo numero e'' nudo e l''anno viaggia in colonna');

-- ============================================================
-- 5/6) La prova che conta: la stringa consegnata
-- ============================================================
CREATE TEMP TABLE tmp_ann_num_a AS
SELECT v.numero
  FROM vendite.fn_assegna_numero_documento(
           p_famiglia_documento          => 'DDT_VENDITA',
           p_emittente_soggetto_ruolo_id => (SELECT sr FROM tmp_ann),
           p_data                        => DATE '2126-04-10',
           p_documento_id                => NULL,
           p_utility_id                  => (SELECT ut FROM tmp_ann),
           p_corpo                       => NULL,
           p_serie                       => NULL) v;

SELECT matches(
    (SELECT numero FROM tmp_ann_num_a),
    '^QAA2126-[0-9]{7}$',
    '5) Il numero consegnato porta l''anno: prefisso + anno + progressivo');

CREATE TEMP TABLE tmp_ann_num_b AS
SELECT v.numero
  FROM vendite.fn_assegna_numero_documento(
           p_famiglia_documento          => 'ORDINE_VENDITA',
           p_emittente_soggetto_ruolo_id => (SELECT sr FROM tmp_ann),
           p_data                        => DATE '2126-04-10',
           p_documento_id                => NULL,
           p_utility_id                  => (SELECT ut FROM tmp_ann),
           p_corpo                       => NULL,
           p_serie                       => NULL) v;

SELECT matches(
    (SELECT numero FROM tmp_ann_num_b),
    '^QAB[0-9]{7}$',
    '6) ...e dove l''anno non e'' dichiarato la stringa resta quella di prima');

-- ============================================================
-- 7) La forma non si cambia dopo il primo numero
-- ============================================================
PREPARE ann_cambia_forma AS
UPDATE vendite.registri_fatturazione
   SET anno_nel_numero = false
 WHERE id = (SELECT reg_a FROM tmp_ann);

SELECT throws_ok(
    'EXECUTE ann_cambia_forma',
    'P0001',
    NULL,
    '7) Il registro ha gia'' consegnato un numero: l''anno nel numero e'' forma, e non si cambia piu''');

SELECT * FROM finish();

ROLLBACK;
