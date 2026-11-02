-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

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

-- rev 2026-10-27 (lotto 4 di D7): listino PRODOTTI e articolo PRODOTTI si
-- COSTRUISCONO (prima si pescavano con ORDER BY id LIMIT 1: da zero non
-- c'erano, e le INSERT su tmp vuote passavano o fallivano a vuoto).
-- Listino: dbops.fn_pgtap_crea_listino sull'utility BASE del seed, la cui
-- prima tipologia ammessa e' PRODOTTI (config.listini_tipologie_utilities).
-- Articolo: dbops.fn_pgtap_crea_articolo con tipologia PRODOTTI e la UoM
-- del builder (prima attiva del seed).
CREATE TEMP TABLE tmp_ctx_listino_prod AS
SELECT l.listino_id, l.listino_versione_id
  FROM dbops.fn_pgtap_crea_listino(
           (SELECT u.id FROM config.utilities u WHERE u.codice = 'BASE'),
           'guard tipologia') l
 WHERE l.tipologia_id = (SELECT tipologia_id FROM tmp_tipologia_prodotti);

-- Articolo con tipologia PRODOTTI
CREATE TEMP TABLE tmp_art_prod AS
SELECT b.articolo_id, NULL::bigint AS uom_id
  FROM dbops.fn_pgtap_crea_articolo(
           'PGTAP_ART_PROD', false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_tipologia_prodotti)) AS b(articolo_id);
-- La UoM in un'istruzione a parte: la riga scritta dal builder non e'
-- visibile a una JOIN nella stessa istruzione che lo chiama.
UPDATE tmp_art_prod t
   SET uom_id = a.uom_id
  FROM catalogo.articoli a
 WHERE a.id = t.articolo_id;

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
-- rev 2026-10-27 (lotto 4 di D7): discriminante sulla frase del registro
-- (prima throws_ok P0001 senza messaggio: qualunque P0001 passava).
SELECT throws_like(
    $$INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
      SELECT lv.listino_versione_id,
             (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_ART_NO_TIP'),
             (SELECT uom_id FROM tmp_art_prod),
             100
        FROM tmp_ctx_listino_prod lv$$,
    '%privo di listino_tipologia_id: non ammesso in listino tipizzato%',
    'Articolo senza listino_tipologia_id -> guard lo blocca (E_ARTICOLO_TIPOLOGIA_MANCANTE)'
);

-- 2) articolo con tipologia diversa (SERVIZI) vs listino PRODOTTI ->
-- E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE
-- rev 2026-10-27 (lotto 4 di D7): discriminante sulla frase del registro.
SELECT throws_like(
    $$INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
      SELECT lv.listino_versione_id,
             (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_ART_SERV'),
             (SELECT uom_id FROM tmp_art_prod),
             150
        FROM tmp_ctx_listino_prod lv$$,
    '%incompatibile con tipologia listino%',
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
