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

-- Precondizioni: BA su utility con dimensione + categoria + classe coerente + listino.
CREATE TEMP TABLE tmp_ctx_wd AS
SELECT
    ba.id                       AS ba_id,
    ba.categoria_cliente_id     AS categoria_id,
    ba.istanza_utility_id       AS istanza_utility_id,
    ba.utility_id               AS utility_id,
    -- 2026-10-08 (§F.2): l'emittente del BA, non il primo per id.
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(ba.id))                       AS emittente_srid,
    -- 2026-10-08 (§F.2): l'articolo si costruisce qui sotto, con la prima tipologia
    --   che la utility del BA ammette (come fn_pgtap_crea_listino).
    NULL::uuid                  AS articolo_id,
    NULL::bigint                AS uom_id,
    (SELECT ltu.tipologia_id FROM config.listini_tipologie_utilities ltu
       JOIN config.listini_tipologie lt ON lt.id = ltu.tipologia_id AND lt.attivo
      WHERE ltu.utility_id = ba.utility_id AND ltu.attivo
      ORDER BY lt.ordinamento, lt.id LIMIT 1) AS tipologia_id,
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
 WHERE ba.categoria_cliente_id IS NOT NULL
   AND EXISTS (
       SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
   )
   -- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
   --   contratto e' della sua utility e del suo emittente (guard nuovo). Listino e
   --   articolo si COSTRUISCONO qui sotto, con una tipologia che la utility del BA
   --   ammette (guard trgfn_listini_guard_tipologia_utility).
   --   ⚠️ Due stesure dello stesso giorno, entrambe rosse su dbdev: prima si cercava
   --   fra i dati un listino gia' coerente, poi un articolo dei dati con una tipologia
   --   della utility del BA. Nessuno dei due c'era. L'articolo non e' il soggetto del
   --   test (lo e' la classe letta dal contratto): si costruisce.
   AND EXISTS (
       SELECT 1 FROM config.listini_tipologie_utilities ltu
        WHERE ltu.utility_id = ba.utility_id AND ltu.attivo
   )
 ORDER BY ba.id
 LIMIT 1;

-- 1) Precondizione con dimensione
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_wd WHERE classe_contratto_id IS NOT NULL),
    0,
    '(precondizione) BA su utility con dimensione + classe coerente disponibile'
);

-- Listino con versione attiva e riga (riusa struttura esistente o crea in-TX).
-- L'articolo del caso: costruito, con la tipologia del contesto.
UPDATE tmp_ctx_wd SET articolo_id = dbops.fn_pgtap_crea_articolo('PGTAP-V5B-WD',
    p_listino_tipologia_id => tipologia_id);
UPDATE tmp_ctx_wd t
   SET uom_id = (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = t.articolo_id);

-- 2026-10-08 (§F.2): il listino si COSTRUISCE, della tipologia dell'articolo, della
--   utility e dell'emittente del BA. Prima era il primo listino di quella tipologia,
--   di qualunque utility ed emittente.
CREATE TEMP TABLE tmp_ctx_wd_listino AS
WITH ins AS (
    INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_V5B_WD_' || substr(md5(clock_timestamp()::text || random()::text), 1, 12),
           'Fixture pgTAP: classe da contratto WD', t.utility_id, t.tipologia_id, t.emittente_srid
      FROM tmp_ctx_wd t
    RETURNING id)
SELECT id AS listino_id FROM ins;

INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, valido_al, stato, attivo)
SELECT l.listino_id, 'PGTAP_V5B_VER', script.fn_data_operativa(), script.fn_data_operativa() + 365, 'ATTIVA', TRUE
  FROM tmp_ctx_wd_listino l
 WHERE NOT EXISTS (
     SELECT 1 FROM vendite.listini_versioni lv
      WHERE lv.listino_id = l.listino_id AND lv.attivo = TRUE
        AND lv.validita @> script.fn_data_operativa()
 );

CREATE TEMP TABLE tmp_ctx_wd_versione AS
SELECT lv.id AS versione_id, lv.listino_id
  FROM vendite.listini_versioni lv, tmp_ctx_wd_listino l
 WHERE lv.listino_id = l.listino_id
   AND lv.attivo IS TRUE
   AND lv.validita @> script.fn_data_operativa()
 ORDER BY lv.id DESC LIMIT 1;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, t.articolo_id, t.uom_id, 100
  FROM tmp_ctx_wd_versione v, tmp_ctx_wd t
ON CONFLICT DO NOTHING;

-- Contratto ATTIVO in modalita' A (con listino, senza variazione globale):
-- nasce DRAFT e si attiva dopo la fornitura (rev 2026-10-11, sotto).
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
    valido_dal, valido_al, listino_id)
SELECT 'PGTAP_V5B_CONTR_WD', t.ba_id, t.istanza_utility_id, t.utility_id,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
       script.fn_data_operativa(), script.fn_data_operativa() + 365, v.listino_id
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

-- ⛔ rev 2026-10-11 (brief-db-testata-dopo-emissione §11.7): la fornitura si
--   scrive solo in bozza (lock dei satelliti, 20261011-24). Il contratto nasce
--   quindi DRAFT, riceve la sua fornitura, e poi si ATTIVA con la transizione
--   vera (il listino costruito ha una versione in vigore oggi). Prima nasceva
--   ATTIVO e la fornitura gli si cancellava e riscriveva dopo.
-- rev 2026-10-27 (brief-modello-documento-vendita §11, debito del giro 8): il contratto ha la
--   porta sulla colonna di stato; l'attivazione passa dal verbo, che la fixture chiama con
--   emetti_contratto concessa (prima un UPDATE diretto, ora fermato dalla porta).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c
 WHERE c.numero = 'PGTAP_V5B_CONTR_WD';

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
CREATE TEMP TABLE tmp_ctx_nd AS
SELECT
    ba.id                       AS ba_id,
    ba.categoria_cliente_id     AS categoria_id,
    ba.istanza_utility_id       AS istanza_utility_id,
    ba.utility_id               AS utility_id,
    -- 2026-10-08 (§F.2): l'emittente del BA, non il primo per id.
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(ba.id)) AS emittente_srid,
    -- 2026-10-08 (§F.2): l'articolo si costruisce qui sotto, con la prima tipologia
    --   che la utility del BA ammette (come fn_pgtap_crea_listino).
    NULL::uuid                  AS articolo_id,
    NULL::bigint                AS uom_id,
    (SELECT ltu.tipologia_id FROM config.listini_tipologie_utilities ltu
       JOIN config.listini_tipologie lt ON lt.id = ltu.tipologia_id AND lt.attivo
      WHERE ltu.utility_id = ba.utility_id AND ltu.attivo
      ORDER BY lt.ordinamento, lt.id LIMIT 1) AS tipologia_id,
    -- Classe fittizia passata come parametro input (non esiste nel contratto).
    (SELECT id FROM config.classi_utenze ORDER BY id LIMIT 1) AS classe_input_id
  FROM anagrafiche.billing_account ba
 WHERE ba.categoria_cliente_id IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
   )
   -- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
   --   contratto e' della sua utility e del suo emittente (guard nuovo). Listino e
   --   articolo si COSTRUISCONO qui sotto, con una tipologia che la utility del BA
   --   ammette (guard trgfn_listini_guard_tipologia_utility).
   --   ⚠️ Due stesure dello stesso giorno, entrambe rosse su dbdev: prima si cercava
   --   fra i dati un listino gia' coerente, poi un articolo dei dati con una tipologia
   --   della utility del BA. Nessuno dei due c'era. L'articolo non e' il soggetto del
   --   test (lo e' la classe letta dal contratto): si costruisce.
   AND EXISTS (
       SELECT 1 FROM config.listini_tipologie_utilities ltu
        WHERE ltu.utility_id = ba.utility_id AND ltu.attivo
   )
 ORDER BY ba.id
 LIMIT 1;

-- 3) Precondizione no-dim
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_nd),
    0,
    '(precondizione) BA su utility senza dimensione tipo/classe disponibile'
);

-- L'articolo del caso: costruito, con la tipologia del contesto.
UPDATE tmp_ctx_nd SET articolo_id = dbops.fn_pgtap_crea_articolo('PGTAP-V5B-ND',
    p_listino_tipologia_id => tipologia_id);
UPDATE tmp_ctx_nd t
   SET uom_id = (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = t.articolo_id);

-- 2026-10-08 (§F.2): il listino si COSTRUISCE, della tipologia dell'articolo, della
--   utility e dell'emittente del BA. Prima era il primo listino di quella tipologia,
--   di qualunque utility ed emittente.
CREATE TEMP TABLE tmp_ctx_nd_listino AS
WITH ins AS (
    INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_V5B_ND_' || substr(md5(clock_timestamp()::text || random()::text), 1, 12),
           'Fixture pgTAP: classe da contratto ND', t.utility_id, t.tipologia_id, t.emittente_srid
      FROM tmp_ctx_nd t
    RETURNING id)
SELECT id AS listino_id FROM ins;

INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, valido_al, stato, attivo)
SELECT l.listino_id, 'PGTAP_V5B_VER_ND', script.fn_data_operativa(), script.fn_data_operativa() + 365, 'ATTIVA', TRUE
  FROM tmp_ctx_nd_listino l
 WHERE NOT EXISTS (
     SELECT 1 FROM vendite.listini_versioni lv
      WHERE lv.listino_id = l.listino_id AND lv.attivo = TRUE
        AND lv.validita @> script.fn_data_operativa()
 );

CREATE TEMP TABLE tmp_ctx_nd_versione AS
SELECT lv.id AS versione_id, lv.listino_id
  FROM vendite.listini_versioni lv, tmp_ctx_nd_listino l
 WHERE lv.listino_id = l.listino_id
   AND lv.attivo IS TRUE
   AND lv.validita @> script.fn_data_operativa()
 ORDER BY lv.id DESC LIMIT 1;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, t.articolo_id, t.uom_id, 100
  FROM tmp_ctx_nd_versione v, tmp_ctx_nd t
ON CONFLICT DO NOTHING;

-- Contratto ATTIVO su utility commercio (contratti_utilities avra' classe NULL):
-- nasce DRAFT e si attiva dopo la fornitura (rev 2026-10-11, sotto).
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
    valido_dal, valido_al, listino_id)
SELECT 'PGTAP_V5B_CONTR_ND', t.ba_id, t.istanza_utility_id, t.utility_id,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
       script.fn_data_operativa(), script.fn_data_operativa() + 365, v.listino_id
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

-- ⛔ rev 2026-10-11 (brief-db-testata-dopo-emissione §11.7): la fornitura si
--   scrive solo in bozza (lock dei satelliti, 20261011-24). Il contratto nasce
--   quindi DRAFT, riceve la sua fornitura, e poi si ATTIVA con la transizione
--   vera (il listino costruito ha una versione in vigore oggi). Prima nasceva
--   ATTIVO e la fornitura gli si cancellava e riscriveva dopo.
-- rev 2026-10-27 (§11, debito del giro 8): dal verbo, come il contratto del test 2.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c
 WHERE c.numero = 'PGTAP_V5B_CONTR_ND';

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
