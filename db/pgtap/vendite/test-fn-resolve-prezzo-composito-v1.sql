-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_resolve_prezzo_composito (BoM ibrido pricing v5).
-- Copre i 3 casi logici della funzione + validazione coeff_qta
-- (aggiunto da 20260422-02 per sbloccare BoMComponentExpander).
--
-- Rilevante: dopo l'introduzione del trigger
-- trgfn_articoli_componenti_block_modifica_struttura (BoM immutabile,
-- migration 20260422-01) non e' piu' possibile cambiare i flag di
-- struttura (incluso esposizione_in_fattura) dopo l'INSERT. Il test
-- precedente usava 1 solo prodotto e faceva UPDATE per passare fra i
-- 3 scenari — pattern non piu' ammesso. Questo test riscritto usa
-- 3 prodotti composito distinti, uno per scenario.
--
-- Scenari:
--   CASO A  — almeno un componente esposto -> N righe
--   CASO B1 — nessun esposto, riga listino per il composito -> 1 riga prezzo padre
--   CASO B2 — nessun esposto, no riga listino padre -> 1 riga Sigma componenti
--
-- Elenco test (1..7):
--   1) Precondizione: 3 prodotti padre + 2 componenti + righe listino
--   2) CASO A: 2 righe ritornate (una per ciascun componente obbligatorio)
--   3) CASO A coeff_qta: propagato da ac.coeff_qta (A=2, B=3)
--   4) CASO B1: prezzo_unitario = 100 (riga listino padre)
--   5) CASO B1 coeff_qta = 1 (padre neutro)
--   6) CASO B2: Sigma = 10*2 + 20*3 = 80
--   7) CASO B2 coeff_qta = 1 (padre aggregato)
--
-- BEGIN + ROLLBACK isolamento completo.
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

SELECT plan(7);

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

-- =========================================================
-- 3 prodotti padre (uno per scenario) + 2 componenti condivisi.
-- Post BoM-immutabile (20260422-01): la struttura va fissata
-- all'INSERT, nessun UPDATE successivo e' piu' ammesso.
-- =========================================================

-- Padre CASO A: componenti A esposto + B non esposto -> v_has_esposti=true
INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id,
                              is_composito, attivo)
SELECT 'PGTAP_BOM_PADRE_A', 'Composito padre CASO A pgtap', t.uom_id, t.tipologia_prodotti,
       TRUE, TRUE
  FROM tmp_ctx t;

-- Padre CASO B1: entrambi componenti NON esposti + riga listino sul padre
INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id,
                              is_composito, attivo)
SELECT 'PGTAP_BOM_PADRE_B1', 'Composito padre CASO B1 pgtap', t.uom_id, t.tipologia_prodotti,
       TRUE, TRUE
  FROM tmp_ctx t;

-- Padre CASO B2: entrambi componenti NON esposti + NO riga listino padre
INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id,
                              is_composito, attivo)
SELECT 'PGTAP_BOM_PADRE_B2', 'Composito padre CASO B2 pgtap', t.uom_id, t.tipologia_prodotti,
       TRUE, TRUE
  FROM tmp_ctx t;

-- Componenti condivisi (stessi coeff per riutilizzo dei 3 padri).
INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id, attivo)
SELECT 'PGTAP_BOM_A', 'Componente A pgtap', t.uom_id, t.tipologia_prodotti, TRUE
  FROM tmp_ctx t;

INSERT INTO catalogo.articoli(codice, descrizione, uom_id, listino_tipologia_id, attivo)
SELECT 'PGTAP_BOM_B', 'Componente B pgtap', t.uom_id, t.tipologia_prodotti, TRUE
  FROM tmp_ctx t;

-- BoM CASO A: A DESCRITTIVO coeff=2, B NASCOSTO coeff=3.
INSERT INTO catalogo.articoli_componenti(prodotto_id, componente_id, coeff_qta,
                                         obbligatorio, valido_dal, attivo,
                                         esposizione_in_fattura)
SELECT p.id, a.id, 2, TRUE, CURRENT_DATE, TRUE, 'DESCRITTIVO'
  FROM catalogo.articoli p, catalogo.articoli a
 WHERE p.codice = 'PGTAP_BOM_PADRE_A' AND a.codice = 'PGTAP_BOM_A';

INSERT INTO catalogo.articoli_componenti(prodotto_id, componente_id, coeff_qta,
                                         obbligatorio, valido_dal, attivo,
                                         esposizione_in_fattura)
SELECT p.id, b.id, 3, TRUE, CURRENT_DATE, TRUE, 'NASCOSTO'
  FROM catalogo.articoli p, catalogo.articoli b
 WHERE p.codice = 'PGTAP_BOM_PADRE_A' AND b.codice = 'PGTAP_BOM_B';

-- BoM CASO B1 / CASO B2: entrambi componenti non esposti (stessi coeff).
INSERT INTO catalogo.articoli_componenti(prodotto_id, componente_id, coeff_qta,
                                         obbligatorio, valido_dal, attivo,
                                         esposizione_in_fattura)
SELECT p.id, a.id, 2, TRUE, CURRENT_DATE, TRUE, 'NASCOSTO'
  FROM catalogo.articoli p, catalogo.articoli a
 WHERE p.codice IN ('PGTAP_BOM_PADRE_B1', 'PGTAP_BOM_PADRE_B2') AND a.codice = 'PGTAP_BOM_A';

INSERT INTO catalogo.articoli_componenti(prodotto_id, componente_id, coeff_qta,
                                         obbligatorio, valido_dal, attivo,
                                         esposizione_in_fattura)
SELECT p.id, b.id, 3, TRUE, CURRENT_DATE, TRUE, 'NASCOSTO'
  FROM catalogo.articoli p, catalogo.articoli b
 WHERE p.codice IN ('PGTAP_BOM_PADRE_B1', 'PGTAP_BOM_PADRE_B2') AND b.codice = 'PGTAP_BOM_B';

-- Listino di test: uso un listino PRODOTTI esistente attivo con versione
-- attiva alla data corrente.
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

-- Righe listino: padre B1 a 100 (solo lui ha prezzo diretto), A a 10, B a 20.
-- PADRE_A e PADRE_B2 NON hanno riga listino propria.
INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, a.id, a.uom_id, 100
  FROM tmp_ctx_versione v, catalogo.articoli a WHERE a.codice = 'PGTAP_BOM_PADRE_B1';

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

-- 1) Precondizione: 3 righe listino inserite (padre B1 + 2 componenti).
SELECT is(
    (SELECT COUNT(*)::int FROM vendite.listini_righe lr
      JOIN catalogo.articoli a ON a.id = lr.articolo_id
      JOIN tmp_ctx_versione v ON v.versione_id = lr.listino_versione_id
     WHERE a.codice IN ('PGTAP_BOM_PADRE_B1', 'PGTAP_BOM_A', 'PGTAP_BOM_B')),
    3,
    '(precondizione) 3 righe listino inserite (padre B1 + 2 componenti)'
);

-- =========================================================
-- 2) CASO A: almeno un componente esposto -> 2 righe (una per componente).
-- Uso PGTAP_BOM_PADRE_A: A esposto=TRUE attiva il CASO A.
-- =========================================================
SELECT is(
    (SELECT COUNT(*)::int FROM vendite.fn_resolve_prezzo_composito(
        (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE_A'),
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

-- =========================================================
-- 3) CASO A coeff_qta: propagato da ac.coeff_qta (A=2, B=3).
-- Sblocco BoMComponentExpander (S14.C-BE-1, DEC-3 §14.4.1).
-- =========================================================
SELECT is(
    ARRAY(
        SELECT r.coeff_qta
          FROM vendite.fn_resolve_prezzo_composito(
              (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE_A'),
              (SELECT uom_id FROM tmp_ctx),
              CURRENT_DATE,
              (SELECT ba_id FROM tmp_ctx),
              (SELECT utility_id FROM tmp_ctx),
              (SELECT emittente_srid FROM tmp_ctx),
              NULL
          ) r
          JOIN catalogo.articoli a ON a.id = r.componente_id
         WHERE a.codice IN ('PGTAP_BOM_A', 'PGTAP_BOM_B')
         ORDER BY a.codice
    ),
    ARRAY[2::numeric, 3::numeric],
    'CASO A coeff_qta: riga A=2, riga B=3 (propagato da ac.coeff_qta)'
);

-- =========================================================
-- 4) CASO B1: nessun esposto + riga listino padre -> 1 riga prezzo 100.
-- Uso PGTAP_BOM_PADRE_B1 che ha riga listino propria = 100.
-- =========================================================
SELECT is(
    (SELECT prezzo_unitario FROM vendite.fn_resolve_prezzo_composito(
        (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE_B1'),
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

-- =========================================================
-- 5) CASO B1 coeff_qta = 1 (padre neutro).
-- =========================================================
SELECT is(
    (SELECT coeff_qta FROM vendite.fn_resolve_prezzo_composito(
        (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE_B1'),
        (SELECT uom_id FROM tmp_ctx),
        CURRENT_DATE,
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        NULL
    )),
    1::numeric,
    'CASO B1 coeff_qta = 1 (padre singola riga, moltiplicatore neutro)'
);

-- =========================================================
-- 6) CASO B2: nessun esposto + no listino padre -> Sigma = 10*2 + 20*3 = 80.
-- Uso PGTAP_BOM_PADRE_B2 che non ha riga listino propria.
-- =========================================================
SELECT is(
    (SELECT prezzo_unitario FROM vendite.fn_resolve_prezzo_composito(
        (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE_B2'),
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

-- =========================================================
-- 7) CASO B2 coeff_qta = 1 (padre aggregato, coefficienti gia' applicati).
-- =========================================================
SELECT is(
    (SELECT coeff_qta FROM vendite.fn_resolve_prezzo_composito(
        (SELECT id FROM catalogo.articoli WHERE codice = 'PGTAP_BOM_PADRE_B2'),
        (SELECT uom_id FROM tmp_ctx),
        CURRENT_DATE,
        (SELECT ba_id FROM tmp_ctx),
        (SELECT utility_id FROM tmp_ctx),
        (SELECT emittente_srid FROM tmp_ctx),
        NULL
    )),
    1::numeric,
    'CASO B2 coeff_qta = 1 (padre aggregato Sigma, moltiplicatore neutro)'
);

SELECT * FROM finish();
ROLLBACK;
