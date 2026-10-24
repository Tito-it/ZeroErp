-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test del meccanismo GENERICO di successione contratti su overlap:
--   vendite.fn_contratto_sovrapposto(billing_account, istanza_utility,
--       utility, ambito, valido_dal, valido_al) RETURNS bigint   (STABLE)
--   vendite.fn_chiudi_contratto_per_successione(contratto_id,
--       nuovo_valido_dal) RETURNS date
--
-- Riferimento: brief-db-offerta-push-successione-contratto-overlap.md §4
--
-- Indice test (1..12):
--   1)  fn_contratto_sovrapposto presente
--   2)  fn_chiudi_contratto_per_successione presente
--   3)  rilevamento con overlap reale -> id del contratto incumbent
--   4)  rilevamento senza overlap -> NULL
--   5)  rilevamento ignora contratti abortiti -> NULL
--   6)  rilevamento con valido_al NULL (perpetuo) -> id (COALESCE simmetrico)
--   7)  fn_chiudi con date valide -> ritorna nuovo_valido_dal - 1
--   8)  fn_chiudi con date valide -> valido_al aggiornato sul contratto
--   9)  fn_chiudi con data invalida -> throws E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA
--   10) fn_chiudi con data invalida -> contratto invariato
--   11) fn_chiudi su contratto ATTIVO -> accorciamento consentito (regressione lock)
--   12) fn_chiudi su contratto ATTIVO -> valido_al aggiornato
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i contratti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano
--   gia' ATTIVO o abortiti). Un contratto si attiva su un listino con una
--   versione in vigore: gli ATTIVO lo prendono da dbops.fn_pgtap_crea_listino.
--
-- Fixture: un solo billing_account, finestre temporali disgiunte (nessun
-- conflitto con ex_contratti_no_overlap), emittente coerente con il BA.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(12);

-- ============================================================
-- Setup fixture
-- ============================================================
CREATE TEMP TABLE tmp_succ_ctx AS
SELECT
    ba.id                 AS ba_id,
    ba.istanza_utility_id AS istanza_utility_id,
    ba.utility_id         AS utility_id,
    anagrafiche.fn_get_emittente_fiscale_pk(ba.id) AS emittente_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
    -- lo stato abortito si raggiunge per la matrice: il codice, non l'id
    (SELECT codice_interno FROM config.stati_doc_contratti WHERE is_abortito IS TRUE ORDER BY id LIMIT 1) AS cod_abortito
  FROM anagrafiche.billing_account ba
 WHERE anagrafiche.fn_get_emittente_fiscale_pk(ba.id) IS NOT NULL
 ORDER BY ba.id
 LIMIT 1;

-- Il listino dei contratti ATTIVO: DRAFT->ATTIVO congela la versione in
-- vigore (trgfn_contratti_freeze_listino_versione); senza listino il
-- contratto vorrebbe righe AGGIUNTA con prezzo. LATERAL: con il contesto
-- vuoto il builder non si chiama.
CREATE TEMP TABLE tmp_succ_listino AS
SELECT l.listino_id
  FROM tmp_succ_ctx c,
       LATERAL dbops.fn_pgtap_crea_listino(c.utility_id, 'successione contratti') l;

-- C_A: ATTIVO, finestra 2080 (incumbent per il test di overlap)
-- ⭐ ATTIVO e non DRAFT, ed e' la correzione del 2026-08-24: dal changeSet
--    20260602-18 («Overlap contratti: escludere i DRAFT dal vincolo») la
--    partecipazione all'overlap e' decisa dalla colonna GENERATED
--    `partecipa_overlap_snapshot = NOT is_abortito AND NOT is_draft`. Un
--    incumbent in bozza non blocca nessuno — di proposito — e il test 3
--    misurava quindi il caso sbagliato: NULL invece dell'id.
--    ⛔ rev 2026-10-24: fino a oggi lo stato si metteva all'INSERT («nascere
--    ATTIVO e' lecito»). Non lo e' piu': un contratto nasce in DRAFT
--    (trg_contratti_a05_stato_iniziale_ins) e si attiva per la matrice, sotto
--    il guard di transizione.
INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
    utility_id, emittente_fiscale_id, listino_id, valido_dal, valido_al)
SELECT 'PGTAP_SUCC_A', c.ba_id, c.istanza_utility_id, c.utility_id, c.emittente_id,
       l.listino_id, '2080-01-01'::date, '2080-12-31'::date
  FROM tmp_succ_ctx c, tmp_succ_listino l;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', k.id, 'ATTIVO')
  FROM vendite.contratti k
 WHERE k.numero = 'PGTAP_SUCC_A';

-- C_ABORT: stato abortito, finestra 2082 (deve essere ignorato dal rilevamento)
INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
    utility_id, emittente_fiscale_id, valido_dal, valido_al)
SELECT 'PGTAP_SUCC_ABORT', c.ba_id, c.istanza_utility_id, c.utility_id, c.emittente_id,
       '2082-01-01'::date, '2082-12-31'::date
  FROM tmp_succ_ctx c;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', k.id, c.cod_abortito)
  FROM vendite.contratti k, tmp_succ_ctx c
 WHERE k.numero = 'PGTAP_SUCC_ABORT';

-- C_SUCC: DRAFT, finestra 2100 (per fn_chiudi date valide)
INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
    utility_id, emittente_fiscale_id, stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_SUCC_SUCC', c.ba_id, c.istanza_utility_id, c.utility_id, c.emittente_id,
       c.id_draft, '2100-01-01'::date, '2100-12-31'::date
  FROM tmp_succ_ctx c;

-- C_BAD: DRAFT, finestra 2102-06.. (per fn_chiudi data invalida)
INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
    utility_id, emittente_fiscale_id, stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_SUCC_BAD', c.ba_id, c.istanza_utility_id, c.utility_id, c.emittente_id,
       c.id_draft, '2102-06-01'::date, '2102-12-31'::date
  FROM tmp_succ_ctx c;

-- C_ATT: ATTIVO, finestra 2104 (regressione lock post-attivazione)
INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
    utility_id, emittente_fiscale_id, listino_id, valido_dal, valido_al)
SELECT 'PGTAP_SUCC_ATT', c.ba_id, c.istanza_utility_id, c.utility_id, c.emittente_id,
       l.listino_id, '2104-01-01'::date, '2104-12-31'::date
  FROM tmp_succ_ctx c, tmp_succ_listino l;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', k.id, 'ATTIVO')
  FROM vendite.contratti k
 WHERE k.numero = 'PGTAP_SUCC_ATT';

-- C_PERP: ATTIVO, perpetuo 2110.. (valido_al NULL)
INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
    utility_id, emittente_fiscale_id, listino_id, valido_dal, valido_al)
-- ⭐ ATTIVO per la stessa ragione di C_A: un perpetuo in bozza non partecipa
--    all'overlap, e il test 6 misurerebbe il caso sbagliato.
SELECT 'PGTAP_SUCC_PERP', c.ba_id, c.istanza_utility_id, c.utility_id, c.emittente_id,
       l.listino_id, '2110-01-01'::date, NULL::date
  FROM tmp_succ_ctx c, tmp_succ_listino l;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', k.id, 'ATTIVO')
  FROM vendite.contratti k
 WHERE k.numero = 'PGTAP_SUCC_PERP';

-- ============================================================
-- 1) fn_contratto_sovrapposto presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite' AND p.proname = 'fn_contratto_sovrapposto'
    ),
    '1) vendite.fn_contratto_sovrapposto presente'
);

-- ============================================================
-- 2) fn_chiudi_contratto_per_successione presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite' AND p.proname = 'fn_chiudi_contratto_per_successione'
    ),
    '2) vendite.fn_chiudi_contratto_per_successione presente'
);

-- ============================================================
-- 3) Overlap reale -> id del contratto incumbent (C_A)
-- ============================================================
SELECT is(
    vendite.fn_contratto_sovrapposto(
        (SELECT ba_id FROM tmp_succ_ctx),
        (SELECT istanza_utility_id FROM tmp_succ_ctx),
        (SELECT utility_id FROM tmp_succ_ctx),
        'COMMODITY',
        '2080-05-01'::date, '2080-06-01'::date
    ),
    (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_SUCC_A'),
    '3) overlap reale -> id del contratto incumbent'
);

-- ============================================================
-- 4) Nessun overlap (finestra 2085 libera) -> NULL
-- ============================================================
SELECT is(
    vendite.fn_contratto_sovrapposto(
        (SELECT ba_id FROM tmp_succ_ctx),
        (SELECT istanza_utility_id FROM tmp_succ_ctx),
        (SELECT utility_id FROM tmp_succ_ctx),
        'COMMODITY',
        '2085-01-01'::date, '2085-06-01'::date
    ),
    NULL::bigint,
    '4) nessun overlap -> NULL'
);

-- ============================================================
-- 5) Ignora contratti abortiti (finestra 2082, solo C_ABORT) -> NULL
-- ============================================================
SELECT is(
    vendite.fn_contratto_sovrapposto(
        (SELECT ba_id FROM tmp_succ_ctx),
        (SELECT istanza_utility_id FROM tmp_succ_ctx),
        (SELECT utility_id FROM tmp_succ_ctx),
        'COMMODITY',
        '2082-05-01'::date, '2082-06-01'::date
    ),
    NULL::bigint,
    '5) ignora contratti abortiti -> NULL'
);

-- ============================================================
-- 6) Perpetuo (valido_al NULL) intercettato -> id C_PERP
-- ============================================================
SELECT is(
    vendite.fn_contratto_sovrapposto(
        (SELECT ba_id FROM tmp_succ_ctx),
        (SELECT istanza_utility_id FROM tmp_succ_ctx),
        (SELECT utility_id FROM tmp_succ_ctx),
        'COMMODITY',
        '2115-01-01'::date, '2115-12-31'::date
    ),
    (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_SUCC_PERP'),
    '6) contratto perpetuo (valido_al NULL) intercettato via COALESCE simmetrico'
);

-- ============================================================
-- 7) fn_chiudi date valide -> ritorna nuovo_valido_dal - 1
-- ============================================================
SELECT is(
    vendite.fn_chiudi_contratto_per_successione(
        (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_SUCC_SUCC'),
        '2100-07-01'::date
    ),
    '2100-06-30'::date,
    '7) fn_chiudi date valide -> ritorna nuovo_valido_dal - 1'
);

-- ============================================================
-- 8) fn_chiudi date valide -> valido_al aggiornato sul contratto
-- ============================================================
SELECT is(
    (SELECT valido_al FROM vendite.contratti WHERE numero = 'PGTAP_SUCC_SUCC'),
    '2100-06-30'::date,
    '8) fn_chiudi date valide -> valido_al accorciato sul contratto'
);

-- ============================================================
-- 9) fn_chiudi data invalida -> throws E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_chiudi_contratto_per_successione(%s, '2102-01-01'::date)$q$,
        (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_SUCC_BAD')
    ),
    'P0001', NULL,
    '9) fn_chiudi data invalida -> throws E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA'
);

-- ============================================================
-- 10) fn_chiudi data invalida -> contratto invariato
-- ============================================================
SELECT is(
    (SELECT valido_al FROM vendite.contratti WHERE numero = 'PGTAP_SUCC_BAD'),
    '2102-12-31'::date,
    '10) fn_chiudi data invalida -> valido_al invariato'
);

-- ============================================================
-- 11) fn_chiudi su contratto ATTIVO -> accorciamento consentito (lock non scatta)
-- ============================================================
SELECT is(
    vendite.fn_chiudi_contratto_per_successione(
        (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_SUCC_ATT'),
        '2104-07-01'::date
    ),
    '2104-06-30'::date,
    '11) fn_chiudi su ATTIVO -> accorciamento consentito (regressione lock post-attivazione)'
);

-- ============================================================
-- 12) fn_chiudi su contratto ATTIVO -> valido_al aggiornato
-- ============================================================
SELECT is(
    (SELECT valido_al FROM vendite.contratti WHERE numero = 'PGTAP_SUCC_ATT'),
    '2104-06-30'::date,
    '12) fn_chiudi su ATTIVO -> valido_al accorciato sul contratto'
);

SELECT * FROM finish();
ROLLBACK;
