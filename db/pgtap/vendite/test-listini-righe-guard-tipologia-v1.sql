-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T4: guard coerenza articolo/listino tipologia su
-- vendite.listini_righe (pricing v5).
--
-- Elenco test (1..4):
--   1) Backfill: articoli con voce_utility=FALSE mappati a PRODOTTI
--   2) Articolo senza listino_tipologia_id in listino tipizzato ->
--      E_ARTICOLO_TIPOLOGIA_MANCANTE
--   3) Articolo con tipologia diversa da quella del listino ->
--      E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE
--   4) Articolo con tipologia coerente: insert ammesso
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- Precondizioni: serve un listino tipizzato con versione attiva + 2 articoli
-- (uno con tipologia allineata, uno senza/diversa). Usiamo i seed esistenti
-- per evitare dipendenze da dati specifici del DB di sviluppo.

CREATE TEMP TABLE tmp_tipologia_prodotti AS
SELECT id AS tipologia_id FROM config.listini_tipologie WHERE codice = 'PRODOTTI';

CREATE TEMP TABLE tmp_tipologia_servizi AS
SELECT id AS tipologia_id FROM config.listini_tipologie WHERE codice = 'SERVIZI';

-- 1) Backfill verificato: percentuale articoli non-utility con listino_tipologia_id
-- deve essere uguale al totale (tutti backfillati a PRODOTTI).
SELECT is(
    (SELECT COUNT(*)::int FROM catalogo.articoli
      WHERE voce_utility = FALSE AND listino_tipologia_id IS NULL),
    0,
    'Backfill: tutti gli articoli non-utility hanno listino_tipologia_id valorizzato'
);

-- Seleziona un listino di tipologia PRODOTTI con versione attiva (qualsiasi).
-- Se non esiste, i test 2/3/4 finiscono in skip_unless equivalente via NOT FOUND.
CREATE TEMP TABLE tmp_ctx_listino_prod AS
SELECT l.id AS listino_id, lv.id AS listino_versione_id
  FROM vendite.listini l
  JOIN vendite.listini_versioni lv ON lv.listino_id = l.id
 WHERE l.tipologia_id = (SELECT tipologia_id FROM tmp_tipologia_prodotti)
   AND lv.attivo IS TRUE
   AND lv.validita @> CURRENT_DATE
 ORDER BY l.id, lv.id
 LIMIT 1;

-- Articolo con tipologia PRODOTTI attivo
CREATE TEMP TABLE tmp_art_prod AS
SELECT id AS articolo_id, uom_id
  FROM catalogo.articoli
 WHERE listino_tipologia_id = (SELECT tipologia_id FROM tmp_tipologia_prodotti)
   AND attivo IS TRUE
 ORDER BY id
 LIMIT 1;

-- Articolo "di comodo" per i test negativi: creiamo un articolo senza tipologia
-- e uno con tipologia diversa dentro la transazione, cosi' il ROLLBACK pulisce.
INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id, voce_utility, attivo)
SELECT 'PGTAP_ART_NO_TIP', 'Articolo senza tipologia pgtap',
       (SELECT uom_id FROM tmp_art_prod), NULL, FALSE, TRUE;

INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id, voce_utility, attivo)
SELECT 'PGTAP_ART_SERV', 'Articolo SERVIZI pgtap',
       (SELECT uom_id FROM tmp_art_prod),
       (SELECT tipologia_id FROM tmp_tipologia_servizi), FALSE, TRUE;

-- 2) articolo senza listino_tipologia_id -> E_ARTICOLO_TIPOLOGIA_MANCANTE
-- fn_log_and_raise_error solleva con SQLSTATE P0001.
SELECT throws_ok(
    $$INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
      SELECT lv.listino_versione_id,
             (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_ART_NO_TIP'),
             (SELECT uom_id FROM tmp_art_prod),
             100
        FROM tmp_ctx_listino_prod lv$$,
    'P0001',
    NULL,
    'Articolo senza listino_tipologia_id -> guard lo blocca (E_ARTICOLO_TIPOLOGIA_MANCANTE)'
);

-- 3) articolo con tipologia diversa (SERVIZI) vs listino PRODOTTI ->
-- E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE
SELECT throws_ok(
    $$INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
      SELECT lv.listino_versione_id,
             (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_ART_SERV'),
             (SELECT uom_id FROM tmp_art_prod),
             150
        FROM tmp_ctx_listino_prod lv$$,
    'P0001',
    NULL,
    'Tipologia articolo diversa dal listino -> guard lo blocca (E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE)'
);

-- 4) articolo con tipologia coerente: insert ammesso
SELECT lives_ok(
    $$INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
      SELECT lv.listino_versione_id, ap.articolo_id, ap.uom_id, 200
        FROM tmp_ctx_listino_prod lv, tmp_art_prod ap$$,
    'Articolo con tipologia coerente con il listino: insert ammesso'
);

SELECT * FROM finish();
ROLLBACK;
