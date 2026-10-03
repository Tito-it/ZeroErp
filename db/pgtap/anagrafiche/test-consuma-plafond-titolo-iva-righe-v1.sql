-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_consuma_plafond_titolo_iva_righe — il plafond si
--   consuma per un GRUPPO di righe (un kit) con una frazione sola.
--   Brief: brief-db-bom-flag-quantita-e-kit-in-fattura §11 (D-5).
--   changeSet: 20261003-07 (la funzione), -08 (la primitiva ne diventa
--   l'involucro: la forma a una riga la provano test-soggetti-titoli-iva e
--   test-soggetti-titoli-iva-due-emittenti).
--
-- ⭐ I CASI SI COSTRUISCONO: cliente, fattura, righe e titoli nascono qui
--   (dbops.fn_pgtap_crea_mondo_cliente, dbops.fn_pgtap_crea_fattura). Dal DB si
--   leggono solo seed di catalogo (aliquota, unita' di misura, tipi titolo) e
--   l'emittente della whitelist dell'operatore di contesto.
--
-- IL KIT DI PROVA — tre righe, imponibile 500:
--     C1  2 x 100 = 200
--     C2  6 x  10 =  60
--     C3  8 x  30 = 240
--   Plafond 200 -> frazione 0,4 per tutti: 80, 24, 96 al titolo. Prima di
--   20261003-07, riga per riga, C1 prendeva tutto il plafond e C2, C3 nulla.
--
-- Indice test (1..12):
--    1) kit 500 su plafond 200: la stessa frazione per tutti (80, 24, 96)
--    2) frazione ritornata 0,4 e ordinarie 120, 36, 144
--    3) tre movimenti, uno per riga, che sommano 200; residuo 0
--    4) idempotenza: la seconda chiamata rilegge, nessun movimento nuovo
--    5) ⭐ il centesimo: tre righe da 10 su plafond 10 -> 3,33 3,33 3,34
--    6) plafond che copre tutto: frazione 1, quote = imponibili
--    7) capienza zero (il titolo del 5, esaurito): frazione 0, nessun movimento
--    8) titolo senza tetto: copre tutto e non scrive movimenti
--    9) guard: una riga di un'altra fattura e' rifiutata
--   10) guard: righe e imponibili di lunghezza diversa
--   11) guard: una riga NULL in un gruppo di due
--   12) guard: un imponibile non positivo
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva). Le
-- tabelle dei titoli hanno una policy di perimetro emittente.
CREATE TEMP TABLE tmp_cpr_ctx AS
SELECT script.fn_pgtap_set_contesto_operatore() AS auth_user_id;

SELECT plan(12);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_cpr_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('plafond per gruppo');

CREATE TEMP TABLE tmp_cpr_refs AS
SELECT
    (SELECT uef.emittente_fiscale_id
       FROM config.user_emittenti_fiscali uef
      WHERE uef.auth_user_id = (SELECT auth_user_id FROM tmp_cpr_ctx)
      ORDER BY uef.emittente_fiscale_id
      LIMIT 1)                                              AS emittente_fiscale_id,
    (SELECT m.cliente_soggetto_id FROM tmp_cpr_mondo m)    AS soggetto_id,
    (SELECT i.id FROM config.iva i
      WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)         AS iva_id,
    (SELECT u.id FROM catalogo.unita_misura u
      WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)         AS uom_id,
    (SELECT t.id FROM config.tipi_titolo_iva t
      WHERE t.codice_interno = 'INTENTO')                   AS tipo_intento_id,
    (SELECT t.id FROM config.tipi_titolo_iva t
      WHERE t.codice_interno = 'AGEVOLATA_104')             AS tipo_agevolata_id,
    dbops.fn_pgtap_crea_articolo('PGTAP-CPR-C1')            AS c1,
    dbops.fn_pgtap_crea_articolo('PGTAP-CPR-C2')            AS c2,
    dbops.fn_pgtap_crea_articolo('PGTAP-CPR-C3')            AS c3;

-- Due fatture del cliente: la seconda serve solo al guard 9.
CREATE TEMP TABLE tmp_cpr_fatt AS
SELECT (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura(
            'plafond per gruppo', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_cpr_mondo m)) f) AS f1,
       (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura(
            'plafond per gruppo bis', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_cpr_mondo m)) f) AS f2;

-- Scopo: una riga di fattura; ritorna l'id.
CREATE OR REPLACE FUNCTION pg_temp.fx_cpr_riga(
    p_fattura bigint, p_nr integer, p_art uuid, p_qta numeric, p_prezzo numeric)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, uom_id,
         qta, prezzo_unitario, iva_id, competenza_dal, competenza_al)
  SELECT p_fattura, p_nr, p_art, 'Riga ' || p_nr, (SELECT uom_id FROM tmp_cpr_refs),
         p_qta, p_prezzo, (SELECT iva_id FROM tmp_cpr_refs), CURRENT_DATE, CURRENT_DATE
  RETURNING id;
$fx$;

-- Il kit (gruppo K) e le tre righe da 10 (gruppo T), sulla prima fattura.
CREATE TEMP TABLE tmp_cpr_righe AS
SELECT 'K' AS gruppo, 1 AS ord, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 1, (SELECT c1 FROM tmp_cpr_refs), 2, 100) AS id
UNION ALL SELECT 'K', 2, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 2, (SELECT c2 FROM tmp_cpr_refs), 6, 10)
UNION ALL SELECT 'K', 3, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 3, (SELECT c3 FROM tmp_cpr_refs), 8, 30)
UNION ALL SELECT 'T', 1, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 4, (SELECT c1 FROM tmp_cpr_refs), 1, 10)
UNION ALL SELECT 'T', 2, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 5, (SELECT c2 FROM tmp_cpr_refs), 1, 10)
UNION ALL SELECT 'T', 3, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 6, (SELECT c3 FROM tmp_cpr_refs), 1, 10)
UNION ALL SELECT 'X', 1, pg_temp.fx_cpr_riga((SELECT f2 FROM tmp_cpr_fatt), 1, (SELECT c1 FROM tmp_cpr_refs), 1, 10);

-- Gli array di un gruppo, nell'ordine del documento (ids, imponibili).
CREATE TEMP TABLE tmp_cpr_gruppi AS
SELECT g.gruppo,
       array_agg(fr.id ORDER BY g.ord)              AS ids,
       array_agg(fr.imponibile_riga ORDER BY g.ord) AS imp
  FROM tmp_cpr_righe g
  JOIN vendite.fatture_righe fr ON fr.id = g.id
 GROUP BY g.gruppo;

-- Scopo: un titolo con plafond (NULL = senza tetto) su un anno suo: titoli
-- dello stesso tipo e periodo sovrapposto si escludono (EXCLUDE).
CREATE OR REPLACE FUNCTION pg_temp.fx_cpr_titolo(p_anno integer, p_plafond numeric)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, protocollo, riferimento, plafond)
  SELECT r.soggetto_id, r.emittente_fiscale_id,
         CASE WHEN p_plafond IS NULL THEN r.tipo_agevolata_id ELSE r.tipo_intento_id END,
         r.iva_id, 'TUTTO', make_date(p_anno, 1, 1), make_date(p_anno, 12, 31),
         CASE WHEN p_plafond IS NULL THEN NULL ELSE 'PGTAP-CPR-' || p_anno END,
         CASE WHEN p_plafond IS NULL THEN 'PGTAP-CPR-' || p_anno END,
         p_plafond
    FROM tmp_cpr_refs r
  RETURNING id;
$fx$;

CREATE TEMP TABLE tmp_cpr_tit AS
SELECT pg_temp.fx_cpr_titolo(2040, 200.00)  AS t_kit,
       pg_temp.fx_cpr_titolo(2041, 10.00)   AS t_cent,
       pg_temp.fx_cpr_titolo(2042, 9999.00) AS t_tutto,
       pg_temp.fx_cpr_titolo(2044, NULL)    AS t_senza;

-- Scopo: il consumo di un gruppo su un titolo, alla meta' dell'anno.
CREATE OR REPLACE FUNCTION pg_temp.fx_cpr_consuma(p_titolo bigint, p_gruppo text, p_anno integer)
RETURNS SETOF record LANGUAGE sql AS $fx$
  SELECT c.fattura_riga_id, c.imponibile, c.quota_coperta, c.quota_ordinaria,
         c.frazione, c.residuo_dopo, c.movimento_id
    FROM tmp_cpr_gruppi g,
         anagrafiche.fn_consuma_plafond_titolo_iva_righe(
             p_titolo, (SELECT f1 FROM tmp_cpr_fatt), g.ids, g.imp,
             make_date(p_anno, 6, 15)) c
   WHERE g.gruppo = p_gruppo;
$fx$;

-- Il consumo del kit letto una volta, in un'istruzione a se'.
CREATE TEMP TABLE tmp_cpr_k AS
SELECT * FROM pg_temp.fx_cpr_consuma((SELECT t_kit FROM tmp_cpr_tit), 'K', 2040)
    AS c(fattura_riga_id bigint, imponibile numeric, quota_coperta numeric,
         quota_ordinaria numeric, frazione numeric, residuo_dopo numeric, movimento_id bigint);

-- ============================================================
-- 1..4 — il kit su un plafond che non basta
-- ============================================================
SELECT is(
    (SELECT array_agg(k.quota_coperta ORDER BY g.ord)
       FROM tmp_cpr_k k JOIN tmp_cpr_righe g ON g.id = k.fattura_riga_id),
    ARRAY[80.00, 24.00, 96.00]::numeric[],
    '1) kit 500 su plafond 200: ogni componente prende 0,4 del suo imponibile (80, 24, 96)');

SELECT ok(
    (SELECT bool_and(k.frazione = 0.4)
            AND array_agg(k.quota_ordinaria ORDER BY g.ord) = ARRAY[120.00, 36.00, 144.00]::numeric[]
            AND bool_and(k.quota_coperta + k.quota_ordinaria = k.imponibile)
       FROM tmp_cpr_k k JOIN tmp_cpr_righe g ON g.id = k.fattura_riga_id),
    '2) frazione 0,4 su tutte le righe; ordinarie 120, 36, 144; coperta + ordinaria = imponibile');

SELECT ok(
    (SELECT count(*) = 3 AND sum(m.imponibile) = 200.00
            AND bool_and(m.fattura_riga_id IN (SELECT id FROM tmp_cpr_righe WHERE gruppo = 'K'))
       FROM anagrafiche.soggetti_titoli_iva_movimenti m
      WHERE m.titolo_iva_id = (SELECT t_kit FROM tmp_cpr_tit))
    AND (SELECT bool_and(residuo_dopo = 0) FROM tmp_cpr_k),
    '3) un movimento per riga, la somma e'' la quota coperta (200), il residuo e'' zero');

SELECT ok(
    (SELECT array_agg(c.quota_coperta ORDER BY c.fattura_riga_id)
       FROM pg_temp.fx_cpr_consuma((SELECT t_kit FROM tmp_cpr_tit), 'K', 2040)
            AS c(fattura_riga_id bigint, imponibile numeric, quota_coperta numeric,
                 quota_ordinaria numeric, frazione numeric, residuo_dopo numeric, movimento_id bigint))
      = (SELECT array_agg(quota_coperta ORDER BY fattura_riga_id) FROM tmp_cpr_k)
    AND (SELECT count(*) = 3 FROM anagrafiche.soggetti_titoli_iva_movimenti m
          WHERE m.titolo_iva_id = (SELECT t_kit FROM tmp_cpr_tit)),
    '4) idempotenza: la seconda chiamata rilegge le stesse quote e non scrive movimenti nuovi');

-- ============================================================
-- 5..8 — il centesimo, la copertura piena, la capienza zero, il titolo senza tetto
-- ============================================================
SELECT is(
    (SELECT array_agg(c.quota_coperta ORDER BY g.ord)::text
       FROM pg_temp.fx_cpr_consuma((SELECT t_cent FROM tmp_cpr_tit), 'T', 2041)
            AS c(fattura_riga_id bigint, imponibile numeric, quota_coperta numeric,
                 quota_ordinaria numeric, frazione numeric, residuo_dopo numeric, movimento_id bigint)
       JOIN tmp_cpr_righe g ON g.id = c.fattura_riga_id),
    '{3.33,3.33,3.34}',
    '5) tre righe da 10 su plafond 10: un terzo ciascuna arrotondato, il centesimo all''ultima');

SELECT ok(
    (SELECT bool_and(c.frazione = 1 AND c.quota_coperta = c.imponibile AND c.quota_ordinaria = 0)
       FROM pg_temp.fx_cpr_consuma((SELECT t_tutto FROM tmp_cpr_tit), 'K', 2042)
            AS c(fattura_riga_id bigint, imponibile numeric, quota_coperta numeric,
                 quota_ordinaria numeric, frazione numeric, residuo_dopo numeric, movimento_id bigint)),
    '6) plafond che basta: frazione 1, ogni riga coperta per intero');

-- ⚠️ La capienza zero si ottiene CONSUMANDO: il titolo del test 5 e' esaurito
--   (un plafond a zero lo vieta chk_soggetti_titoli_iva_plafond_pos). Qui ci
--   passa il kit, che su quel titolo non ha movimenti: niente idempotenza.
SELECT ok(
    (SELECT bool_and(c.frazione = 0 AND c.quota_coperta = 0 AND c.movimento_id IS NULL)
       FROM pg_temp.fx_cpr_consuma((SELECT t_cent FROM tmp_cpr_tit), 'K', 2041)
            AS c(fattura_riga_id bigint, imponibile numeric, quota_coperta numeric,
                 quota_ordinaria numeric, frazione numeric, residuo_dopo numeric, movimento_id bigint))
    AND (SELECT count(*) = 0 FROM anagrafiche.soggetti_titoli_iva_movimenti m
          WHERE m.titolo_iva_id = (SELECT t_cent FROM tmp_cpr_tit)
            AND m.fattura_riga_id IN (SELECT id FROM tmp_cpr_righe WHERE gruppo = 'K')),
    '7) capienza zero: frazione 0, tutto all''ordinaria, nessun movimento');

SELECT ok(
    (SELECT bool_and(c.frazione = 1 AND c.quota_coperta = c.imponibile AND c.movimento_id IS NULL)
       FROM pg_temp.fx_cpr_consuma((SELECT t_senza FROM tmp_cpr_tit), 'K', 2044)
            AS c(fattura_riga_id bigint, imponibile numeric, quota_coperta numeric,
                 quota_ordinaria numeric, frazione numeric, residuo_dopo numeric, movimento_id bigint))
    AND (SELECT count(*) = 0 FROM anagrafiche.soggetti_titoli_iva_movimenti m
          WHERE m.titolo_iva_id = (SELECT t_senza FROM tmp_cpr_tit)),
    '8) titolo senza tetto: copre tutto il gruppo e non scrive movimenti');

-- ============================================================
-- 9..12 — i guard di invocazione
-- ============================================================
-- Il frammento e' il PARAMETRO nella frase di E_TITOLO_IVA_CONSUMO_NON_INVOCABILE
-- («Consumo di plafond invocato senza %s.»): P0001 da solo passerebbe per
-- qualunque errore, e il parametro dice QUALE guard ha morso.
SELECT throws_like(
    format($$SELECT * FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(%s, %s, ARRAY[%s, %s]::bigint[], ARRAY[10, 10]::numeric[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE gruppo = 'T' AND ord = 1),
           (SELECT id FROM tmp_cpr_righe WHERE gruppo = 'X')),
    '%invocato senza fattura_riga_ids%',
    '9) una riga di un''altra fattura e'' rifiutata: il movimento legherebbe due documenti');

SELECT throws_like(
    format($$SELECT * FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(%s, %s, ARRAY[%s]::bigint[], ARRAY[10, 10]::numeric[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE gruppo = 'T' AND ord = 1)),
    '%invocato senza fattura_riga_ids%',
    '10) righe e imponibili di lunghezza diversa: rifiutato');

SELECT throws_like(
    format($$SELECT * FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(%s, %s, ARRAY[%s, NULL]::bigint[], ARRAY[10, 10]::numeric[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE gruppo = 'T' AND ord = 1)),
    '%invocato senza fattura_riga_ids%',
    '11) una riga NULL in un gruppo di due: rifiutato (NULL solo da sola, la forma storica)');

SELECT throws_like(
    format($$SELECT * FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(%s, %s, ARRAY[%s, %s]::bigint[], ARRAY[10, 0]::numeric[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE gruppo = 'T' AND ord = 1),
           (SELECT id FROM tmp_cpr_righe WHERE gruppo = 'T' AND ord = 2)),
    '%invocato senza imponibile%',
    '12) un imponibile non positivo: rifiutato');

SELECT * FROM finish();
ROLLBACK;
