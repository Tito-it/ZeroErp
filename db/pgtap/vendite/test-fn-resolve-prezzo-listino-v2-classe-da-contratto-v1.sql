-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T5b: classe_utenza_id_snapshot letta da contratto (pricing v5).
-- Verifica che il resolver v2, quando trova un contratto attivo, usi la
-- classe dichiarata in contratti_utilities invece del parametro input.
--
-- Elenco test (1..4):
--   1) Precondizione: BA su utility CON dimensione tipo/classe + classe coerente
--   2) Contratto con contratti_utilities.classe_utenza_id VALORIZZATA ->
--      classe_utenza_id_snapshot = quella del contratto (ignora input diverso)
--   3) Precondizione: BA su utility SENZA dimensione + contratto
--   4) Contratto con contratti_utilities.classe_utenza_id NULL (utility
--      commercio) -> classe_utenza_id_snapshot = parametro input (fallback)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- =========================================================================
-- Parte A: utility CON dimensione -> classe letta dal contratto
-- =========================================================================

-- Precondizioni: BA su utility con dimensione + categoria + classe coerente + listino.
CREATE TEMP TABLE tmp_ctx_wd AS
SELECT
    ba.id                       AS ba_id,
    ba.categoria_cliente_id     AS categoria_id,
    ba.istanza_utility_id       AS istanza_utility_id,
    ba.utility_id               AS utility_id,
    (SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali
       WHERE attivo IS TRUE ORDER BY id LIMIT 1)                       AS emittente_srid,
    a.id                        AS articolo_id,
    a.uom_id                    AS uom_id,
    a.listino_tipologia_id      AS tipologia_id,
    -- Classe dichiarata sul contratto (coerente con la utility del BA).
    (SELECT cu.id
       FROM config.classi_utenze cu
       JOIN config.tipi_utenze tu ON tu.id = cu.tipo_utenza_id
      WHERE tu.utility_id = ba.utility_id
      ORDER BY cu.id LIMIT 1)                                          AS classe_contratto_id,
    (SELECT cu.tipo_utenza_id
       FROM config.classi_utenze cu
       JOIN config.tipi_utenze tu ON tu.id = cu.tipo_utenza_id
      WHERE tu.utility_id = ba.utility_id
      ORDER BY cu.id LIMIT 1)                                          AS tipo_utenza_id
  FROM anagrafiche.billing_account ba
  JOIN catalogo.articoli a
    ON a.attivo IS TRUE
   AND a.listino_tipologia_id IS NOT NULL
 WHERE ba.categoria_cliente_id IS NOT NULL
   AND EXISTS (
       SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
   )
 ORDER BY ba.id, a.id
 LIMIT 1;

-- 1) Precondizione con dimensione
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_wd WHERE classe_contratto_id IS NOT NULL),
    0,
    '(precondizione) BA su utility con dimensione + classe coerente disponibile'
);

-- Listino con versione attiva e riga (riusa struttura esistente o crea in-TX).
CREATE TEMP TABLE tmp_ctx_wd_listino AS
SELECT l.id AS listino_id
  FROM vendite.listini l, tmp_ctx_wd t
 WHERE l.tipologia_id = t.tipologia_id
   AND l.attivo       = TRUE
 ORDER BY l.id LIMIT 1;

INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, valido_al, stato, attivo)
SELECT l.listino_id, 'PGTAP_V5B_VER', CURRENT_DATE, CURRENT_DATE + 365, 'ATTIVA', TRUE
  FROM tmp_ctx_wd_listino l
 WHERE NOT EXISTS (
     SELECT 1 FROM vendite.listini_versioni lv
      WHERE lv.listino_id = l.listino_id AND lv.attivo = TRUE
        AND lv.validita @> CURRENT_DATE
 );

CREATE TEMP TABLE tmp_ctx_wd_versione AS
SELECT lv.id AS versione_id, lv.listino_id
  FROM vendite.listini_versioni lv, tmp_ctx_wd_listino l
 WHERE lv.listino_id = l.listino_id
   AND lv.attivo IS TRUE
   AND lv.validita @> CURRENT_DATE
 ORDER BY lv.id DESC LIMIT 1;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, t.articolo_id, t.uom_id, 100
  FROM tmp_ctx_wd_versione v, tmp_ctx_wd t
ON CONFLICT DO NOTHING;

-- Contratto ATTIVO in modalita' A (con listino, senza variazione globale).
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
    valido_dal, valido_al, listino_id)
SELECT 'PGTAP_V5B_CONTR_WD', t.ba_id, t.istanza_utility_id, t.utility_id,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO'),
       CURRENT_DATE, CURRENT_DATE + 365, v.listino_id
  FROM tmp_ctx_wd t, tmp_ctx_wd_versione v;

-- Il trigger snapshot precontrattuali potrebbe aver creato la riga gia'.
-- La pulisco e la re-inserisco con classe contrattualizzata nota.
DELETE FROM vendite.contratti_utilities
 WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_V5B_CONTR_WD');

INSERT INTO vendite.contratti_utilities(
    contratto_id, istanza_utility_id, utility_id,
    tipo_utenza_id, classe_utenza_id)
SELECT c.id, t.istanza_utility_id, t.utility_id,
       t.tipo_utenza_id, t.classe_contratto_id
  FROM vendite.contratti c, tmp_ctx_wd t
 WHERE c.numero = 'PGTAP_V5B_CONTR_WD';

-- 2) Test chiave: chiamo il resolver passando p_classe_utenza_id = NULL.
-- Il resolver deve leggere la classe dal contratto, non dal parametro.
SELECT is(
    (SELECT classe_utenza_id_snapshot
       FROM vendite.fn_resolve_prezzo_listino_v2(
           (SELECT articolo_id FROM tmp_ctx_wd),
           (SELECT uom_id FROM tmp_ctx_wd),
           CURRENT_DATE,
           (SELECT ba_id FROM tmp_ctx_wd),
           (SELECT utility_id FROM tmp_ctx_wd),
           (SELECT emittente_srid FROM tmp_ctx_wd),
           NULL  -- input NULL: se il resolver leggesse il parametro avrebbe NULL
       )),
    (SELECT classe_contratto_id FROM tmp_ctx_wd),
    'STADIO 1: classe_utenza_id_snapshot letta da contratti_utilities (non dal parametro input NULL)'
);

-- =========================================================================
-- Parte B: utility SENZA dimensione -> fallback al parametro input
-- =========================================================================

-- BA su utility commercio (no tipi_utenze).
CREATE TEMP TABLE tmp_ctx_nd AS
SELECT
    ba.id                       AS ba_id,
    ba.categoria_cliente_id     AS categoria_id,
    ba.istanza_utility_id       AS istanza_utility_id,
    ba.utility_id               AS utility_id,
    (SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali
       WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS emittente_srid,
    a.id                        AS articolo_id,
    a.uom_id                    AS uom_id,
    a.listino_tipologia_id      AS tipologia_id,
    -- Classe fittizia passata come parametro input (non esiste nel contratto).
    (SELECT id FROM config.classi_utenze ORDER BY id LIMIT 1) AS classe_input_id
  FROM anagrafiche.billing_account ba
  JOIN catalogo.articoli a
    ON a.attivo IS TRUE
   AND a.listino_tipologia_id IS NOT NULL
 WHERE ba.categoria_cliente_id IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
   )
 ORDER BY ba.id, a.id
 LIMIT 1;

-- 3) Precondizione no-dim
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_nd),
    0,
    '(precondizione) BA su utility senza dimensione tipo/classe disponibile'
);

CREATE TEMP TABLE tmp_ctx_nd_listino AS
SELECT l.id AS listino_id
  FROM vendite.listini l, tmp_ctx_nd t
 WHERE l.tipologia_id = t.tipologia_id
   AND l.attivo       = TRUE
 ORDER BY l.id LIMIT 1;

INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, valido_al, stato, attivo)
SELECT l.listino_id, 'PGTAP_V5B_VER_ND', CURRENT_DATE, CURRENT_DATE + 365, 'ATTIVA', TRUE
  FROM tmp_ctx_nd_listino l
 WHERE NOT EXISTS (
     SELECT 1 FROM vendite.listini_versioni lv
      WHERE lv.listino_id = l.listino_id AND lv.attivo = TRUE
        AND lv.validita @> CURRENT_DATE
 );

CREATE TEMP TABLE tmp_ctx_nd_versione AS
SELECT lv.id AS versione_id, lv.listino_id
  FROM vendite.listini_versioni lv, tmp_ctx_nd_listino l
 WHERE lv.listino_id = l.listino_id
   AND lv.attivo IS TRUE
   AND lv.validita @> CURRENT_DATE
 ORDER BY lv.id DESC LIMIT 1;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, t.articolo_id, t.uom_id, 100
  FROM tmp_ctx_nd_versione v, tmp_ctx_nd t
ON CONFLICT DO NOTHING;

-- Contratto ATTIVO su utility commercio (contratti_utilities avra' classe NULL).
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
    valido_dal, valido_al, listino_id)
SELECT 'PGTAP_V5B_CONTR_ND', t.ba_id, t.istanza_utility_id, t.utility_id,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO'),
       CURRENT_DATE, CURRENT_DATE + 365, v.listino_id
  FROM tmp_ctx_nd t, tmp_ctx_nd_versione v;

-- Garantisco esistenza riga contratti_utilities con classe NULL
-- (il trigger snapshot puo' averla creata o meno a seconda dei precontrattuali).
DELETE FROM vendite.contratti_utilities
 WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_V5B_CONTR_ND');

INSERT INTO vendite.contratti_utilities(
    contratto_id, istanza_utility_id, utility_id,
    tipo_utenza_id, classe_utenza_id)
SELECT c.id, t.istanza_utility_id, t.utility_id,
       NULL, NULL
  FROM vendite.contratti c, tmp_ctx_nd t
 WHERE c.numero = 'PGTAP_V5B_CONTR_ND';

-- 4) Test: classe da contratto NULL -> fallback al parametro input
SELECT is(
    (SELECT classe_utenza_id_snapshot
       FROM vendite.fn_resolve_prezzo_listino_v2(
           (SELECT articolo_id FROM tmp_ctx_nd),
           (SELECT uom_id FROM tmp_ctx_nd),
           CURRENT_DATE,
           (SELECT ba_id FROM tmp_ctx_nd),
           (SELECT utility_id FROM tmp_ctx_nd),
           (SELECT emittente_srid FROM tmp_ctx_nd),
           (SELECT classe_input_id FROM tmp_ctx_nd)
       )),
    (SELECT classe_input_id FROM tmp_ctx_nd),
    'STADIO 1 fallback: contratti_utilities.classe_utenza_id NULL -> snapshot = parametro input'
);

SELECT * FROM finish();
ROLLBACK;
