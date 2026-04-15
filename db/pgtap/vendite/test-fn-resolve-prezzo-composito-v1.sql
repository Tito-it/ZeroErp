-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T6: vendite.fn_resolve_prezzo_composito (BoM ibrido).
-- Copre i 3 casi logici della funzione:
--   CASO A:  almeno un componente esposto -> N righe
--   CASO B1: nessun esposto, riga listino per il composito -> 1 riga (prezzo negoziato)
--   CASO B2: nessun esposto, no riga listino padre -> 1 riga (Sigma componenti)
--
-- Setup: creiamo nella TX articolo padre composito, 2 componenti, listino
-- con versione attiva e 3 righe, matrice categoria -> listino senza variazione.
-- ROLLBACK pulisce tutto a fine test.
--
-- Elenco test (1..4):
--   1) Precondizione: setup completato (padre, componenti, listino, matrice)
--   2) CASO A: componente A esposto -> 2 righe, flag esposto coerente
--   3) CASO B1: nessun componente esposto, riga listino padre -> 1 riga con prezzo padre
--   4) CASO B2: nessun componente esposto + niente riga listino padre -> Sigma componenti
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- Precondizioni: BA su utility senza dimensione + emittente + tipologia PRODOTTI.
CREATE TEMP TABLE tmp_ctx AS
SELECT
    ba.id                    AS ba_id,
    ba.categoria_cliente_id  AS categoria_id,
    ba.utility_id            AS utility_id,
    (SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali
       WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS emittente_srid,
    (SELECT id FROM config.listini_tipologie WHERE codice = 'PRODOTTI') AS tipologia_prodotti,
    (SELECT id FROM catalogo.unita_misura ORDER BY id LIMIT 1)          AS uom_id
  FROM anagrafiche.billing_account ba
 WHERE ba.categoria_cliente_id IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
   )
 ORDER BY ba.id
 LIMIT 1;

-- Articoli di test (ROLLBACK pulisce).
INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id,
                              is_composito, attivo)
SELECT 'PGTAP_BOM_PADRE', 'Composito padre pgtap', t.uom_id, t.tipologia_prodotti,
       TRUE, TRUE
  FROM tmp_ctx t;

INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id, attivo)
SELECT 'PGTAP_BOM_A', 'Componente A pgtap', t.uom_id, t.tipologia_prodotti, TRUE
  FROM tmp_ctx t;

INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id, attivo)
SELECT 'PGTAP_BOM_B', 'Componente B pgtap', t.uom_id, t.tipologia_prodotti, TRUE
  FROM tmp_ctx t;

-- BoM: padre = A + B (entrambi obbligatori, esposto default FALSE).
INSERT INTO catalogo.articoli_componenti(prodotto_id, componente_id, coeff_qta,
                                         obbligatorio, valido_dal, attivo,
                                         esposto_in_fattura)
SELECT p.id, a.id, 2, TRUE, CURRENT_DATE, TRUE, FALSE
  FROM catalogo.articoli p, catalogo.articoli a
 WHERE p.codice = 'PGTAP_BOM_PADRE' AND a.codice = 'PGTAP_BOM_A';

INSERT INTO catalogo.articoli_componenti(prodotto_id, componente_id, coeff_qta,
                                         obbligatorio, valido_dal, attivo,
                                         esposto_in_fattura)
SELECT p.id, b.id, 3, TRUE, CURRENT_DATE, TRUE, FALSE
  FROM catalogo.articoli p, catalogo.articoli b
 WHERE p.codice = 'PGTAP_BOM_PADRE' AND b.codice = 'PGTAP_BOM_B';

-- Listino di test: uso un listino PRODOTTI esistente attivo (fallback se non c'e')
-- con versione attiva alla data corrente.
CREATE TEMP TABLE tmp_ctx_listino AS
SELECT l.id AS listino_id
  FROM vendite.listini l, tmp_ctx t
 WHERE l.tipologia_id = t.tipologia_prodotti
   AND l.attivo       = TRUE
 ORDER BY l.id
 LIMIT 1;

INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, valido_al, stato, attivo)
SELECT l.listino_id, 'PGTAP_BOM_VER', CURRENT_DATE, CURRENT_DATE + 365, 'ATTIVA', TRUE
  FROM tmp_ctx_listino l
 WHERE NOT EXISTS (
     SELECT 1 FROM vendite.listini_versioni lv
      WHERE lv.listino_id = l.listino_id AND lv.attivo = TRUE
        AND lv.validita @> CURRENT_DATE
 );

CREATE TEMP TABLE tmp_ctx_versione AS
SELECT lv.id AS versione_id, lv.listino_id
  FROM vendite.listini_versioni lv, tmp_ctx_listino l
 WHERE lv.listino_id = l.listino_id
   AND lv.attivo IS TRUE
   AND lv.validita @> CURRENT_DATE
 ORDER BY lv.id DESC
 LIMIT 1;

-- Righe listino: padre a 100, A a 10, B a 20.
INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, a.id, a.uom_id, 100
  FROM tmp_ctx_versione v, catalogo.articoli a WHERE a.codice = 'PGTAP_BOM_PADRE';

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, a.id, a.uom_id, 10
  FROM tmp_ctx_versione v, catalogo.articoli a WHERE a.codice = 'PGTAP_BOM_A';

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, a.id, a.uom_id, 20
  FROM tmp_ctx_versione v, catalogo.articoli a WHERE a.codice = 'PGTAP_BOM_B';

-- Matrice categoria -> listino (senza variazione): il resolver STADIO 2 trova match.
INSERT INTO anagrafiche.categorie_clienti_listini(
    categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
    classe_utenza_id, listino_id, valido_dal, valido_al)
SELECT t.categoria_id, t.utility_id, t.emittente_srid,
       NULL, v.listino_id, CURRENT_DATE, CURRENT_DATE + 365
  FROM tmp_ctx t, tmp_ctx_versione v;

-- 1) Precondizione: tutto il setup e' a posto
SELECT is(
    (SELECT COUNT(*)::int FROM vendite.listini_righe lr
      JOIN catalogo.articoli a ON a.id = lr.articolo_id
      JOIN tmp_ctx_versione v ON v.versione_id = lr.listino_versione_id
     WHERE a.codice IN ('PGTAP_BOM_PADRE', 'PGTAP_BOM_A', 'PGTAP_BOM_B')),
    3,
    '(precondizione) 3 righe listino inserite (padre + 2 componenti)'
);

-- 2) CASO A: marco componente A come esposto -> 2 righe, una per ciascun componente.
UPDATE catalogo.articoli_componenti
   SET esposto_in_fattura = TRUE
 WHERE prodotto_id   = (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE')
   AND componente_id = (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_A');

SELECT is(
    (SELECT COUNT(*)::int FROM vendite.fn_resolve_prezzo_composito(
        (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE'),
        (SELECT uom_id FROM tmp_ctx),
        CURRENT_DATE,
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        NULL
    )),
    2,
    'CASO A: almeno un componente esposto -> 2 righe (una per componente)'
);

-- 3) CASO B1: rimuovo l'esposizione, listino padre presente -> 1 riga con prezzo 100.
UPDATE catalogo.articoli_componenti
   SET esposto_in_fattura = FALSE
 WHERE prodotto_id = (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE');

SELECT is(
    (SELECT prezzo_unitario FROM vendite.fn_resolve_prezzo_composito(
        (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE'),
        (SELECT uom_id FROM tmp_ctx),
        CURRENT_DATE,
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        NULL
    )),
    100::numeric,
    'CASO B1: nessun esposto + riga listino padre -> prezzo_unitario = 100'
);

-- 4) CASO B2: tolgo la riga listino del padre -> Sigma componenti = 10*2 + 20*3 = 80.
DELETE FROM vendite.listini_righe
 WHERE articolo_id = (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE');

SELECT is(
    (SELECT prezzo_unitario FROM vendite.fn_resolve_prezzo_composito(
        (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE'),
        (SELECT uom_id FROM tmp_ctx),
        CURRENT_DATE,
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        NULL
    )),
    80::numeric,
    'CASO B2: nessun esposto + no listino padre -> Sigma = 10*2 + 20*3 = 80'
);

SELECT * FROM finish();
ROLLBACK;
