-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T4: guard coerenza articolo/listino tipologia su
-- vendite.listini_righe (pricing v5).
--
-- Elenco test (1..3):
--   1) Articolo senza listino_tipologia_id in listino tipizzato ->
--      E_ARTICOLO_TIPOLOGIA_MANCANTE
--   2) Articolo con tipologia diversa da quella del listino ->
--      E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE
--   3) Articolo con tipologia coerente: insert ammesso
--
-- Nota: non esiste un test d'invariante "tutti gli articoli hanno
-- listino_tipologia_id valorizzato". Il backfill assegna PRODOTTI di
-- default ma gli articoli inseriti manualmente senza tipologia sono
-- ammissibili a livello DB (la colonna e' nullable); e' il guard su
-- listini_righe a bloccare l'insert in un listino tipizzato.
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

-- Precondizioni: serve un listino tipizzato con versione attiva + 2 articoli
-- (uno con tipologia allineata, uno senza/diversa). Usiamo i seed esistenti
-- per evitare dipendenze da dati specifici del DB di sviluppo.

CREATE TEMP TABLE tmp_tipologia_prodotti AS
SELECT id AS tipologia_id FROM config.listini_tipologie WHERE codice = 'PRODOTTI';

CREATE TEMP TABLE tmp_tipologia_servizi AS
SELECT id AS tipologia_id FROM config.listini_tipologie WHERE codice = 'SERVIZI';

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
INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id, attivo)
SELECT 'PGTAP_ART_NO_TIP', 'Articolo senza tipologia pgtap',
       (SELECT uom_id FROM tmp_art_prod), NULL, TRUE;

INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id, attivo)
SELECT 'PGTAP_ART_SERV', 'Articolo SERVIZI pgtap',
       (SELECT uom_id FROM tmp_art_prod),
       (SELECT tipologia_id FROM tmp_tipologia_servizi), TRUE;

-- 1) articolo senza listino_tipologia_id -> E_ARTICOLO_TIPOLOGIA_MANCANTE
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

-- 2) articolo con tipologia diversa (SERVIZI) vs listino PRODOTTI ->
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

-- 3) articolo con tipologia coerente: insert ammesso
SELECT lives_ok(
    $$INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
      SELECT lv.listino_versione_id, ap.articolo_id, ap.uom_id, 200
        FROM tmp_ctx_listino_prod lv, tmp_art_prod ap$$,
    'Articolo con tipologia coerente con il listino: insert ammesso'
);

SELECT * FROM finish();
ROLLBACK;
