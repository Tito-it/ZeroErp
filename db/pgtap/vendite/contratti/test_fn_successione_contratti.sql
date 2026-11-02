-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): il mondo si costruisce
--   (dbops.fn_pgtap_crea_mondo_cliente) e i contratti nascono da
--   dbops.fn_pgtap_crea_contratto col periodo e il listino del test; prima il
--   BA era «il primo del database» e su un database ricostruito da zero la
--   fixture restava vuota. I casi ritrovano i contratti per nome in tmp_succ_k
--   (il numero lo da' la madre), non per numero.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i contratti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano
--   gia' ATTIVO o abortiti). Un contratto si attiva su un listino con una
--   versione in vigore: gli ATTIVO lo prendono da dbops.fn_pgtap_crea_listino.
--
-- Fixture: un solo billing_account, finestre temporali disgiunte (nessun
-- conflitto con ex_contratti_no_overlap), emittente coerente con il BA.
-- ------------------------------------------------------------

BEGIN;

-- ⭐ rev 2026-10-24 (Q-4): il mondo si COSTRUISCE — azienda, operatore,
--   contesto aperto su di lui, un cliente con il suo BA legato a quella
--   azienda. Prima il contesto era nudo e il BA era «il primo del database
--   con un emittente»: su un database ricostruito da zero non c'e', la
--   fixture restava VUOTA e i casi 3-6 passavano per sottrazione (NULL = NULL).
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('SUCC');

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(12);

-- ============================================================
-- Setup fixture
-- ============================================================
CREATE TEMP TABLE tmp_succ_ctx AS
SELECT
    m.billing_account_id  AS ba_id,
    m.istanza_utility_id  AS istanza_utility_id,
    m.utility_id          AS utility_id,
    -- lo stato abortito si raggiunge per la matrice: il codice, non l'id
    (SELECT codice_interno FROM config.stati_doc_contratti WHERE is_abortito IS TRUE ORDER BY id LIMIT 1) AS cod_abortito
  FROM tmp_mondo m;

-- Il listino dei contratti ATTIVO: DRAFT->ATTIVO congela la versione in
-- vigore (trgfn_contratti_freeze_listino_versione); senza listino il
-- contratto vorrebbe righe AGGIUNTA con prezzo. Uno solo per i tre ATTIVO.
CREATE TEMP TABLE tmp_succ_listino AS
SELECT l.listino_id
  FROM tmp_succ_ctx c,
       LATERAL dbops.fn_pgtap_crea_listino(c.utility_id, 'successione contratti') l;

-- ⭐ rev 2026-10-24 (Q-4, R-3): i contratti nascono dal builder
--   (dbops.fn_pgtap_crea_contratto: madre vendite.fn_create_contratto,
--   periodo e listino del test, stato per la matrice), sul BA del mondo.
--   Il numero lo da' la madre: i casi li ritrovano per NOME in tmp_succ_k,
--   non piu' per un numero scritto a mano ('PGTAP_SUCC_*').
CREATE TEMP TABLE tmp_succ_k (nome text PRIMARY KEY, contratto_id bigint NOT NULL);

-- C_A: ATTIVO, finestra 2080 (incumbent per il test di overlap)
-- ⭐ ATTIVO e non DRAFT, ed e' la correzione del 2026-08-24: dal changeSet
--    20260602-18 («Overlap contratti: escludere i DRAFT dal vincolo») la
--    partecipazione all'overlap e' decisa dalla colonna GENERATED
--    `partecipa_overlap_snapshot = NOT is_abortito AND NOT is_draft`. Un
--    incumbent in bozza non blocca nessuno — di proposito — e il test 3
--    misurava quindi il caso sbagliato: NULL invece dell'id.
INSERT INTO tmp_succ_k
SELECT 'A', k.contratto_id
  FROM tmp_succ_ctx c, tmp_succ_listino l,
       LATERAL dbops.fn_pgtap_crea_contratto('SUCC-A', 'ATTIVO', c.ba_id, NULL,
                 DATE '2080-01-01', DATE '2080-12-31', NULL, l.listino_id) k;

-- C_ABORT: stato abortito, finestra 2082 (deve essere ignorato dal rilevamento)
INSERT INTO tmp_succ_k
SELECT 'ABORT', k.contratto_id
  FROM tmp_succ_ctx c,
       LATERAL dbops.fn_pgtap_crea_contratto('SUCC-ABORT', c.cod_abortito, c.ba_id, NULL,
                 DATE '2082-01-01', DATE '2082-12-31') k;

-- C_SUCC: DRAFT, finestra 2100 (per fn_chiudi date valide)
INSERT INTO tmp_succ_k
SELECT 'SUCC', k.contratto_id
  FROM tmp_succ_ctx c,
       LATERAL dbops.fn_pgtap_crea_contratto('SUCC-SUCC', 'DRAFT', c.ba_id, NULL,
                 DATE '2100-01-01', DATE '2100-12-31') k;

-- C_BAD: DRAFT, finestra 2102-06.. (per fn_chiudi data invalida)
INSERT INTO tmp_succ_k
SELECT 'BAD', k.contratto_id
  FROM tmp_succ_ctx c,
       LATERAL dbops.fn_pgtap_crea_contratto('SUCC-BAD', 'DRAFT', c.ba_id, NULL,
                 DATE '2102-06-01', DATE '2102-12-31') k;

-- C_ATT: ATTIVO, finestra 2104 (regressione lock post-attivazione)
INSERT INTO tmp_succ_k
SELECT 'ATT', k.contratto_id
  FROM tmp_succ_ctx c, tmp_succ_listino l,
       LATERAL dbops.fn_pgtap_crea_contratto('SUCC-ATT', 'ATTIVO', c.ba_id, NULL,
                 DATE '2104-01-01', DATE '2104-12-31', NULL, l.listino_id) k;

-- C_PERP: ATTIVO, perpetuo 2110.. (valido_al NULL)
-- ⭐ ATTIVO per la stessa ragione di C_A: un perpetuo in bozza non partecipa
--    all'overlap, e il test 6 misurerebbe il caso sbagliato.
INSERT INTO tmp_succ_k
SELECT 'PERP', k.contratto_id
  FROM tmp_succ_ctx c, tmp_succ_listino l,
       LATERAL dbops.fn_pgtap_crea_contratto('SUCC-PERP', 'ATTIVO', c.ba_id, NULL,
                 DATE '2110-01-01', NULL, NULL, l.listino_id) k;

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
    (SELECT contratto_id FROM tmp_succ_k WHERE nome = 'A'),
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
    (SELECT contratto_id FROM tmp_succ_k WHERE nome = 'PERP'),
    '6) contratto perpetuo (valido_al NULL) intercettato via COALESCE simmetrico'
);

-- ============================================================
-- 7) fn_chiudi date valide -> ritorna nuovo_valido_dal - 1
-- ============================================================
SELECT is(
    vendite.fn_chiudi_contratto_per_successione(
        (SELECT contratto_id FROM tmp_succ_k WHERE nome = 'SUCC'),
        '2100-07-01'::date
    ),
    '2100-06-30'::date,
    '7) fn_chiudi date valide -> ritorna nuovo_valido_dal - 1'
);

-- ============================================================
-- 8) fn_chiudi date valide -> valido_al aggiornato sul contratto
-- ============================================================
SELECT is(
    (SELECT valido_al FROM vendite.contratti WHERE id = (SELECT contratto_id FROM tmp_succ_k WHERE nome = 'SUCC')),
    '2100-06-30'::date,
    '8) fn_chiudi date valide -> valido_al accorciato sul contratto'
);

-- ============================================================
-- 9) fn_chiudi data invalida -> throws E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_chiudi_contratto_per_successione(%s, '2102-01-01'::date)$q$,
        (SELECT contratto_id FROM tmp_succ_k WHERE nome = 'BAD')
    ),
    'P0001', NULL,
    '9) fn_chiudi data invalida -> throws E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA'
);

-- ============================================================
-- 10) fn_chiudi data invalida -> contratto invariato
-- ============================================================
SELECT is(
    (SELECT valido_al FROM vendite.contratti WHERE id = (SELECT contratto_id FROM tmp_succ_k WHERE nome = 'BAD')),
    '2102-12-31'::date,
    '10) fn_chiudi data invalida -> valido_al invariato'
);

-- ============================================================
-- 11) fn_chiudi su contratto ATTIVO -> accorciamento consentito (lock non scatta)
-- ============================================================
SELECT is(
    vendite.fn_chiudi_contratto_per_successione(
        (SELECT contratto_id FROM tmp_succ_k WHERE nome = 'ATT'),
        '2104-07-01'::date
    ),
    '2104-06-30'::date,
    '11) fn_chiudi su ATTIVO -> accorciamento consentito (regressione lock post-attivazione)'
);

-- ============================================================
-- 12) fn_chiudi su contratto ATTIVO -> valido_al aggiornato
-- ============================================================
SELECT is(
    (SELECT valido_al FROM vendite.contratti WHERE id = (SELECT contratto_id FROM tmp_succ_k WHERE nome = 'ATT')),
    '2104-06-30'::date,
    '12) fn_chiudi su ATTIVO -> valido_al accorciato sul contratto'
);

SELECT * FROM finish();
ROLLBACK;
