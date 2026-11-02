-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

SELECT plan(4);

-- =========================================================================
-- Parte A: utility CON dimensione -> classe letta dal contratto
-- =========================================================================

-- rev 2026-10-27 (lotto 4 di D7): BA, listino, articolo, riga e contratto si
--   COSTRUISCONO. Prima il BA si pescava (il primo con categoria su una utility
--   con dimensione, ORDER BY ba.id LIMIT 1): da zero non c'era, e il file
--   moriva sulla precondizione. Ora si sceglie dal catalogo di seed la UTILITY
--   — con dimensione tipo/classe e una classe (config.tipi_utenze /
--   config.classi_utenze), una tipologia di listino ammessa, e compatibile con
--   l'emittente di chi agisce secondo config.utilities_tipi_ruolo (fail-open
--   come script.fn_guard_utility_tipo_ruolo) — e su quella si costruisce il
--   cliente (dbops.fn_pgtap_crea_cliente_ba, legato all'emittente di chi
--   agisce). Listino e versione da dbops.fn_pgtap_crea_listino (prima INSERT a
--   mano), la riga da dbops.fn_pgtap_listino_aggiungi_articoli, la testata
--   DRAFT da dbops.fn_pgtap_crea_contratto (prima INSERT a mano col numero
--   fisso). La fornitura (contratti_utilities) resta scritta qui: e' il caso.
CREATE TEMP TABLE tmp_utility_wd AS
SELECT u.id AS utility_id
  FROM config.utilities u
 WHERE EXISTS (SELECT 1
                 FROM config.classi_utenze cu
                 JOIN config.tipi_utenze tu ON tu.id = cu.tipo_utenza_id
                WHERE tu.utility_id = u.id)
   AND EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo)
   AND (NOT EXISTS (SELECT 1 FROM config.utilities_tipi_ruolo utr
                     WHERE utr.utility_id = u.id AND utr.attivo IS TRUE
                       AND utr.validita @> script.fn_data_operativa())
        OR EXISTS (SELECT 1
                     FROM config.utilities_tipi_ruolo utr
                     JOIN anagrafiche.soggetti_ruoli sr
                       ON sr.id = script.fn_pgtap_emittente_sr_operatore()
                    WHERE utr.utility_id = u.id
                      AND utr.tipo_ruolo_id = sr.tipo_ruolo_id
                      AND utr.attivo IS TRUE
                      AND utr.validita @> script.fn_data_operativa()))
 ORDER BY u.id
 LIMIT 1;

CREATE TEMP TABLE tmp_cli_wd AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'classe da contratto WD', (SELECT utility_id FROM tmp_utility_wd));

-- 2026-10-08 (§F.2): il listino si COSTRUISCE, della utility e dell'emittente
--   del BA, con la prima tipologia che la utility ammette (guard
--   trgfn_listini_guard_tipologia_utility).
CREATE TEMP TABLE tmp_ctx_wd_versione AS
SELECT l.listino_versione_id AS versione_id, l.listino_id, l.tipologia_id
  FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_utility_wd), 'classe da contratto WD') l;

CREATE TEMP TABLE tmp_ctx_wd_listino AS
SELECT v.listino_id FROM tmp_ctx_wd_versione v;

-- L'articolo del caso: costruito, con la tipologia del listino. Non e' il
--   soggetto del test (lo e' la classe letta dal contratto).
CREATE TEMP TABLE tmp_art_wd AS
SELECT b.articolo_id
  FROM dbops.fn_pgtap_crea_articolo(
           'PGTAP-V5B-WD', false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_ctx_wd_versione)) AS b(articolo_id);

-- In un'istruzione a parte dai builder: le righe che scrivono non sono
-- visibili a una JOIN nella stessa istruzione che li chiama.
CREATE TEMP TABLE tmp_ctx_wd AS
SELECT
    ba.id                       AS ba_id,
    ba.categoria_cliente_id     AS categoria_id,
    ba.istanza_utility_id       AS istanza_utility_id,
    ba.utility_id               AS utility_id,
    -- 2026-10-08 (§F.2): l'emittente del BA, non il primo per id.
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(ba.id)) AS emittente_srid,
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
  FROM tmp_cli_wd c
  JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id
  CROSS JOIN tmp_art_wd t
  JOIN catalogo.articoli a ON a.id = t.articolo_id;

-- 1) Precondizione con dimensione
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_wd WHERE classe_contratto_id IS NOT NULL),
    0,
    '(precondizione) BA su utility con dimensione + classe coerente disponibile'
);

-- Riga di listino a 100. In un DO: una SELECT nuda stamperebbe una riga in
-- mezzo al flusso TAP.
DO $riga_wd$ BEGIN
    PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(
        (SELECT versione_id FROM tmp_ctx_wd_versione),
        ARRAY[(SELECT articolo_id FROM tmp_ctx_wd)],
        100);
END $riga_wd$;

-- Contratto ATTIVO in modalita' A (con listino, senza variazione globale):
-- nasce DRAFT e si attiva dopo la fornitura (rev 2026-10-11, sotto).
CREATE TEMP TABLE tmp_contratto_wd AS
SELECT k.contratto_id
  FROM dbops.fn_pgtap_crea_contratto(
           'classe da contratto WD', 'DRAFT', (SELECT ba_id FROM tmp_ctx_wd), NULL,
           script.fn_data_operativa(), script.fn_data_operativa() + 365, NULL,
           (SELECT listino_id FROM tmp_ctx_wd_listino)) k;

-- Il trigger snapshot precontrattuali potrebbe aver creato la riga gia'.
-- La pulisco e la re-inserisco con classe contrattualizzata nota.
DELETE FROM vendite.contratti_utilities
 WHERE contratto_id = (SELECT contratto_id FROM tmp_contratto_wd);

INSERT INTO vendite.contratti_utilities(
    contratto_id, istanza_utility_id, utility_id,
    tipo_utenza_id, classe_utenza_id)
SELECT c.contratto_id, t.istanza_utility_id, t.utility_id,
       t.tipo_utenza_id, t.classe_contratto_id
  FROM tmp_contratto_wd c, tmp_ctx_wd t;

-- ⛔ rev 2026-10-11 (brief-db-testata-dopo-emissione §11.7): la fornitura si
--   scrive solo in bozza (lock dei satelliti, 20261011-24). Il contratto nasce
--   quindi DRAFT, riceve la sua fornitura, e poi si ATTIVA con la transizione
--   vera (il listino costruito ha una versione in vigore oggi). Prima nasceva
--   ATTIVO e la fornitura gli si cancellava e riscriveva dopo.
-- rev 2026-10-27 (brief-modello-documento-vendita §11, debito del giro 8): il contratto ha la
--   porta sulla colonna di stato; l'attivazione passa dal verbo, che la fixture chiama con
--   emetti_contratto concessa (prima un UPDATE diretto, ora fermato dalla porta).
-- In un DO: una SELECT nuda stamperebbe lo stato in mezzo al flusso TAP.
DO $attiva_wd$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.contratto_id, 'ATTIVO')
       FROM tmp_contratto_wd c;
END $attiva_wd$;

-- 2) Test chiave: chiamo il resolver passando p_classe_utenza_id = NULL.
-- Il resolver deve leggere la classe dal contratto, non dal parametro.
SELECT is(
    (SELECT classe_utenza_id_snapshot
       FROM vendite.fn_resolve_prezzo_listino_v2(
           (SELECT articolo_id FROM tmp_ctx_wd),
           (SELECT uom_id FROM tmp_ctx_wd),
           script.fn_data_operativa(),
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
-- rev 2026-10-27 (lotto 4 di D7): come la parte A — la utility si sceglie dal
--   seed (senza dimensione, tipologia ammessa, compatibile con l'emittente),
--   cliente, listino, articolo, riga e testata si costruiscono (prima il BA si
--   pescava, il listino e il contratto si scrivevano a mano).
CREATE TEMP TABLE tmp_utility_nd AS
SELECT u.id AS utility_id
  FROM config.utilities u
 WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
   AND EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo)
   AND (NOT EXISTS (SELECT 1 FROM config.utilities_tipi_ruolo utr
                     WHERE utr.utility_id = u.id AND utr.attivo IS TRUE
                       AND utr.validita @> script.fn_data_operativa())
        OR EXISTS (SELECT 1
                     FROM config.utilities_tipi_ruolo utr
                     JOIN anagrafiche.soggetti_ruoli sr
                       ON sr.id = script.fn_pgtap_emittente_sr_operatore()
                    WHERE utr.utility_id = u.id
                      AND utr.tipo_ruolo_id = sr.tipo_ruolo_id
                      AND utr.attivo IS TRUE
                      AND utr.validita @> script.fn_data_operativa()))
 ORDER BY u.id
 LIMIT 1;

CREATE TEMP TABLE tmp_cli_nd AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'classe da contratto ND', (SELECT utility_id FROM tmp_utility_nd));

-- 2026-10-08 (§F.2): il listino si COSTRUISCE, della utility e dell'emittente
--   del BA, con la prima tipologia che la utility ammette (guard
--   trgfn_listini_guard_tipologia_utility).
CREATE TEMP TABLE tmp_ctx_nd_versione AS
SELECT l.listino_versione_id AS versione_id, l.listino_id, l.tipologia_id
  FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_utility_nd), 'classe da contratto ND') l;

CREATE TEMP TABLE tmp_ctx_nd_listino AS
SELECT v.listino_id FROM tmp_ctx_nd_versione v;

-- L'articolo del caso: costruito, con la tipologia del listino. Non e' il
--   soggetto del test (lo e' la classe letta dal contratto).
CREATE TEMP TABLE tmp_art_nd AS
SELECT b.articolo_id
  FROM dbops.fn_pgtap_crea_articolo(
           'PGTAP-V5B-ND', false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_ctx_nd_versione)) AS b(articolo_id);

-- In un'istruzione a parte dai builder: le righe che scrivono non sono
-- visibili a una JOIN nella stessa istruzione che li chiama.
CREATE TEMP TABLE tmp_ctx_nd AS
SELECT
    ba.id                       AS ba_id,
    ba.categoria_cliente_id     AS categoria_id,
    ba.istanza_utility_id       AS istanza_utility_id,
    ba.utility_id               AS utility_id,
    -- 2026-10-08 (§F.2): l'emittente del BA, non il primo per id.
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(ba.id)) AS emittente_srid,
    a.id                        AS articolo_id,
    a.uom_id                    AS uom_id,
    a.listino_tipologia_id      AS tipologia_id,
    -- Classe fittizia passata come parametro input (non esiste nel contratto).
    (SELECT id FROM config.classi_utenze ORDER BY id LIMIT 1) AS classe_input_id
  FROM tmp_cli_nd c
  JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id
  CROSS JOIN tmp_art_nd t
  JOIN catalogo.articoli a ON a.id = t.articolo_id;

-- 3) Precondizione no-dim
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_nd),
    0,
    '(precondizione) BA su utility senza dimensione tipo/classe disponibile'
);

-- Riga di listino a 100 (in un DO, come sopra).
DO $riga_nd$ BEGIN
    PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(
        (SELECT versione_id FROM tmp_ctx_nd_versione),
        ARRAY[(SELECT articolo_id FROM tmp_ctx_nd)],
        100);
END $riga_nd$;

-- Contratto ATTIVO su utility commercio (contratti_utilities avra' classe NULL):
-- nasce DRAFT e si attiva dopo la fornitura (rev 2026-10-11, sotto).
CREATE TEMP TABLE tmp_contratto_nd AS
SELECT k.contratto_id
  FROM dbops.fn_pgtap_crea_contratto(
           'classe da contratto ND', 'DRAFT', (SELECT ba_id FROM tmp_ctx_nd), NULL,
           script.fn_data_operativa(), script.fn_data_operativa() + 365, NULL,
           (SELECT listino_id FROM tmp_ctx_nd_listino)) k;

-- Garantisco esistenza riga contratti_utilities con classe NULL
-- (il trigger snapshot puo' averla creata o meno a seconda dei precontrattuali).
DELETE FROM vendite.contratti_utilities
 WHERE contratto_id = (SELECT contratto_id FROM tmp_contratto_nd);

INSERT INTO vendite.contratti_utilities(
    contratto_id, istanza_utility_id, utility_id,
    tipo_utenza_id, classe_utenza_id)
SELECT c.contratto_id, t.istanza_utility_id, t.utility_id,
       NULL, NULL
  FROM tmp_contratto_nd c, tmp_ctx_nd t;

-- ⛔ rev 2026-10-11 (brief-db-testata-dopo-emissione §11.7): la fornitura si
--   scrive solo in bozza (lock dei satelliti, 20261011-24). Il contratto nasce
--   quindi DRAFT, riceve la sua fornitura, e poi si ATTIVA con la transizione
--   vera (il listino costruito ha una versione in vigore oggi). Prima nasceva
--   ATTIVO e la fornitura gli si cancellava e riscriveva dopo.
-- rev 2026-10-27 (§11, debito del giro 8): dal verbo, come il contratto del test 2.
-- In un DO: una SELECT nuda stamperebbe lo stato in mezzo al flusso TAP.
DO $attiva_nd$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.contratto_id, 'ATTIVO')
       FROM tmp_contratto_nd c;
END $attiva_nd$;

-- 4) Test: classe da contratto NULL -> fallback al parametro input
SELECT is(
    (SELECT classe_utenza_id_snapshot
       FROM vendite.fn_resolve_prezzo_listino_v2(
           (SELECT articolo_id FROM tmp_ctx_nd),
           (SELECT uom_id FROM tmp_ctx_nd),
           script.fn_data_operativa(),
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
