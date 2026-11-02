-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.vw_fattura_righe_esposte e vendite.vw_fattura_righe_lista —
--   i TRE MODI di esporre un componente di kit in fattura (NASCOSTO,
--   DESCRITTIVO, VALORIZZATO).
--   Brief: brief-db-esposizione-componenti-kit-in-fattura (E-1, E-2, E-3).
--   changeSet: 20261001-41 -> -47, -56, -57.
--
-- ⭐ I CASI SI COSTRUISCONO (dbops.fn_pgtap_crea_fattura): nessun confronto con
--   la popolazione, quindi il file vale anche su un DB ricostruito da zero.
--   Dal DB si legge solo un'aliquota del catalogo config.iva.
--
-- LA FIXTURE — una fattura in bozza, quattro kit e una riga sciolta:
--   riga  kit  modo         prezzo
--     1   KM   NASCOSTO       10     ┐ un componente per modo
--     2   KM   DESCRITTIVO    20     │
--     3   KM   VALORIZZATO    30     ┘
--     4   KV   VALORIZZATO    40     ┐ kit SENZA RESTO (E-2)
--     5   KV   VALORIZZATO    50     ┘
--     6   KD   VALORIZZATO    60     ┐ valorizzato + descrittivo
--     7   KD   DESCRITTIVO    70     ┘
--     8   KN   NASCOSTO       80       tutto nascosto
--     9   --   (riga sciolta)  5
--   Totale del documento: 365.
--
-- ⛔ COSA PRESIDIA:
--   · il padre porta la somma dei NON valorizzati; il valorizzato ha prezzo e
--     importo suoi; il descrittivo nessuno dei due; il nascosto non compare;
--   · il kit senza resto resta come intestazione con importo NULL, non zero;
--   · ⭐ il componente resta legato al kit: livello 1, stessa kit_key, e
--     kit_riga_nr = riga_nr del suo padre;
--   · ⭐ il totale del documento non cambia al variare dell'esposizione: lo
--     stesso documento letto con tutti i componenti NASCOSTO, poi DESCRITTIVO,
--     poi VALORIZZATO da' sempre 365;
--   · la lista porta prezzo e importo dei valorizzati dentro `componenti`;
--   · il vocabolario e le FK.
-- ⚠️ Il caso KD presidia la LETTURA di E-2 scritta nel brief, sezione 9: con
--   valorizzati e descrittivi il padre porta il valore dei descrittivi (70),
--   perche' altrimenti quel valore sparirebbe dal documento.
--
-- Indice test (1..18):
--    1) il vocabolario ha i tre modi, per nome
--    2) la distinta nasce NASCOSTO per default
--    3) KM: il padre porta 10 + 20 = 30 (nascosto + descrittivo)
--    4) KM: compaiono il descrittivo e il valorizzato, il nascosto no
--    5) KM: il descrittivo non ha prezzo ne' importo
--    6) KM: il valorizzato ha prezzo e importo suoi (30)
--    7) KV: il padre resta, con importo e prezzo NULL (E-2)
--    8) KV: il padre ha comunque la sua quantita' (kit_qta, valorizzati compresi)
--    9) KV: i due valorizzati sotto il padre, coi loro importi
--   10) KD: il padre porta il valore del descrittivo (70)
--   11) KN: il padre porta 80, nessun componente sotto
--   12) ogni componente esposto e' legato al suo padre (kit_key, kit_riga_nr, livello 1)
--   13) ⭐ totale della vista = totale delle righe (365), coi modi misti
--   14) ⭐ tutto NASCOSTO: totale 365
--   15) ⭐ tutto DESCRITTIVO: totale 365
--   16) ⭐ tutto VALORIZZATO: totale 365
--   17) lista: il padre di KV ha importo_riga NULL, e i componenti portano
--       esposizione e importo
--   18) un modo fuori catalogo e' respinto dalla FK (23503)
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_e3m AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('esposizione tre modi');

CREATE TEMP TABLE tmp_e3m_iva AS
SELECT (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS iva_id;

-- ⭐ Un componente di kit e' un ARTICOLO della distinta, e dentro un kit due
--   componenti sono due articoli diversi: la vista raggruppa il kit
--   componente per componente (per articolo_id, 20261002-64). Senza articolo
--   le righe di un kit cadrebbero tutte nello stesso gruppo NULL e i loro
--   kit_qta si sommerebbero (KV: 1 + 1 = 2 kit).
CREATE TEMP TABLE tmp_e3m_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-E3M-KIT') AS padre_id,
       dbops.fn_pgtap_crea_articolo('PGTAP-E3M-C1')  AS c1,
       dbops.fn_pgtap_crea_articolo('PGTAP-E3M-C2')  AS c2,
       dbops.fn_pgtap_crea_articolo('PGTAP-E3M-C3')  AS c3;

-- Scopo: una riga di fattura, di kit se p_kit e' valorizzato; p_cmp = quale
--   componente (1, 2, 3) dentro il kit.
CREATE OR REPLACE FUNCTION pg_temp.fx_riga_e3m(
    p_nr integer, p_prezzo numeric, p_kit text DEFAULT NULL, p_modo varchar DEFAULT NULL,
    p_cmp integer DEFAULT NULL)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, qta, prezzo_unitario,
         iva_id, kit_key, kit_esposizione, kit_articolo_padre_id, kit_descrizione_padre, competenza_dal, competenza_al,
         kit_qta)
  SELECT (SELECT fattura_id FROM tmp_e3m), p_nr,
         (SELECT CASE p_cmp WHEN 1 THEN c1 WHEN 2 THEN c2 WHEN 3 THEN c3 END FROM tmp_e3m_art),
         'Riga ' || p_nr, 1, p_prezzo,
         (SELECT iva_id FROM tmp_e3m_iva),
         p_kit, p_modo,
         CASE WHEN p_kit IS NOT NULL THEN (SELECT padre_id FROM tmp_e3m_art) END,
         CASE WHEN p_kit IS NOT NULL THEN 'Padre ' || p_kit END, script.fn_data_operativa(), script.fn_data_operativa(),
         -- un kit per riga di componente (rev 2026-10-02: la quantita' del kit
         -- viene dalla riga padre del documento, non piu' dalla media)
         CASE WHEN p_kit IS NOT NULL THEN 1 END
  RETURNING id;
$fx$;

SELECT pg_temp.fx_riga_e3m(1, 10, 'KM', 'NASCOSTO',    1);
SELECT pg_temp.fx_riga_e3m(2, 20, 'KM', 'DESCRITTIVO', 2);
SELECT pg_temp.fx_riga_e3m(3, 30, 'KM', 'VALORIZZATO', 3);
SELECT pg_temp.fx_riga_e3m(4, 40, 'KV', 'VALORIZZATO', 1);
SELECT pg_temp.fx_riga_e3m(5, 50, 'KV', 'VALORIZZATO', 2);
SELECT pg_temp.fx_riga_e3m(6, 60, 'KD', 'VALORIZZATO', 1);
SELECT pg_temp.fx_riga_e3m(7, 70, 'KD', 'DESCRITTIVO', 2);
SELECT pg_temp.fx_riga_e3m(8, 80, 'KN', 'NASCOSTO',    1);
SELECT pg_temp.fx_riga_e3m(9, 5);

-- La vista letta una volta, sui modi misti della fixture.
CREATE TEMP TABLE tmp_e3m_v AS
SELECT * FROM vendite.vw_fattura_righe_esposte
 WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m);

-- ============================================================
-- 1..2 — vocabolario e default
-- ============================================================
SELECT is(
    (SELECT array_agg(codice_interno::text ORDER BY codice_interno)
       FROM config.esposizioni_componente
      WHERE codice_interno IN ('NASCOSTO', 'DESCRITTIVO', 'VALORIZZATO')),
    ARRAY['DESCRITTIVO', 'NASCOSTO', 'VALORIZZATO'],
    '1) il vocabolario ha i tre modi');

SELECT ok(
    (SELECT column_default LIKE '''NASCOSTO''%' AND is_nullable = 'NO'
       FROM information_schema.columns
      WHERE table_schema = 'catalogo' AND table_name = 'articoli_componenti'
        AND column_name = 'esposizione_in_fattura'),
    '2) una riga di distinta nasce NASCOSTO, e la colonna e'' NOT NULL');

-- ============================================================
-- 3..6 — KM: un componente per modo
-- ============================================================
SELECT is(
    (SELECT imponibile FROM tmp_e3m_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KM'),
    30::numeric,
    '3) KM: il padre porta nascosto + descrittivo (10 + 20), non il valorizzato');

SELECT is(
    (SELECT array_agg(esposizione::text ORDER BY riga_nr) FROM tmp_e3m_v
      WHERE tipo_riga = 'KIT_COMPONENTE' AND kit_key = 'KM'),
    ARRAY['DESCRITTIVO', 'VALORIZZATO'],
    '4) KM: compaiono il descrittivo e il valorizzato, il nascosto no');

SELECT ok(
    (SELECT prezzo_unitario IS NULL AND imponibile IS NULL AND sconto_percentuale IS NULL
       FROM tmp_e3m_v WHERE tipo_riga = 'KIT_COMPONENTE' AND riga_nr = 2),
    '5) KM: il descrittivo non ha prezzo, sconto ne'' importo (il valore e'' nel padre)');

SELECT ok(
    (SELECT prezzo_unitario = 30 AND imponibile = 30
       FROM tmp_e3m_v WHERE tipo_riga = 'KIT_COMPONENTE' AND riga_nr = 3),
    '6) KM: il valorizzato ha prezzo e importo suoi');

-- ============================================================
-- 7..9 — KV: il kit senza resto (E-2, strada a)
-- ============================================================
SELECT ok(
    (SELECT imponibile IS NULL AND prezzo_unitario IS NULL
       FROM tmp_e3m_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KV'),
    '7) KV: il padre resta come intestazione, importo e prezzo NULL (non zero)');

SELECT is(
    (SELECT qta FROM tmp_e3m_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KV'),
    1::numeric,
    '8) KV: il padre ha comunque la sua quantita'' (kit_qta dei componenti, valorizzati compresi)');

SELECT is(
    (SELECT array_agg(imponibile ORDER BY riga_nr) FROM tmp_e3m_v
      WHERE tipo_riga = 'KIT_COMPONENTE' AND kit_key = 'KV'),
    ARRAY[40, 50]::numeric[],
    '9) KV: i due valorizzati sotto il padre, coi loro importi');

-- ============================================================
-- 10..12 — KD, KN, il legame
-- ============================================================
SELECT is(
    (SELECT imponibile FROM tmp_e3m_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KD'),
    70::numeric,
    '10) KD: valorizzato + descrittivo, il padre porta il valore del descrittivo');

SELECT ok(
    (SELECT imponibile = 80 FROM tmp_e3m_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KN')
    AND NOT EXISTS (SELECT 1 FROM tmp_e3m_v WHERE tipo_riga = 'KIT_COMPONENTE' AND kit_key = 'KN'),
    '11) KN: tutto nascosto, il padre porta 80 e sotto non c''e'' niente');

-- ⭐ Mai una riga sciolta: ogni componente esposto sta a livello 1, sotto il
--    padre del SUO kit, e kit_riga_nr lo dice.
SELECT is(
    (SELECT count(*)::integer FROM tmp_e3m_v c
      WHERE c.tipo_riga = 'KIT_COMPONENTE'
        AND (c.livello <> 1
             OR NOT EXISTS (SELECT 1 FROM tmp_e3m_v p
                             WHERE p.tipo_riga = 'KIT_PADRE'
                               AND p.kit_key = c.kit_key
                               AND p.riga_nr = c.kit_riga_nr
                               AND p.ordinamento = c.ordinamento))),
    0,
    '12) ogni componente esposto e'' legato al suo padre: livello 1, kit_key, kit_riga_nr, ordinamento');

-- ============================================================
-- 13..16 — ⭐ il totale del documento non cambia mai
-- ============================================================
SELECT is(
    (SELECT sum(imponibile) FROM tmp_e3m_v),
    (SELECT sum(imponibile_riga) FROM vendite.fatture_righe
      WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m)),
    '13) totale della vista = totale delle righe, coi modi misti');

-- Lo STESSO documento, riletto con tutti i componenti in un modo solo. Ogni
-- verbo in un'istruzione a se', e la vista riletta dopo.
UPDATE vendite.fatture_righe SET kit_esposizione = 'NASCOSTO'
 WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m) AND kit_key IS NOT NULL;

SELECT is(
    (SELECT sum(imponibile) FROM vendite.vw_fattura_righe_esposte
      WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m)),
    365::numeric,
    '14) tutto NASCOSTO: il totale della vista resta 365');

UPDATE vendite.fatture_righe SET kit_esposizione = 'DESCRITTIVO'
 WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m) AND kit_key IS NOT NULL;

SELECT is(
    (SELECT sum(imponibile) FROM vendite.vw_fattura_righe_esposte
      WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m)),
    365::numeric,
    '15) tutto DESCRITTIVO: il totale della vista resta 365');

UPDATE vendite.fatture_righe SET kit_esposizione = 'VALORIZZATO'
 WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m) AND kit_key IS NOT NULL;

SELECT is(
    (SELECT sum(imponibile) FROM vendite.vw_fattura_righe_esposte
      WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m)),
    365::numeric,
    '16) tutto VALORIZZATO: il totale della vista resta 365 (i padri senza importo)');

-- ============================================================
-- 17..18 — la lista e la FK
-- ============================================================
-- (tutto VALORIZZATO dal passo 16: ogni padre e' senza resto)
SELECT ok(
    (SELECT l.importo_riga IS NULL
            AND l.componenti_numero = 2
            AND (SELECT array_agg((c ->> 'importo_riga')::numeric ORDER BY (c ->> 'riga_nr')::integer)
                   FROM jsonb_array_elements(l.componenti) AS j(c)) = ARRAY[40, 50]::numeric[]
            AND (SELECT bool_and(c ->> 'esposizione' = 'VALORIZZATO')
                   FROM jsonb_array_elements(l.componenti) AS j(c))
       FROM vendite.vw_fattura_righe_lista l
      WHERE l.fattura_id = (SELECT fattura_id FROM tmp_e3m)
        AND l.tipo_riga = 'KIT_PADRE' AND l.descrizione = 'Padre KV'),
    '17) lista: il padre senza resto ha importo_riga NULL, i componenti portano esposizione e importo');

SELECT throws_ok(
    $$UPDATE vendite.fatture_righe SET kit_esposizione = 'PGTAP_NON_ESISTE'
       WHERE fattura_id = (SELECT fattura_id FROM tmp_e3m) AND riga_nr = 1$$,
    '23503', NULL,
    '18) un modo fuori catalogo e'' respinto dalla FK');

SELECT * FROM finish();
ROLLBACK;
