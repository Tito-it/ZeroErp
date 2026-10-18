-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La correzione della struttura di un articolo usato (la porta amministratore)
-- non rende non valide le righe VIVE: attive, in documenti non chiusi. Le
-- rigiudica con la stessa check dei guard di riga, e se una non e' piu'
-- ammessa rifiuta tutta la correzione.
-- Brief: brief-db-articoli-ammessi-per-documento (§9.8.4, A-11 di Tid)
-- ChangeSet: 20261018-72; 20261018-73, -74 (solo le righe che la correzione
--   RENDE non ammesse: una riga gia' non ammessa prima non blocca)
--
-- Elenco test (plan 10):
--  Il rifiuto
--   1) A in un preventivo in bozza: «solo componente» -> E_ARTICOLO_STRUTTURA_RIGHE_APERTE
--   2) ... e la correzione si annulla: A non e' diventato solo componente
--   3) B in un ordine e in un preventivo aperti: il messaggio conta righe e documenti
--  Cio' che non blocca
--   4) la natura di A si corregge: la riga ha la sua, congelata
--   5) C sta solo in un preventivo ANNULLATO (fase CHIUSO): la correzione passa
--   6) D sta solo in una riga spenta: la correzione passa
--   7) senza righe vive nemmeno la correzione di piu' colonne trova motivi:
--      e' scritta intera
--  Il presidio
--   8) l'elenco delle righe vive (catalogo.fn_articolo_righe_vive_non_ammesse)
--      legge tutte le tabelle dove e' montato il guard di riga
--      (script.trgfn_righe_guard_articolo_ammesso): un montaggio nuovo lo fa rosso
--   9) e il guard di riga e' montato su sette tabelle (se cambia, cambia anche l'8)
--  Prima e dopo
--  10) E ha una riga viva GIA' non ammessa (riaccesa dopo una correzione: il
--      guard di riga e' UPDATE OF articolo_id): un'altra correzione passa
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE' AND nv.attivo ORDER BY nv.id LIMIT 1)   AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1) AS servizio;

CREATE TEMP TABLE _iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS id;

CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-ACR-A', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS a,
       dbops.fn_pgtap_crea_articolo('PGT-ACR-B', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS b,
       dbops.fn_pgtap_crea_articolo('PGT-ACR-C', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS c,
       dbops.fn_pgtap_crea_articolo('PGT-ACR-D', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS d;

-- P1: aperto, con A e B. P2: con C, poi annullato. P3: aperto, con D spenta. O: ordine aperto con B.
CREATE TEMP TABLE _p1 AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP correzione righe aperte 1');
CREATE TEMP TABLE _p2 AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP correzione righe aperte 2');
CREATE TEMP TABLE _p3 AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP correzione righe aperte 3');
CREATE TEMP TABLE _ord AS SELECT * FROM dbops.fn_pgtap_crea_ordine('pgTAP correzione righe aperte');

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT preventivo_id FROM _p1), x.art, (SELECT id FROM _iva), 10, 1
  FROM (VALUES ((SELECT a FROM _art)), ((SELECT b FROM _art))) x(art);

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT preventivo_id FROM _p2), (SELECT c FROM _art), (SELECT id FROM _iva), 10, 1;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT preventivo_id FROM _p3), (SELECT d FROM _art), (SELECT id FROM _iva), 10, 1;
UPDATE vendite.preventivi_righe SET attivo = false
 WHERE preventivo_id = (SELECT preventivo_id FROM _p3);

INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT ordine_id FROM _ord), 1, (SELECT b FROM _art), 'pgTAP B', (SELECT id FROM _iva), 10, 1;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT preventivo_id FROM _p2), 'ANNULLATO');

-- Il SUPER_ADMIN che corregge; il contesto di prima si rimette per scrivere righe.
CREATE TEMP TABLE _ctx AS SELECT current_setting('app.current_user_id', true) AS prima;
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-righe-aperte', true);
DO $sa$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $sa$;

-- ============================================================
-- Il rifiuto (1-3)
-- ============================================================
SELECT throws_like(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, '{"is_solo_componente": true}'::jsonb)$$,
           (SELECT a FROM _art)),
    '%PGT-ACR-A%non ancora chiusi (righe: 1, documenti: 1)%',
    '1) A in un preventivo in bozza: la correzione a «solo componente» e'' rifiutata');

SELECT is(
    (SELECT is_solo_componente FROM catalogo.articoli WHERE id = (SELECT a FROM _art)),
    false,
    '2) la correzione rifiutata si annulla: A non e'' solo componente');

SELECT throws_like(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, '{"is_solo_componente": true}'::jsonb)$$,
           (SELECT b FROM _art)),
    '%(righe: 2, documenti: 2)%',
    '3) B in un ordine e in un preventivo aperti: contate due righe in due documenti');

-- ============================================================
-- Cio' che non blocca (4-7)
-- ============================================================
SELECT lives_ok(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, %L::jsonb)$$,
           (SELECT a FROM _art), jsonb_build_object('natura_vendita_id', (SELECT servizio FROM _nat))),
    '4) la natura di A si corregge: la riga del preventivo ha la sua, congelata');

SELECT catalogo.fn_articolo_correggi_struttura((SELECT c FROM _art), '{"is_solo_componente": true}'::jsonb);
SELECT is(
    (SELECT is_solo_componente FROM catalogo.articoli WHERE id = (SELECT c FROM _art)),
    true,
    '5) C sta solo in un preventivo annullato: la correzione passa');

SELECT catalogo.fn_articolo_correggi_struttura((SELECT d FROM _art), '{"is_solo_componente": true}'::jsonb);
SELECT is(
    (SELECT is_solo_componente FROM catalogo.articoli WHERE id = (SELECT d FROM _art)),
    true,
    '6) D sta solo in una riga spenta: la correzione passa');

SELECT catalogo.fn_articolo_correggi_struttura(
    (SELECT d FROM _art),
    jsonb_build_object('is_solo_componente', false, 'natura_vendita_id', (SELECT servizio FROM _nat)));
SELECT is(
    (SELECT (is_solo_componente, natura_vendita_id)::text FROM catalogo.articoli WHERE id = (SELECT d FROM _art)),
    (false, (SELECT servizio FROM _nat))::text,
    '7) senza righe vive la correzione di due colonne e'' scritta intera');

-- ============================================================
-- Il presidio (8-9)
-- ============================================================
CREATE TEMP TABLE _montaggi AS
SELECT DISTINCT t.tgrelid::regclass AS tabella
  FROM pg_trigger t
 WHERE t.tgfoid = 'script.trgfn_righe_guard_articolo_ammesso()'::regprocedure
   AND NOT t.tgisinternal;

SELECT is(
    (SELECT array_agg(m.tabella::text ORDER BY m.tabella::text)
       FROM _montaggi m
      WHERE position(
                (SELECT n.nspname || '.' || c.relname
                   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                  WHERE c.oid = m.tabella) || ' '
                IN (SELECT p.prosrc FROM pg_proc p
                     WHERE p.oid = 'catalogo.fn_articolo_righe_vive_non_ammesse(uuid)'::regprocedure)) = 0),
    NULL::text[],
    '8) l''elenco delle righe vive legge ogni tabella dove e'' montato il guard di riga (nessuna mancante)');

SELECT is((SELECT count(*)::integer FROM _montaggi), 7,
    '9) il guard di riga e'' montato su sette tabelle');

-- ============================================================
-- Prima e dopo (10)
-- ============================================================
-- E: la sua riga spenta non blocca la correzione a «solo componente»; poi la
-- riga si riaccende, e il guard di riga (UPDATE OF articolo_id) non la
-- rigiudica: e' viva e gia' non ammessa. Una correzione che non la cambia passa.
CREATE TEMP TABLE _e AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-ACR-E', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS e;
DO $op$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT prima FROM _ctx)::integer); END $op$;
CREATE TEMP TABLE _p4 AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP correzione righe aperte 4');
INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT preventivo_id FROM _p4), (SELECT e FROM _e), (SELECT id FROM _iva), 10, 1;
UPDATE vendite.preventivi_righe SET attivo = false WHERE preventivo_id = (SELECT preventivo_id FROM _p4);
DO $sa2$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $sa2$;
SELECT catalogo.fn_articolo_correggi_struttura((SELECT e FROM _e), '{"is_solo_componente": true}'::jsonb);
DO $op2$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT prima FROM _ctx)::integer); END $op2$;
UPDATE vendite.preventivi_righe SET attivo = true WHERE preventivo_id = (SELECT preventivo_id FROM _p4);
DO $sa3$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $sa3$;

SELECT lives_ok(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, %L::jsonb)$$,
           (SELECT e FROM _e), jsonb_build_object('natura_vendita_id', (SELECT servizio FROM _nat))),
    '10) una riga viva gia'' non ammessa prima non blocca un''altra correzione');

SELECT * FROM finish();
ROLLBACK;
