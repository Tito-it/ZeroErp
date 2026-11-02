-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: quantita' e UoM della riga del kit, e periodo di competenza, in
--   vendite.vw_fattura_righe_esposte e vendite.vw_fattura_righe_lista.
--   Brief: brief-db-bom-flag-quantita-e-kit-in-fattura (D-1, D-2, D-3, D-3.1).
--   changeSet: 20261002-60 -> -67; 20261003-06 (test 26).
--
-- ⭐ I CASI SI COSTRUISCONO (dbops.fn_pgtap_crea_fattura): nessun confronto con
--   la popolazione. Dal DB si leggono solo un'aliquota (config.iva) e quattro
--   unita' di misura (catalogo.unita_misura), entrambe seed di catalogo.
--
-- IL KIT DI PROVA — misto, come il modello ammette (D-2): venduto in quantita'
--   2, unita' del kit u_kit; tre componenti di unita' DIVERSE fra loro:
--     C1  u1  qta 2  x 100 = 200
--     C2  u2  qta 6  x  10 =  60
--     C3  u3  qta 8  x  30 = 240        totale del kit 500
--   Prima del 2026-10-02 la riga del kit diceva avg(qta) = 5.33 e max(uom):
--   una media fra unita' diverse e un'unita' a caso.
--
-- LA FIXTURE — una fattura in bozza:
--   KN  il kit, tutto NASCOSTO        ┐ lo stesso kit nei tre modi: la riga
--   KD  il kit, tutto DESCRITTIVO     │ del kit dice sempre «2 u_kit»
--   KV  il kit, tutto VALORIZZATO     ┘
--   KP  un kit al mese su gennaio e febbraio (C1 1, C2 3, C3 4 per mese)
--   KX  nota parziale: C1 di 2 kit, C2 di 1 kit — il kit non ha una quantita'
--   KS  C1 spezzato in due righe per prezzo (1 + 1 kit), C2 in una (2 kit)
--
-- Indice test (1..24):
--    1) KN: la riga del kit e' 2 u_kit, 250 l'una, 500
--    2) KN: sotto non c'e' niente
--    3) KD: i componenti sotto il kit, ognuno con la sua unita' e quantita'
--    4) KV: la riga del kit e' 2 u_kit, senza importo (kit senza resto)
--    5) KV: i componenti coi loro importi e le loro unita'
--    6) le righe puntuali non hanno un periodo da stampare
--    7) KP: due righe del kit, una per periodo, 1 kit a 250 ciascuna
--    8) KP: ha_periodo vero, coi due inizi
--    9) KP: ogni componente sta sotto il kit del SUO periodo
--   10) KX: componenti discordanti -> quantita' e prezzo del kit NULL, importo 230
--   11) KS: componente spezzato per prezzo -> 2 kit
--   12) ⭐ totale del documento: vista = tabella
--   13) lista: KP sono due padri, chiavi diverse, tre componenti ciascuno
--   14) lista: il periodo arriva in coda (ha_periodo)
--   15) una riga senza periodo e' respinta (NOT NULL)
--   16) un periodo rovesciato e' respinto (CHECK)
--   17) una riga di kit senza kit_qta e' respinta (CHECK di coerenza)
--   18) kit_uom_id fuori da un kit e' respinta (CHECK di coerenza)
--   19) le competenze sono NOT NULL e senza default
--   20) uom_operativa_id NOT NULL sui cinque *_componenti
--   21) il trigger di immutabilita' ricreato ascolta ancora i campi di struttura
--   22) la distinta non ha piu' partecipa_qta
--   23) la distinta non ha piu' determina_qta_padre
--   24) i due parametri di default ritirati non ci sono piu'
--   25) ⭐ una riga di kit senza articolo e' respinta (chk_fatture_righe_kit_articolo,
--       20261002-43): la vista conta i kit per articolo, e due righe senza
--       articolo sommerebbero le loro quantita'
--   26) ⭐ lista: periodo_dal / periodo_al (20261003-06, R-DB-B9) valorizzati
--       solo dove c'e' un periodo; sulle righe puntuali NULL, anche se
--       competenza_dal/_al ci sono. Sono le sorgenti delle colonne di lista
--       «Periodo dal» e «Periodo al»: l'export non deve mostrare una data dove
--       il documento non stampa un periodo
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(26);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_kqp AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('kit quantita e periodo');

CREATE TEMP TABLE tmp_kqp_ref AS
SELECT (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS iva_id,
       dbops.fn_pgtap_crea_articolo('PGTAP-KQP-KIT') AS padre_id,
       dbops.fn_pgtap_crea_articolo('PGTAP-KQP-C1')  AS c1,
       dbops.fn_pgtap_crea_articolo('PGTAP-KQP-C2')  AS c2,
       dbops.fn_pgtap_crea_articolo('PGTAP-KQP-C3')  AS c3;

-- Quattro unita' distinte del catalogo: la prima e' quella del kit.
CREATE TEMP TABLE tmp_kqp_u AS
SELECT u[1] AS u_kit, u[2] AS u1, u[3] AS u2, u[4] AS u3
  FROM (SELECT array_agg(id ORDER BY id) AS u
          FROM (SELECT id FROM catalogo.unita_misura
                 WHERE attivo IS TRUE ORDER BY id LIMIT 4) x) y;

-- Scopo: una riga di componente di kit.
CREATE OR REPLACE FUNCTION pg_temp.fx_kqp(
    p_nr integer, p_kit text, p_modo varchar, p_art uuid, p_uom bigint,
    p_qta numeric, p_prezzo numeric, p_kit_qta numeric,
    p_dal date DEFAULT script.fn_data_operativa(), p_al date DEFAULT script.fn_data_operativa())
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, uom_id,
         qta, prezzo_unitario, iva_id, kit_key, kit_esposizione, kit_articolo_padre_id,
         kit_descrizione_padre, kit_qta, kit_uom_id, competenza_dal, competenza_al)
  SELECT (SELECT fattura_id FROM tmp_kqp), p_nr, p_art, 'Riga ' || p_nr, p_uom,
         p_qta, p_prezzo, (SELECT iva_id FROM tmp_kqp_ref), p_kit, p_modo,
         (SELECT padre_id FROM tmp_kqp_ref), 'Kit ' || p_kit,
         p_kit_qta, (SELECT u_kit FROM tmp_kqp_u), p_dal, p_al
  RETURNING id;
$fx$;

-- Scopo: il kit misto (2 kit) in un modo solo.
CREATE OR REPLACE FUNCTION pg_temp.fx_kqp_kit(p_base integer, p_kit text, p_modo varchar)
RETURNS void LANGUAGE sql AS $fx$
  SELECT pg_temp.fx_kqp(p_base + 1, p_kit, p_modo, (SELECT c1 FROM tmp_kqp_ref), (SELECT u1 FROM tmp_kqp_u), 2, 100, 2);
  SELECT pg_temp.fx_kqp(p_base + 2, p_kit, p_modo, (SELECT c2 FROM tmp_kqp_ref), (SELECT u2 FROM tmp_kqp_u), 6,  10, 2);
  SELECT pg_temp.fx_kqp(p_base + 3, p_kit, p_modo, (SELECT c3 FROM tmp_kqp_ref), (SELECT u3 FROM tmp_kqp_u), 8,  30, 2);
$fx$;

SELECT pg_temp.fx_kqp_kit(10, 'KN', 'NASCOSTO');
SELECT pg_temp.fx_kqp_kit(20, 'KD', 'DESCRITTIVO');
SELECT pg_temp.fx_kqp_kit(30, 'KV', 'VALORIZZATO');

-- KP: un kit al mese, gennaio e febbraio 2026.
SELECT pg_temp.fx_kqp(41, 'KP', 'DESCRITTIVO', (SELECT c1 FROM tmp_kqp_ref), (SELECT u1 FROM tmp_kqp_u), 1, 100, 1, DATE '2026-01-01', DATE '2026-01-31');
SELECT pg_temp.fx_kqp(42, 'KP', 'DESCRITTIVO', (SELECT c2 FROM tmp_kqp_ref), (SELECT u2 FROM tmp_kqp_u), 3,  10, 1, DATE '2026-01-01', DATE '2026-01-31');
SELECT pg_temp.fx_kqp(43, 'KP', 'DESCRITTIVO', (SELECT c3 FROM tmp_kqp_ref), (SELECT u3 FROM tmp_kqp_u), 4,  30, 1, DATE '2026-01-01', DATE '2026-01-31');
SELECT pg_temp.fx_kqp(51, 'KP', 'DESCRITTIVO', (SELECT c1 FROM tmp_kqp_ref), (SELECT u1 FROM tmp_kqp_u), 1, 100, 1, DATE '2026-02-01', DATE '2026-02-28');
SELECT pg_temp.fx_kqp(52, 'KP', 'DESCRITTIVO', (SELECT c2 FROM tmp_kqp_ref), (SELECT u2 FROM tmp_kqp_u), 3,  10, 1, DATE '2026-02-01', DATE '2026-02-28');
SELECT pg_temp.fx_kqp(53, 'KP', 'DESCRITTIVO', (SELECT c3 FROM tmp_kqp_ref), (SELECT u3 FROM tmp_kqp_u), 4,  30, 1, DATE '2026-02-01', DATE '2026-02-28');

-- KX: nota parziale, i componenti non raccontano lo stesso numero di kit.
SELECT pg_temp.fx_kqp(61, 'KX', 'NASCOSTO', (SELECT c1 FROM tmp_kqp_ref), (SELECT u1 FROM tmp_kqp_u), 2, 100, 2);
SELECT pg_temp.fx_kqp(62, 'KX', 'NASCOSTO', (SELECT c2 FROM tmp_kqp_ref), (SELECT u2 FROM tmp_kqp_u), 3,  10, 1);

-- KS: C1 in due righe (prezzi diversi, un kit ciascuna), C2 in una da due kit.
SELECT pg_temp.fx_kqp(71, 'KS', 'NASCOSTO', (SELECT c1 FROM tmp_kqp_ref), (SELECT u1 FROM tmp_kqp_u), 1, 100, 1);
SELECT pg_temp.fx_kqp(72, 'KS', 'NASCOSTO', (SELECT c1 FROM tmp_kqp_ref), (SELECT u1 FROM tmp_kqp_u), 1, 110, 1);
SELECT pg_temp.fx_kqp(73, 'KS', 'NASCOSTO', (SELECT c2 FROM tmp_kqp_ref), (SELECT u2 FROM tmp_kqp_u), 6,  10, 2);

-- La vista letta una volta, in un'istruzione a se'.
CREATE TEMP TABLE tmp_kqp_v AS
SELECT * FROM vendite.vw_fattura_righe_esposte
 WHERE fattura_id = (SELECT fattura_id FROM tmp_kqp);

-- ============================================================
-- 1..6 — il kit misto nei tre modi
-- ============================================================
SELECT ok(
    (SELECT qta = 2 AND uom_id = (SELECT u_kit FROM tmp_kqp_u)
            AND prezzo_unitario = 250 AND imponibile = 500
       FROM tmp_kqp_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KN'),
    '1) KN: la riga del kit e'' 2 nell''unita'' del kit, 250 l''una, 500');

SELECT is(
    (SELECT count(*)::integer FROM tmp_kqp_v WHERE tipo_riga = 'KIT_COMPONENTE' AND kit_key = 'KN'),
    0,
    '2) KN: tutto nascosto, sotto il kit non c''e'' niente');

SELECT ok(
    (SELECT array_agg(uom_id ORDER BY riga_nr) = ARRAY[(SELECT u1 FROM tmp_kqp_u), (SELECT u2 FROM tmp_kqp_u), (SELECT u3 FROM tmp_kqp_u)]
            AND array_agg(qta ORDER BY riga_nr) = ARRAY[2, 6, 8]::numeric[]
            AND bool_and(imponibile IS NULL)
       FROM tmp_kqp_v WHERE tipo_riga = 'KIT_COMPONENTE' AND kit_key = 'KD')
    AND (SELECT qta = 2 AND imponibile = 500
           FROM tmp_kqp_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KD'),
    '3) KD: il kit dice 2 e porta 500; sotto, ogni componente con la sua unita'' e quantita''');

SELECT ok(
    (SELECT qta = 2 AND uom_id = (SELECT u_kit FROM tmp_kqp_u)
            AND imponibile IS NULL AND prezzo_unitario IS NULL
       FROM tmp_kqp_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KV'),
    '4) KV: kit senza resto, ma la sua quantita'' e la sua unita'' restano (2)');

SELECT ok(
    (SELECT array_agg(imponibile ORDER BY riga_nr) = ARRAY[200, 60, 240]::numeric[]
            AND array_agg(uom_id ORDER BY riga_nr) = ARRAY[(SELECT u1 FROM tmp_kqp_u), (SELECT u2 FROM tmp_kqp_u), (SELECT u3 FROM tmp_kqp_u)]
       FROM tmp_kqp_v WHERE tipo_riga = 'KIT_COMPONENTE' AND kit_key = 'KV'),
    '5) KV: i valorizzati coi loro importi e le loro unita''');

SELECT ok(
    (SELECT bool_and(NOT ha_periodo) FROM tmp_kqp_v WHERE kit_key IN ('KN', 'KD', 'KV')),
    '6) righe puntuali (dal = al): nessun periodo da stampare');

-- ============================================================
-- 7..9 — lo stesso kit su due periodi
-- ============================================================
SELECT ok(
    (SELECT count(*) = 2 AND bool_and(qta = 1 AND prezzo_unitario = 250 AND imponibile = 250)
       FROM tmp_kqp_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KP'),
    '7) KP: una riga del kit per periodo, 1 kit a 250 ciascuna (prima: 1 kit a 500)');

SELECT ok(
    (SELECT bool_and(ha_periodo)
            AND array_agg(competenza_dal ORDER BY competenza_dal) = ARRAY[DATE '2026-01-01', DATE '2026-02-01']
       FROM tmp_kqp_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KP'),
    '8) KP: ha_periodo vero, coi due inizi di gennaio e febbraio');

SELECT is(
    (SELECT count(*)::integer FROM tmp_kqp_v c
      WHERE c.tipo_riga = 'KIT_COMPONENTE' AND c.kit_key = 'KP'
        AND NOT EXISTS (SELECT 1 FROM tmp_kqp_v p
                         WHERE p.tipo_riga = 'KIT_PADRE' AND p.kit_key = 'KP'
                           AND p.riga_nr = c.kit_riga_nr
                           AND p.competenza_dal = c.competenza_dal)),
    0,
    '9) KP: ogni componente sta sotto il kit del suo periodo');

-- ============================================================
-- 10..12 — nota parziale, componente spezzato, totale
-- ============================================================
SELECT ok(
    (SELECT qta IS NULL AND prezzo_unitario IS NULL AND imponibile = 230
       FROM tmp_kqp_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KX'),
    '10) KX: componenti discordanti -> il kit non ha quantita'' ne'' prezzo, ma porta 230 (non si rifiuta)');

SELECT is(
    (SELECT qta FROM tmp_kqp_v WHERE tipo_riga = 'KIT_PADRE' AND kit_key = 'KS'),
    2::numeric,
    '11) KS: le righe dello stesso componente si sommano -> 2 kit');

SELECT is(
    (SELECT sum(imponibile) FROM tmp_kqp_v WHERE livello = 0 OR esposizione = 'VALORIZZATO'),
    (SELECT sum(imponibile_riga) FROM vendite.fatture_righe
      WHERE fattura_id = (SELECT fattura_id FROM tmp_kqp)),
    '12) totale della vista (kit + valorizzati) = totale delle righe');

-- ============================================================
-- 13..14 — la lista
-- ============================================================
SELECT ok(
    (SELECT count(*) = 2 AND count(DISTINCT riga_key) = 2 AND bool_and(componenti_numero = 3)
       FROM vendite.vw_fattura_righe_lista
      WHERE fattura_id = (SELECT fattura_id FROM tmp_kqp)
        AND tipo_riga = 'KIT_PADRE' AND descrizione = 'Kit KP'),
    '13) lista: KP sono due padri, con chiavi diverse e tre componenti ciascuno');

SELECT ok(
    (SELECT bool_and(ha_periodo) AND bool_and(competenza_al > competenza_dal)
       FROM vendite.vw_fattura_righe_lista
      WHERE fattura_id = (SELECT fattura_id FROM tmp_kqp)
        AND tipo_riga = 'KIT_PADRE' AND descrizione = 'Kit KP'),
    '14) lista: competenza_dal, competenza_al e ha_periodo arrivano in coda');

-- ============================================================
-- 15..21 — i vincoli
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id)
      SELECT (SELECT fattura_id FROM tmp_kqp), 91, 'Senza periodo', 1, 1, (SELECT iva_id FROM tmp_kqp_ref)$$,
    '23502', NULL,
    '15) una riga senza periodo e'' respinta: chi scrive la riga dice il suo periodo');

SELECT throws_ok(
    $$INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
             competenza_dal, competenza_al)
      SELECT (SELECT fattura_id FROM tmp_kqp), 92, 'Periodo rovesciato', 1, 1, (SELECT iva_id FROM tmp_kqp_ref),
             DATE '2026-02-01', DATE '2026-01-01'$$,
    '23514', NULL,
    '16) un periodo che finisce prima di cominciare e'' respinto');

SELECT throws_ok(
    $$SELECT pg_temp.fx_kqp(93, 'KZ', 'NASCOSTO', (SELECT c1 FROM tmp_kqp_ref), (SELECT u1 FROM tmp_kqp_u), 1, 1, NULL)$$,
    '23514', NULL,
    '17) una riga di kit senza kit_qta e'' respinta (chk_fatture_righe_kit_coerente)');

SELECT throws_ok(
    $$INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
             competenza_dal, competenza_al, kit_uom_id)
      SELECT (SELECT fattura_id FROM tmp_kqp), 94, 'Fuori kit', 1, 1, (SELECT iva_id FROM tmp_kqp_ref),
             script.fn_data_operativa(), script.fn_data_operativa(), (SELECT u_kit FROM tmp_kqp_u)$$,
    '23514', NULL,
    '18) kit_uom_id su una riga che non e'' di kit e'' respinta');

-- pg_attribute e non information_schema: quella vede solo cio' su cui il ruolo
-- corrente ha privilegi.
SELECT ok(
    (SELECT count(*) = 2 FROM pg_attribute
      WHERE attrelid = 'vendite.fatture_righe'::regclass
        AND attname IN ('competenza_dal', 'competenza_al')
        AND attnotnull AND NOT atthasdef AND NOT attisdropped),
    '19) competenza_dal e competenza_al: NOT NULL e senza default');

SELECT is(
    (SELECT count(*)::integer FROM pg_attribute a
       JOIN pg_class c ON c.oid = a.attrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'vendite' AND a.attname = 'uom_operativa_id' AND a.attnotnull
        AND c.relname IN ('preventivi_righe_componenti', 'ordini_righe_componenti',
                          'contratti_righe_componenti', 'ddt_righe_componenti',
                          'offerte_commerciali_eccezioni_componenti')),
    5,
    '20) uom_operativa_id NOT NULL sui cinque *_componenti dei documenti');

-- Il trigger di immutabilita' e' stato ricreato (20261002-60) senza le due
-- colonne ritirate: deve ascoltare ancora TUTTI i campi di struttura. La lista
-- UPDATE OF si legge da pg_trigger.tgattr, non dalla doc auto-gen (che stampa
-- l'evento senza colonne: e' cio' che ha nascosto il difetto di 20261001-42).
SELECT is(
    (SELECT array_agg(a.attname::text ORDER BY a.attname)
       FROM pg_trigger t
       JOIN pg_attribute a ON a.attrelid = t.tgrelid AND a.attnum = ANY (t.tgattr)
      WHERE t.tgrelid = 'catalogo.articoli_componenti'::regclass
        AND t.tgname = 'trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt'),
    ARRAY['coeff_qta', 'componente_id', 'esposizione_in_fattura', 'obbligatorio',
          'valido_al', 'valido_dal'],
    '21) il guard di immutabilita'' della distinta ascolta ancora i sei campi di struttura');

-- ============================================================
-- 22..24 — la distinta senza i due flag
-- ============================================================
SELECT hasnt_column('catalogo', 'articoli_componenti', 'partecipa_qta',
    '22) la distinta non ha piu'' partecipa_qta (nessuna logica la leggeva)');

SELECT hasnt_column('catalogo', 'articoli_componenti', 'determina_qta_padre',
    '23) la distinta non ha piu'' determina_qta_padre (nessuna logica la leggeva)');

SELECT is(
    (SELECT count(*)::integer FROM config.parameters
      WHERE code IN ('CATALOGO_BOM_DEFAULT_PARTECIPA_QTA', 'CATALOGO_BOM_DEFAULT_DETERMINA_QTA_PADRE')),
    0,
    '24) i parametri di default dei due flag sono ritirati');

-- Il frammento e' il NOME del vincolo: 23514 da solo passerebbe anche per il
-- CHECK di coerenza, cioe' per il motivo sbagliato.
SELECT throws_like(
    $$SELECT pg_temp.fx_kqp(95, 'KA', 'DESCRITTIVO', NULL, (SELECT u1 FROM tmp_kqp_u), 1, 1, 1)$$,
    '%chk_fatture_righe_kit_articolo%',
    '25) una riga di kit senza articolo e'' respinta: un componente e'' un articolo');

-- ============================================================
-- 26 — il periodo da mostrare nella lista
-- ============================================================
SELECT ok(
    (SELECT bool_and(periodo_dal = competenza_dal AND periodo_al = competenza_al)
       FROM vendite.vw_fattura_righe_lista
      WHERE fattura_id = (SELECT fattura_id FROM tmp_kqp)
        AND tipo_riga = 'KIT_PADRE' AND descrizione = 'Kit KP')
    AND (SELECT count(*) > 0
                AND bool_and(periodo_dal IS NULL AND periodo_al IS NULL
                             AND competenza_dal IS NOT NULL)
           FROM vendite.vw_fattura_righe_lista
          WHERE fattura_id = (SELECT fattura_id FROM tmp_kqp)
            AND NOT ha_periodo),
    '26) lista: periodo_dal/_al pieni sul kit di gennaio e febbraio, NULL sulle righe puntuali');

SELECT * FROM finish();
ROLLBACK;
