-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_consuma_plafond_titolo_iva_righe — il plafond si
--   consuma sul NETTO della fattura: un kit si spezza come un'unita' sola
--   (D-5), le righe negative restituiscono (decisione C).
--   Brief: brief-db-bom-flag-quantita-e-kit-in-fattura §11 (D-5) e §13 (C).
--   changeSet: 20261003-07 (la funzione), 20261004-02 (il registro ammette
--   FATTURA negativo), 20261004-06 (il netto, i gruppi letti dalle righe;
--   firma invariata: p_imponibili resta come contratto di coerenza).
--
-- ⭐ I CASI SI COSTRUISCONO: cliente, fatture, righe e titoli nascono qui
--   (dbops.fn_pgtap_crea_mondo_cliente, dbops.fn_pgtap_crea_fattura). Dal DB si
--   leggono solo seed di catalogo (aliquota, unita' di misura, tipi titolo) e
--   l'emittente della whitelist dell'operatore di contesto.
--
-- IL KIT DI PROVA — tre righe, imponibile 500:
--     C1  2 x 100 = 200
--     C2  6 x  10 =  60
--     C3  8 x  30 = 240
--   Plafond 200 -> frazione 0,4 per tutti: 80, 24, 96 al titolo.
--
-- Indice test (1..20):
--    1) kit 500 su plafond 200: la stessa frazione per tutti (80, 24, 96)
--    2) frazione 0,4 e ordinarie 120, 36, 144
--    3) tre movimenti, uno per riga, che sommano 200; residuo 0
--    4) idempotenza: la seconda chiamata (righe in altro ordine) rilegge
--    5) il centesimo: un kit di tre righe da 10 su plafond 10 -> 3,33 3,33 3,34
--    6) plafond che copre tutto: frazione 1, quote = imponibili
--    7) capienza zero (il titolo del 5, esaurito): frazione 0, nessun movimento
--    8) titolo senza tetto: copre tutto e non scrive movimenti
--    9) ⭐ lo sconto: merce 1000 e sconto -100 su plafond 500 -> 600 e -100
--   10) ⭐ movimenti +600 e -100 (FATTURA col segno), utilizzato 500
--   11) ⭐ kit con componente negativo (+100, -30) su plafond 35 -> +50, -15
--   12) kit a netto zero (+50, -50): coperto per intero, consumo zero
--   13) una riga negativa senza positivi: all'ordinaria, nessun movimento
--   14) l'ordine e' quello di stampa: la riga sciolta 1 prima del kit 5-6
--   15) guard: un kit passato a meta'
--   16) guard: una riga di un'altra fattura
--   17) guard: una PARTE di plafond (riga_capofila_id valorizzata)
--   18) guard: una riga NULL
--   19) guard: una riga ripetuta
--   20) la forma a una riga e' ritirata (20261004-05)
--   21) guard: un imponibile diverso da quello della riga
--   22) ⭐ righe a 6 decimali (articolo che arrotonda a 6): quote e movimenti al
--       centesimo, somma esatta, le frazioni di centesimo nella quota ordinaria
-- ------------------------------------------------------------

-- ⭐ rev 2026-10-10 (brief-db-dati-fiscali-e-societari-del-soggetto, Parte D):
--   il «tipo senza plafond» della fixture e' USO_INDUSTRIALE, non piu'
--   AGEVOLATA_104. Da trgfn_soggetti_titoli_iva_guard_tipo_soggetto (20261010-92)
--   un titolo vigente deve essere ammesso dalla natura del titolare, e
--   l'agevolazione L. 104 spetta al solo privato: sul cliente della fixture (una
--   societa' di capitali) sarebbe rifiutata, e i rifiuti attesi dal guard di
--   coerenza (P0001) passerebbero per il motivo sbagliato.

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva). Le
-- tabelle dei titoli hanno una policy di perimetro emittente.
CREATE TEMP TABLE tmp_cpr_ctx AS
SELECT script.fn_pgtap_set_contesto_operatore() AS auth_user_id;

SELECT plan(22);

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
      WHERE t.codice_interno = 'USO_INDUSTRIALE')             AS tipo_senza_plafond_id,
    dbops.fn_pgtap_crea_articolo('PGTAP-CPR-C1')            AS c1,
    dbops.fn_pgtap_crea_articolo('PGTAP-CPR-C2')            AS c2,
    dbops.fn_pgtap_crea_articolo('PGTAP-CPR-C3')            AS c3,
    dbops.fn_pgtap_crea_articolo('PGTAP-CPR-KIT')           AS padre;

-- Cinque fatture del cliente, una per famiglia di casi: la seconda serve al
-- guard 16. L'idempotenza e' per (titolo, fattura), quindi casi diversi sulla
-- stessa fattura usano titoli diversi.
CREATE TEMP TABLE tmp_cpr_fatt AS
SELECT (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('plafond kit', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_cpr_mondo m)) f) AS f1,
       (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('plafond altra', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_cpr_mondo m)) f) AS f2,
       (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('plafond sconto', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_cpr_mondo m)) f) AS f3,
       (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('plafond negativi', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_cpr_mondo m)) f) AS f4,
       (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('plafond ordine', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_cpr_mondo m)) f) AS f5;

-- Scopo: una riga di fattura, sciolta (p_kit NULL) o componente di un kit;
-- ritorna l'id. Le colonne kit seguono chk_fatture_righe_kit_coerente.
CREATE OR REPLACE FUNCTION pg_temp.fx_cpr_riga(
    p_fattura bigint, p_nr integer, p_art uuid, p_qta numeric, p_prezzo numeric,
    p_kit text DEFAULT NULL)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, uom_id,
         qta, prezzo_unitario, iva_id, competenza_dal, competenza_al,
         kit_key, kit_esposizione, kit_articolo_padre_id, kit_descrizione_padre,
         kit_qta, kit_uom_id)
  SELECT p_fattura, p_nr, p_art, 'Riga ' || p_nr, r.uom_id,
         p_qta, p_prezzo, r.iva_id, script.fn_data_operativa(), script.fn_data_operativa(),
         p_kit,
         CASE WHEN p_kit IS NOT NULL THEN 'VALORIZZATO' END,
         CASE WHEN p_kit IS NOT NULL THEN r.padre END,
         CASE WHEN p_kit IS NOT NULL THEN 'Kit ' || p_kit END,
         CASE WHEN p_kit IS NOT NULL THEN 1 END,
         CASE WHEN p_kit IS NOT NULL THEN r.uom_id END
    FROM tmp_cpr_refs r
  RETURNING id;
$fx$;

CREATE TEMP TABLE tmp_cpr_righe AS
-- f1: il kit K (500) e il kit T (tre da 10)
SELECT 'K' AS caso, 1 AS ord, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 1, (SELECT c1 FROM tmp_cpr_refs), 2, 100, 'K') AS id
UNION ALL SELECT 'K', 2, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 2, (SELECT c2 FROM tmp_cpr_refs), 6, 10, 'K')
UNION ALL SELECT 'K', 3, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 3, (SELECT c3 FROM tmp_cpr_refs), 8, 30, 'K')
UNION ALL SELECT 'T', 1, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 4, (SELECT c1 FROM tmp_cpr_refs), 1, 10, 'T')
UNION ALL SELECT 'T', 2, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 5, (SELECT c2 FROM tmp_cpr_refs), 1, 10, 'T')
UNION ALL SELECT 'T', 3, pg_temp.fx_cpr_riga((SELECT f1 FROM tmp_cpr_fatt), 6, (SELECT c3 FROM tmp_cpr_refs), 1, 10, 'T')
-- f2: la riga dell'altra fattura (guard 16)
UNION ALL SELECT 'X', 1, pg_temp.fx_cpr_riga((SELECT f2 FROM tmp_cpr_fatt), 1, (SELECT c1 FROM tmp_cpr_refs), 1, 10)
-- f3: merce 1000 e sconto -100, sciolte
UNION ALL SELECT 'S', 1, pg_temp.fx_cpr_riga((SELECT f3 FROM tmp_cpr_fatt), 1, (SELECT c1 FROM tmp_cpr_refs), 10, 100)
UNION ALL SELECT 'S', 2, pg_temp.fx_cpr_riga((SELECT f3 FROM tmp_cpr_fatt), 2, (SELECT c2 FROM tmp_cpr_refs), 1, -100)
-- f4: kit con componente negativo, kit a netto zero, negativo da solo
UNION ALL SELECT 'E', 1, pg_temp.fx_cpr_riga((SELECT f4 FROM tmp_cpr_fatt), 1, (SELECT c1 FROM tmp_cpr_refs), 1, 100, 'E')
UNION ALL SELECT 'E', 2, pg_temp.fx_cpr_riga((SELECT f4 FROM tmp_cpr_fatt), 2, (SELECT c2 FROM tmp_cpr_refs), 1, -30, 'E')
UNION ALL SELECT 'Z', 1, pg_temp.fx_cpr_riga((SELECT f4 FROM tmp_cpr_fatt), 3, (SELECT c1 FROM tmp_cpr_refs), 1, 50, 'Z')
UNION ALL SELECT 'Z', 2, pg_temp.fx_cpr_riga((SELECT f4 FROM tmp_cpr_fatt), 4, (SELECT c2 FROM tmp_cpr_refs), 1, -50, 'Z')
UNION ALL SELECT 'N', 1, pg_temp.fx_cpr_riga((SELECT f4 FROM tmp_cpr_fatt), 5, (SELECT c3 FROM tmp_cpr_refs), 1, -40)
-- f5: il kit alle righe 5-6, la riga sciolta alla riga 1
UNION ALL SELECT 'M', 1, pg_temp.fx_cpr_riga((SELECT f5 FROM tmp_cpr_fatt), 5, (SELECT c1 FROM tmp_cpr_refs), 1, 10, 'M')
UNION ALL SELECT 'M', 2, pg_temp.fx_cpr_riga((SELECT f5 FROM tmp_cpr_fatt), 6, (SELECT c2 FROM tmp_cpr_refs), 1, 10, 'M')
UNION ALL SELECT 'L', 1, pg_temp.fx_cpr_riga((SELECT f5 FROM tmp_cpr_fatt), 1, (SELECT c3 FROM tmp_cpr_refs), 1, 10);

-- La PARTE di plafond della riga sciolta di f5 (guard 17).
CREATE TEMP TABLE tmp_cpr_parte AS
WITH p AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, uom_id,
         qta, prezzo_unitario, iva_id, competenza_dal, competenza_al, riga_capofila_id)
  SELECT (SELECT f5 FROM tmp_cpr_fatt), 2, r.c3, 'Parte', r.uom_id, 1, 5, r.iva_id,
         script.fn_data_operativa(), script.fn_data_operativa(), (SELECT id FROM tmp_cpr_righe WHERE caso = 'L')
    FROM tmp_cpr_refs r
  RETURNING id)
SELECT id FROM p;

-- Scopo: un titolo con plafond (NULL = senza tetto) su un anno suo: titoli
-- dello stesso tipo e periodo sovrapposto si escludono (EXCLUDE).
CREATE OR REPLACE FUNCTION pg_temp.fx_cpr_titolo(p_anno integer, p_plafond numeric)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, protocollo, riferimento, plafond)
  SELECT r.soggetto_id, r.emittente_fiscale_id,
         CASE WHEN p_plafond IS NULL THEN r.tipo_senza_plafond_id ELSE r.tipo_intento_id END,
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
       pg_temp.fx_cpr_titolo(2044, NULL)    AS t_senza,
       pg_temp.fx_cpr_titolo(2045, 500.00)  AS t_sconto,
       pg_temp.fx_cpr_titolo(2046, 35.00)   AS t_neg,
       pg_temp.fx_cpr_titolo(2047, 10.00)   AS t_zero,
       pg_temp.fx_cpr_titolo(2048, 100.00)  AS t_solo,
       pg_temp.fx_cpr_titolo(2049, 15.00)   AS t_ordine;

-- Scopo: la chiamata alla madre con gli imponibili DELLE RIGHE, nell'ordine
-- dell'array (una riga inesistente o NULL da' un imponibile NULL: lo ferma il
-- guard delle righe, che viene prima).
CREATE OR REPLACE FUNCTION pg_temp.fx_cpr_chiama(
    p_titolo bigint, p_fattura bigint, p_ids bigint[], p_data date)
RETURNS TABLE (fattura_riga_id bigint, imponibile numeric, quota_coperta numeric,
               quota_ordinaria numeric, frazione numeric, residuo_dopo numeric,
               movimento_id bigint)
LANGUAGE sql AS $fx$
  SELECT c.*
    FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
             p_titolo, p_fattura, p_ids,
             (SELECT array_agg(fr.imponibile_riga ORDER BY x.n)
                FROM unnest(p_ids) WITH ORDINALITY AS x(id, n)
                LEFT JOIN vendite.fatture_righe fr ON fr.id = x.id),
             p_data) c;
$fx$;

-- Scopo: il consumo delle righe di uno o piu' casi su un titolo, a meta'
-- dell'anno. Le righe si passano in ordine INVERSO: la madre l'ordine lo
-- legge dalle righe, non dall'array.
CREATE OR REPLACE FUNCTION pg_temp.fx_cpr_consuma(
    p_titolo bigint, p_fattura bigint, p_casi text[], p_anno integer)
RETURNS TABLE (fattura_riga_id bigint, imponibile numeric, quota_coperta numeric,
               quota_ordinaria numeric, frazione numeric, residuo_dopo numeric,
               movimento_id bigint)
LANGUAGE sql AS $fx$
  SELECT c.*
    FROM pg_temp.fx_cpr_chiama(
             p_titolo, p_fattura,
             (SELECT array_agg(g.id ORDER BY g.caso DESC, g.ord DESC)
                FROM tmp_cpr_righe g WHERE g.caso = ANY (p_casi)),
             make_date(p_anno, 6, 15)) c;
$fx$;

-- Il consumo del kit letto una volta, in un'istruzione a se'.
CREATE TEMP TABLE tmp_cpr_k AS
SELECT * FROM pg_temp.fx_cpr_consuma((SELECT t_kit FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt), ARRAY['K'], 2040);

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
            AND bool_and(m.fattura_riga_id IN (SELECT id FROM tmp_cpr_righe WHERE caso = 'K'))
       FROM anagrafiche.soggetti_titoli_iva_movimenti m
      WHERE m.titolo_iva_id = (SELECT t_kit FROM tmp_cpr_tit))
    AND (SELECT bool_and(residuo_dopo = 0) FROM tmp_cpr_k),
    '3) un movimento per riga, la somma e'' la quota coperta (200), il residuo e'' zero');

SELECT ok(
    (SELECT array_agg(c.quota_coperta ORDER BY c.fattura_riga_id)
       FROM pg_temp.fx_cpr_consuma((SELECT t_kit FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt), ARRAY['K'], 2040) c)
      = (SELECT array_agg(quota_coperta ORDER BY fattura_riga_id) FROM tmp_cpr_k)
    AND (SELECT count(*) = 3 FROM anagrafiche.soggetti_titoli_iva_movimenti m
          WHERE m.titolo_iva_id = (SELECT t_kit FROM tmp_cpr_tit)),
    '4) idempotenza: la seconda chiamata rilegge le stesse quote e non scrive movimenti nuovi');

-- ============================================================
-- 5..8 — il centesimo, la copertura piena, la capienza zero, il titolo senza tetto
-- ============================================================
SELECT is(
    (SELECT array_agg(c.quota_coperta ORDER BY g.ord)::text
       FROM pg_temp.fx_cpr_consuma((SELECT t_cent FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt), ARRAY['T'], 2041) c
       JOIN tmp_cpr_righe g ON g.id = c.fattura_riga_id),
    '{3.33,3.33,3.34}',
    '5) kit di tre righe da 10 su plafond 10: un terzo ciascuna arrotondato, il centesimo all''ultima');

SELECT ok(
    (SELECT bool_and(c.frazione = 1 AND c.quota_coperta = c.imponibile AND c.quota_ordinaria = 0)
       FROM pg_temp.fx_cpr_consuma((SELECT t_tutto FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt), ARRAY['K'], 2042) c),
    '6) plafond che basta: frazione 1, ogni riga coperta per intero');

-- ⚠️ La capienza zero si ottiene CONSUMANDO: il titolo del test 5 e' esaurito
--   (un plafond a zero lo vieta chk_soggetti_titoli_iva_plafond_pos). Qui ci
--   passa il kit K, che su quel titolo non ha movimenti: niente idempotenza.
SELECT ok(
    (SELECT bool_and(c.frazione = 0 AND c.quota_coperta = 0 AND c.movimento_id IS NULL)
       FROM pg_temp.fx_cpr_consuma((SELECT t_cent FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt), ARRAY['K'], 2041) c)
    AND (SELECT count(*) = 0 FROM anagrafiche.soggetti_titoli_iva_movimenti m
          WHERE m.titolo_iva_id = (SELECT t_cent FROM tmp_cpr_tit)
            AND m.fattura_riga_id IN (SELECT id FROM tmp_cpr_righe WHERE caso = 'K')),
    '7) capienza zero: frazione 0, tutto all''ordinaria, nessun movimento');

SELECT ok(
    (SELECT bool_and(c.frazione = 1 AND c.quota_coperta = c.imponibile AND c.movimento_id IS NULL)
       FROM pg_temp.fx_cpr_consuma((SELECT t_senza FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt), ARRAY['K'], 2044) c)
    AND (SELECT count(*) = 0 FROM anagrafiche.soggetti_titoli_iva_movimenti m
          WHERE m.titolo_iva_id = (SELECT t_senza FROM tmp_cpr_tit)),
    '8) titolo senza tetto: copre tutto il gruppo e non scrive movimenti');

-- ============================================================
-- 9..14 — il netto (decisione C)
-- ============================================================
CREATE TEMP TABLE tmp_cpr_s AS
SELECT * FROM pg_temp.fx_cpr_consuma((SELECT t_sconto FROM tmp_cpr_tit), (SELECT f3 FROM tmp_cpr_fatt), ARRAY['S'], 2045);

SELECT is(
    (SELECT array_agg(s.quota_coperta || '/' || round(s.frazione, 4) ORDER BY g.ord)
       FROM tmp_cpr_s s JOIN tmp_cpr_righe g ON g.id = s.fattura_riga_id),
    ARRAY['600.00/0.6000', '-100.00/1.0000'],
    '9) merce 1000 e sconto -100 su plafond 500: merce 600 al titolo (0,6), sconto -100 al titolo (1)');

SELECT ok(
    (SELECT array_agg(m.imponibile ORDER BY m.id) = ARRAY[600.00, -100.00]::numeric[]
            AND bool_and(m.tipo_movimento = 'FATTURA')
       FROM anagrafiche.soggetti_titoli_iva_movimenti m
      WHERE m.titolo_iva_id = (SELECT t_sconto FROM tmp_cpr_tit))
    AND (SELECT t.imponibile_utilizzato = 500.00 FROM anagrafiche.soggetti_titoli_iva t
          WHERE t.id = (SELECT t_sconto FROM tmp_cpr_tit)),
    '10) movimenti FATTURA +600 e -100, prima il positivo: consumo netto 500, la capienza');

SELECT is(
    (SELECT array_agg(c.quota_coperta || '/' || round(c.frazione, 4) ORDER BY g.ord)
       FROM pg_temp.fx_cpr_consuma((SELECT t_neg FROM tmp_cpr_tit), (SELECT f4 FROM tmp_cpr_fatt), ARRAY['E'], 2046) c
       JOIN tmp_cpr_righe g ON g.id = c.fattura_riga_id),
    ARRAY['50.00/0.5000', '-15.00/0.5000'],
    '11) kit +100 -30 (netto 70) su plafond 35: frazione 0,5 per entrambi, +50 e -15');

SELECT ok(
    (SELECT bool_and(c.frazione = 1 AND c.quota_coperta = c.imponibile)
       FROM pg_temp.fx_cpr_consuma((SELECT t_zero FROM tmp_cpr_tit), (SELECT f4 FROM tmp_cpr_fatt), ARRAY['Z'], 2047) c)
    AND (SELECT t.imponibile_utilizzato = 0 FROM anagrafiche.soggetti_titoli_iva t
          WHERE t.id = (SELECT t_zero FROM tmp_cpr_tit)),
    '12) kit a netto zero (+50 -50): coperto per intero, consumo zero, nessun conto sotto zero');

SELECT ok(
    (SELECT bool_and(c.frazione = 0 AND c.quota_coperta = 0 AND c.movimento_id IS NULL)
       FROM pg_temp.fx_cpr_consuma((SELECT t_solo FROM tmp_cpr_tit), (SELECT f4 FROM tmp_cpr_fatt), ARRAY['N'], 2048) c),
    '13) una riga negativa senza positivi: all''ordinaria, nessun movimento (la restituzione oltre e'' della NC)');

SELECT is(
    (SELECT array_agg(c.quota_coperta ORDER BY g.caso, g.ord)
       FROM pg_temp.fx_cpr_consuma((SELECT t_ordine FROM tmp_cpr_tit), (SELECT f5 FROM tmp_cpr_fatt), ARRAY['L', 'M'], 2049) c
       JOIN tmp_cpr_righe g ON g.id = c.fattura_riga_id),
    ARRAY[10.00, 2.50, 2.50]::numeric[],
    '14) ordine di stampa: la riga sciolta (riga 1) per intera, il kit (righe 5-6) col resto');

-- ============================================================
-- 15..20 — i guard di invocazione, e la forma ritirata
-- ============================================================
-- Il frammento e' il PARAMETRO nella frase di E_TITOLO_IVA_CONSUMO_NON_INVOCABILE
-- («Consumo di plafond invocato senza %s.»): P0001 da solo passerebbe per
-- qualunque errore, e il parametro dice QUALE guard ha morso.
SELECT throws_like(
    format($$SELECT * FROM pg_temp.fx_cpr_chiama(%s, %s, ARRAY[%s, %s]::bigint[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f1 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'K' AND ord = 1),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'K' AND ord = 2)),
    '%invocato senza fattura_riga_ids%',
    '15) un kit passato a meta'': rifiutato, le due meta'' avrebbero due frazioni');

SELECT throws_like(
    format($$SELECT * FROM pg_temp.fx_cpr_chiama(%s, %s, ARRAY[%s, %s]::bigint[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f5 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'L'),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'X')),
    '%invocato senza fattura_riga_ids%',
    '16) una riga di un''altra fattura e'' rifiutata: il movimento legherebbe due documenti');

SELECT throws_like(
    format($$SELECT * FROM pg_temp.fx_cpr_chiama(%s, %s, ARRAY[%s, %s]::bigint[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f5 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'L'),
           (SELECT id FROM tmp_cpr_parte)),
    '%invocato senza fattura_riga_ids%',
    '17) una parte di plafond e'' rifiutata: il movimento sta sulla capofila');

SELECT throws_like(
    format($$SELECT * FROM pg_temp.fx_cpr_chiama(%s, %s, ARRAY[%s, NULL]::bigint[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f5 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'L')),
    '%invocato senza fattura_riga_ids%',
    '18) una riga NULL e'' rifiutata: un movimento di fattura nomina sempre la sua riga');

SELECT throws_like(
    format($$SELECT * FROM pg_temp.fx_cpr_chiama(%s, %s, ARRAY[%s, %s]::bigint[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f5 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'L'),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'L')),
    '%invocato senza fattura_riga_ids%',
    '19) una riga ripetuta e'' rifiutata: due movimenti sulla stessa riga');

SELECT ok(
    to_regprocedure('anagrafiche.fn_consuma_plafond_titolo_iva(bigint, bigint, numeric, date, bigint, uuid)') IS NULL,
    '20) la forma a una riga e'' ritirata (20261004-05)');

-- ⭐ L'imponibile dichiarato deve essere quello della riga: un chiamante che ha
--   ragionato su una riga poi cambiata spezzerebbe quantita' e kit su un numero
--   che non c'e' piu'.
SELECT throws_like(
    format($$SELECT * FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(%s, %s, ARRAY[%s]::bigint[], ARRAY[9.99]::numeric[], DATE '2042-06-15')$$,
           (SELECT t_tutto FROM tmp_cpr_tit), (SELECT f5 FROM tmp_cpr_fatt),
           (SELECT id FROM tmp_cpr_righe WHERE caso = 'L')),
    '%invocato senza imponibili%',
    '21) un imponibile diverso da quello della riga e'' rifiutato');

-- ============================================================
-- 22 — righe con piu' decimali del registro
-- ============================================================
-- ⭐ imponibile_riga e' numeric(18,6) e l'articolo puo' arrotondare fino a 6
--   decimali (chk_regole_decimali_importi 0..6); il registro e' numeric(15,2).
--   La quota diventa un movimento, quindi si calcola alla scala del registro:
--   prima (20261004-06, prima stesura) usciva a 6 decimali, l'INSERT la
--   arrotondava in silenzio e una frazione di centesimo diventava uno zero che
--   chk_stiva_movimenti_segno rifiutava. Il caso lo COSTRUISCE: tre righe da
--   3,333333 / 3,333333 / 3,333334 (10 in tutto) su un plafond di 5.
INSERT INTO vendite.articolo_regole_fatturazione (articolo_id, arrotondamento_importi_dec)
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-CPR-DEC6'), 6;

INSERT INTO tmp_cpr_righe
SELECT 'D', v.ord,
       pg_temp.fx_cpr_riga((SELECT f5 FROM tmp_cpr_fatt), 20 + v.ord,
                           (SELECT a.id FROM catalogo.articoli a WHERE a.codice = 'PGTAP-CPR-DEC6'),
                           1, v.prezzo, 'D')
  FROM (VALUES (1, 3.333333), (2, 3.333333), (3, 3.333334)) v(ord, prezzo);

CREATE TEMP TABLE tmp_cpr_d AS
SELECT * FROM pg_temp.fx_cpr_consuma(pg_temp.fx_cpr_titolo(2051, 5.00), (SELECT f5 FROM tmp_cpr_fatt), ARRAY['D'], 2051);

SELECT ok(
    (SELECT sum(d.quota_coperta) = 5.00
            AND bool_and(d.quota_coperta = round(d.quota_coperta, 2))
            AND bool_and(d.quota_coperta + d.quota_ordinaria = d.imponibile)
            AND sum(d.imponibile) = 10
       FROM tmp_cpr_d d)
    AND (SELECT count(*) = 3 AND sum(m.imponibile) = 5.00
           FROM anagrafiche.soggetti_titoli_iva_movimenti m
          WHERE m.fattura_riga_id IN (SELECT id FROM tmp_cpr_righe WHERE caso = 'D')),
    '22) righe a 6 decimali su plafond 5: quote e movimenti al centesimo, somma 5,00, ogni quota + ordinaria = imponibile');

SELECT * FROM finish();
ROLLBACK;
