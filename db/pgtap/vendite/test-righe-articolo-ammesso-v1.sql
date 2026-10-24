-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   la natura merce ha destinazione ORDINE_VENDITA, il codice della sorgente (era ORDINE).
-- pgTAP test per Zero ERP
--
-- Quali articoli ammette una riga di preventivo, ordine e bolla: una check
-- sola per tipo di riga, un guard per tabella, la riconsegna esente, e il
-- «solo componente» che non si accende su un articolo usato (A-10).
-- Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-2, A-3, A-6, D-1,
-- D-2, D-3; §9.3.1)
-- ChangeSet: 20261013-40 -> -43; lato articolo 20261013-47 -> -51 (A-10,
--   che ha sostituito il guard «solo componente in bozza» di -44/-46)
--
-- Elenco test (plan 18):
--  La check (script.fn_check_articolo_riga)
--   1) articolo merce vendibile, su ordine: nessun motivo
--   2) solo componente e servizio insieme, su ordine: i due motivi
--      nell'ordine dichiarato (solo componente prima, natura dopo)
--   3) servizio su bolla: E_RIGA_NATURA_NON_AMMESSA
--   4) servizio su ordine, ma la riga porta la natura merce: nessun motivo
--      (si giudica la natura della riga, congelata)
--   5) ricorrente su preventivo: E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA
--   6) servizio una tantum su preventivo: nessun motivo
--   7) documento non gestito: E_DOC_TIPO_NON_GESTITO
--  Il guard di tabella (script.trgfn_righe_guard_articolo_ammesso)
--   8) preventivo: solo componente rifiutato
--   9) preventivo: ricorrente rifiutato (la regola del guard ritirato, stessa frase)
--  10) ordine: servizio rifiutato
--  11) ordine: merce ammessa
--  12) ordine: cambio di articolo verso un servizio rifiutato
--  13) bolla: servizio rifiutato
--  La riconsegna (A-6)
--  14) l'articolo spedito diventa solo componente dopo la consegna:
--      la riconsegna passa lo stesso
--  15) ma una riga scritta a mano con lo stesso articolo, nella stessa bolla,
--      e' rifiutata (la porta vale solo per il verbo)
--  16) e la porta accesa a mano su un reso che non contiene l'articolo non
--      lo esenta
--  Il lato articolo (A-3, A-10)
--  17) un articolo usato (qui: in una riga di un ordine in bozza) non diventa
--      solo componente: E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE
--  18) il form spegne is_solo_componente su quell'articolo
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo ORDER BY nv.id LIMIT 1)    AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1)  AS servizio,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'CONTRATTO' AND nv.attivo ORDER BY nv.id LIMIT 1) AS ricorrente;

-- M merce, S servizio una tantum, R ricorrente, C solo componente (e
-- servizio), K merce che diventera' solo componente dopo la consegna.
-- Natura e «solo componente» si scelgono alla nascita.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-AAM-M', false,
           p_natura_vendita_id => n.merce)                    AS m,
       dbops.fn_pgtap_crea_articolo('PGT-AAM-S', false,
           p_natura_vendita_id => n.servizio)                 AS s,
       dbops.fn_pgtap_crea_articolo('PGT-AAM-R', false,
           p_natura_vendita_id => n.ricorrente)               AS r,
       dbops.fn_pgtap_crea_articolo('PGT-AAM-C', false,
           p_is_solo_componente => true,
           p_natura_vendita_id  => n.servizio)                AS c,
       dbops.fn_pgtap_crea_articolo('PGT-AAM-K', false,
           p_natura_vendita_id => n.merce)                    AS k
  FROM _nat n;

CREATE TEMP TABLE _iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS id;

CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP articoli ammessi');

-- ============================================================
-- La check (1-7)
-- ============================================================
SELECT is(script.fn_check_articolo_riga('ORDINE_VENDITA', NULL, (SELECT m FROM _art)),
          '[]'::jsonb,
    '1) check: merce vendibile su ordine, nessun motivo');

SELECT is(
    (SELECT jsonb_agg(e ->> 'codice' ORDER BY o)
       FROM jsonb_array_elements(script.fn_check_articolo_riga('ORDINE_VENDITA', NULL, (SELECT c FROM _art)))
            WITH ORDINALITY AS x(e, o)),
    '["E_ARTICOLO_SOLO_COMPONENTE", "E_RIGA_NATURA_NON_AMMESSA"]'::jsonb,
    '2) check: solo componente e servizio, i due motivi nell''ordine dichiarato');

SELECT is(script.fn_check_articolo_riga('DDT_VENDITA', NULL, (SELECT s FROM _art)) -> 0 ->> 'codice',
          'E_RIGA_NATURA_NON_AMMESSA',
    '3) check: servizio su bolla, E_RIGA_NATURA_NON_AMMESSA');

SELECT is(script.fn_check_articolo_riga('ORDINE_VENDITA', NULL, (SELECT s FROM _art), (SELECT merce FROM _nat)),
          '[]'::jsonb,
    '4) check: si giudica la natura della riga, se la riga la porta');

SELECT is(script.fn_check_articolo_riga('PREVENTIVO', NULL, (SELECT r FROM _art)) -> 0 ->> 'codice',
          'E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA',
    '5) check: ricorrente su preventivo, va in offerta');

SELECT is(script.fn_check_articolo_riga('PREVENTIVO', NULL, (SELECT s FROM _art)),
          '[]'::jsonb,
    '6) check: servizio una tantum su preventivo, nessun motivo');

SELECT throws_like(
    $$ SELECT script.fn_check_articolo_riga('FATTURA', NULL, NULL) $$,
    '%FATTURA sconosciuto%',
    '7) check: documento non gestito, E_DOC_TIPO_NON_GESTITO');

-- ============================================================
-- Il guard di tabella (8-13)
-- ============================================================
CREATE TEMP TABLE _prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP articoli ammessi');

SELECT throws_like(
    format($$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, %L, %s, 10, 1)$$,
           (SELECT preventivo_id FROM _prev), (SELECT c FROM _art), (SELECT id FROM _iva)),
    '%solo come componente%',
    '8) preventivo: solo componente rifiutato');

SELECT throws_like(
    format($$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, %L, %s, 10, 1)$$,
           (SELECT preventivo_id FROM _prev), (SELECT r FROM _art), (SELECT id FROM _iva)),
    '%servizio ricorrente%',
    '9) preventivo: ricorrente rifiutato, con la frase di prima');

CREATE TEMP TABLE _ord AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('pgTAP articoli ammessi');

SELECT throws_like(
    format($$INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, 1, %L, 'servizio', %s, 10, 1)$$,
           (SELECT ordine_id FROM _ord), (SELECT s FROM _art), (SELECT id FROM _iva)),
    '%vanno solo merci%',
    '10) ordine: servizio rifiutato (E_RIGA_NATURA_NON_AMMESSA)');

CREATE TEMP TABLE _or AS
WITH ins AS (
    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id, prezzo_unitario, qta_operativa)
    SELECT (SELECT ordine_id FROM _ord), 2, (SELECT k FROM _art), 'merce', (SELECT id FROM _iva), 10, 1
    RETURNING id
)
SELECT * FROM ins;

SELECT ok((SELECT count(*) = 1 FROM _or), '11) ordine: merce ammessa');

SELECT throws_like(
    format($$UPDATE vendite.ordini_righe SET articolo_id = %L WHERE id = %s$$,
           (SELECT s FROM _art), (SELECT id FROM _or)),
    '%vanno solo merci%',
    '12) ordine: cambio di articolo verso un servizio rifiutato');

CREATE TEMP TABLE _ddt AS
SELECT dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m),
                               (SELECT cliente_soggetto_ruolo_id FROM _m), 'VENDITA') AS id;

SELECT throws_like(
    format($$INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa)
             VALUES (%s, 1, %L, 'servizio', 1)$$,
           (SELECT id FROM _ddt), (SELECT s FROM _art)),
    '%vanno solo merci%',
    '13) bolla: servizio rifiutato');

-- ============================================================
-- La riconsegna (14-16)
-- ============================================================
-- La bolla porta K (merce, vendibile) e viene consegnata.
INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa,
                               prezzo_unitario, iva_id)
SELECT (SELECT id FROM _ddt), 2, (SELECT k FROM _art), 'merce da rendere', 3, 10, (SELECT id FROM _iva);

-- Lo stato della bolla e la conferma del reso passano dai loro verbi, che
-- chiedono le azioni emetti_ddt e conferma_reso all'operatore del test.
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;
SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT id FROM _ddt), 'EMESSO');
SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT id FROM _ddt), 'SPEDITO');
SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT id FROM _ddt), 'CONSEGNATO');

-- K esce dall'ordine in bozza, poi diventa solo componente.
-- ⛔ rev 2026-10-13 (A-10): K e' usato (ordine, bolla), e un articolo usato non
--   cambia i flag strutturali: il caso resta vero dalla porta amministratore,
--   e il builder passa dal verbo.
UPDATE vendite.ordini_righe SET attivo = false WHERE id = (SELECT id FROM _or);
SELECT dbops.fn_pgtap_articolo_correggi_struttura(
    (SELECT k FROM _art), jsonb_build_object('is_solo_componente', true));

CREATE TEMP TABLE _reso AS
WITH ins AS (
    INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
    SELECT (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno = 'DRAFT'),
           (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'DDT_VENDITA'),
           (SELECT d.uid FROM vendite.ddt d WHERE d.id = (SELECT id FROM _ddt)),
           false, jsonb_build_object('test_scope', 'pgtap_articoli_ammessi')
    RETURNING id
)
SELECT * FROM ins;

INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id, articolo_id,
                                descrizione, qta_operativa, uom_operativa_id, factor_to_base,
                                tipo_reso_id, storicizza)
SELECT (SELECT id FROM _reso), 1, dr.id, NULL, dr.articolo_id, dr.descrizione, 1,
       dr.uom_operativa_id, dr.factor_to_base,
       (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno = 'RESO_PER_RICONSEGNA'), false
  FROM vendite.ddt_righe dr
 WHERE dr.ddt_id = (SELECT id FROM _ddt) AND dr.articolo_id = (SELECT k FROM _art);

SELECT vendite.fn_conferma_reso((SELECT id FROM _reso));

CREATE TEMP TABLE _ric AS
SELECT vendite.fn_genera_ddt_riconsegna((SELECT id FROM _reso)) AS ddt_id;

SELECT ok(
    EXISTS (SELECT 1 FROM vendite.ddt_righe dr
             WHERE dr.ddt_id = (SELECT ddt_id FROM _ric) AND dr.articolo_id = (SELECT k FROM _art)),
    '14) riconsegna: l''articolo diventato solo componente si restituisce lo stesso');

SELECT throws_like(
    format($$INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa)
             VALUES (%s, 99, %L, 'a mano', 1)$$,
           (SELECT ddt_id FROM _ric), (SELECT k FROM _art)),
    '%solo come componente%',
    '15) riconsegna: una riga scritta a mano con lo stesso articolo e'' rifiutata');

SELECT throws_like(
    format($f$DO $p$ BEGIN
               PERFORM set_config('zeroerp.ddt_riconsegna', %s::text, true);
               INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa)
               VALUES (%s, 98, %L, 'porta su un altro reso', 1);
             END $p$$f$,
           (SELECT id FROM _reso), (SELECT ddt_id FROM _ric), (SELECT c FROM _art)),
    '%solo come componente%',
    '16) la porta accesa su un reso che non contiene l''articolo non lo esenta');

-- ============================================================
-- Il lato articolo (17-18)
-- ============================================================
-- M sta in una riga dell'ordine in bozza.
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT ordine_id FROM _ord), 3, (SELECT m FROM _art), 'merce in bozza', (SELECT id FROM _iva), 10, 1;

SELECT throws_like(
    format($$UPDATE catalogo.articoli SET is_solo_componente = true WHERE id = %L$$, (SELECT m FROM _art)),
    '%già usato%',
    '17) un articolo usato (in una riga di un ordine in bozza) non diventa solo componente');

SELECT ok(
    'is_solo_componente' = ANY (dbops.fn_non_editable_fields('catalogo', 'articoli', (SELECT m FROM _art)::text)),
    '18) il form spegne is_solo_componente su quell''articolo');

SELECT * FROM finish();
ROLLBACK;
