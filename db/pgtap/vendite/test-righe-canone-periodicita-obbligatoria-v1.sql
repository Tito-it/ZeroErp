-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: una riga a canone di contratto o di offerta dice ogni quanto si addebita.
--   changeSet 20261101-04 (CHECK), -05 (guard script.trgfn_righe_guard_periodicita_canone),
--   -06 (montaggi). Brief: brief-db-contratto-righe-periodiche-in-commessa §6.11 (passo 4).
--   Decisioni di Tid: G-0-bis (2026-10-28), F-9 e la (b) del Lotto 4b (2026-10-29: l'obbligo
--   entra col passaggio BE/FE, quando il form la chiede).
--
-- ⭐ TUTTO COSTRUITO: cliente, articoli, contratto e offerta nascono qui. Il contratto e'
--   SENZA listino: ogni riga e' un'AGGIUNTA, che la periodicita' non la
--   eredita (F-9); l'offerta ha un listino vuoto, perche' la testata lo pretende. Il
--   default dal listino di ADESIONE e OVERRIDE ha il suo pgTAP,
--   vendite/test-righe-periodicita-da-listino-v1.
--   Q: articolo di quota fissa (si eroga a CANONE/FISSA). S: articolo senza tipologia, di
--   natura MERCE (UNA_TANTUM/FISSA di default): decide la natura.
--
-- ⛔ COSA PRESIDIA:
--   · la regola e' nella struttura delle due tabelle (CHECK): presidia le strade senza
--     trigger. Senza un'asserzione sua, toglierlo passerebbe inosservato;
--   · il guard e' montato sulle due, e DOPO il default dal listino (l'ordine e' il nome);
--   · la riga a canone senza periodicita' si rifiuta col CODICE e col CAMPO, non col 23514;
--   · un UPDATE che la toglie si rifiuta;
--   · la regola e' del solo canone: una una tantum senza periodicita' si salva.
--
-- Indice test (1..14):
--    1) CHECK sul contratto: CANONE vuole la periodicita'
--    2) CHECK sull'offerta: lo stesso
--    3) guard montato sul contratto: BEFORE INSERT OR UPDATE OF tipo_erogazione, periodicita
--    4) guard montato sull'offerta: lo stesso
--    5) l'ordine: su tutte e due il guard viene dopo il default della periodicita' e il perimetro
--    6) contratto: AGGIUNTA a canone senza periodicita' rifiutata
--    7) contratto: canale CONSTRAINT = il codice di dominio
--    8) contratto: canale COLUMN = periodicita
--    9) contratto: AGGIUNTA a canone con la periodicita' accettata
--   10) contratto: togliere la periodicita' a quella riga e' rifiutato
--   11) contratto: AGGIUNTA a una tantum senza periodicita' accettata
--   12) offerta: AGGIUNTA a canone senza periodicita' rifiutata
--   13) offerta: canali CONSTRAINT / COLUMN
--   14) offerta: con la periodicita' accettata, e toglierla e' rifiutato
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_cpo_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('canone periodicita obbligatoria');

CREATE TEMP TABLE tmp_cpo_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-CPO-' || v.sigla,
           p_listino_tipologia_id => (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = v.tipologia)) AS id
  FROM (VALUES ('Q', 'QUOTA_FISSA'), ('S', NULL)) AS v(sigla, tipologia);

CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
    SELECT id FROM tmp_cpo_art WHERE sigla = p_sigla;
$fx$;

CREATE TEMP TABLE tmp_cpo_ctr AS
SELECT k.contratto_id AS id
  FROM dbops.fn_pgtap_crea_contratto(
           'canone periodicita obbligatoria', 'DRAFT', (SELECT billing_account_id FROM tmp_cpo_mondo), NULL,
           script.fn_data_operativa(), script.fn_data_operativa() + 365, NULL, NULL) k;

CREATE TEMP TABLE tmp_cpo_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_cpo_mondo), 'canone periodicita obbligatoria');

CREATE TEMP TABLE tmp_cpo_off AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali
           (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
            utility_id, listino_id, validita_dal)
    SELECT 'PGTAP-CPO-O-' || substr(gen_random_uuid()::text, 1, 8),
           m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
           m.utility_id, (SELECT listino_id FROM tmp_cpo_listino), script.fn_data_operativa()
      FROM tmp_cpo_mondo m
    RETURNING id)
SELECT id FROM ins;

-- Scopo: l'INSERT di un'AGGIUNTA sul documento, come testo (per lives_ok / throws_like).
CREATE OR REPLACE FUNCTION pg_temp.ins(p_doc text, p_sigla text, p_erogazione text,
                                       p_periodicita text)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT CASE WHEN p_doc = 'contratto' THEN format(
        $$INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,
                 prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, qta_operativa, periodicita)
          VALUES (%s, %L, 'AGGIUNTA', 80, %L, 'FISSA', 1, %L)$$,
        (SELECT id FROM tmp_cpo_ctr), pg_temp.art(p_sigla), p_erogazione, p_periodicita)
    ELSE format(
        $$INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
                 prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, qta_operativa, periodicita)
          VALUES (%s, %L, 'AGGIUNTA', 80, %L, 'FISSA', 1, %L)$$,
        (SELECT id FROM tmp_cpo_off), pg_temp.art(p_sigla), p_erogazione, p_periodicita)
    END;
$fx$;

-- Scopo: i due canali dell'errore che il backend legge, CONSTRAINT / COLUMN.
--   ⚠️ Si leggono tutti e due: un guard che scrivesse il campo sbagliato nel contesto
--   lascerebbe la frase giusta e il campo vuoto.
CREATE OR REPLACE FUNCTION pg_temp.canali(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-') || ' / ' || coalesce(nullif(v_col, ''), '-');
    END;
END;
$fx$;

-- ============================================================
-- 1..5 — la regola nella struttura, e il guard montato
-- ============================================================
SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'vendite.contratti_righe'::regclass
        AND c.conname = 'chk_contrighe_canone_periodicita'),
    'CHECK ((((tipo_erogazione)::text IS DISTINCT FROM ''CANONE''::text) OR (periodicita IS NOT NULL)))',
    '1) CHECK sul contratto: una riga CANONE vuole la periodicita''');

SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
        AND c.conname = 'chk_offerte_eccezioni_canone_periodicita'),
    'CHECK ((((tipo_erogazione)::text IS DISTINCT FROM ''CANONE''::text) OR (periodicita IS NOT NULL)))',
    '2) CHECK sull''offerta: lo stesso');

-- ⚠️ Per OID, non per testo: regclass::text perde lo schema come app.
SELECT ok(
    (SELECT count(*) = 1
            AND bool_and(t.tgtype = (1 | 2 | 4 | 16))   -- ROW, BEFORE, INSERT, UPDATE
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%BEFORE INSERT OR UPDATE OF tipo_erogazione, periodicita%')
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%(''contratto_id'')')
       FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.contratti_righe'::regclass
        AND NOT t.tgisinternal
        AND t.tgname = 'trg_contratti_righe_a10_guard_periodicita_canone_ins_upd'
        AND t.tgfoid = to_regprocedure('script.trgfn_righe_guard_periodicita_canone()')),
    '3) guard montato sul contratto: _a10_, BEFORE INSERT OR UPDATE OF tipo_erogazione, periodicita');

SELECT ok(
    (SELECT count(*) = 1
            AND bool_and(t.tgtype = (1 | 2 | 4 | 16))
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%BEFORE INSERT OR UPDATE OF tipo_erogazione, periodicita%')
            AND bool_and(pg_get_triggerdef(t.oid) LIKE '%(''offerta_id'')')
       FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
        AND NOT t.tgisinternal
        AND t.tgname = 'trg_offerte_eccezioni_a10_guard_periodicita_canone_ins_upd'
        AND t.tgfoid = to_regprocedure('script.trgfn_righe_guard_periodicita_canone()')),
    '4) guard montato sull''offerta: lo stesso');

-- I BEFORE ROW scattano in ordine di nome: il guard giudica la riga dopo il default
-- della periodicita' e dopo il perimetro dell'erogazione (a una riga che non puo'
-- essere a canone parla prima lui).
SELECT ok(
    (SELECT count(*) = 4
            AND bool_and(g.tgname > d.tgname)
       FROM pg_trigger g
       JOIN pg_trigger d
         ON d.tgrelid = g.tgrelid
        AND d.tgfoid IN (to_regprocedure('script.trgfn_righe_default_periodicita_da_listino()'),
                         to_regprocedure('script.trgfn_righe_guard_erogazione_perimetro()'))
        AND NOT d.tgisinternal
        AND d.tgtype::int & 4 = 4   -- il montaggio su INSERT
      WHERE g.tgfoid = to_regprocedure('script.trgfn_righe_guard_periodicita_canone()')),
    '5) l''ordine: su tutte e due le tabelle il guard viene dopo il default della periodicita'' e dopo il perimetro');

-- ============================================================
-- 6..11 — contratto
-- ============================================================
-- ⚠️ Sul TESTO del messaggio a catalogo: il 23514 del CHECK non deve passare per questo.
SELECT throws_like(
    pg_temp.ins('contratto', 'Q', 'CANONE', NULL),
    '%Manca la periodicità%',
    '6) contratto: AGGIUNTA a canone senza periodicita'' rifiutata (F-9: la scrive l''operatore)');

CREATE TEMP TABLE tmp_cpo_canali_c AS
SELECT pg_temp.canali(pg_temp.ins('contratto', 'Q', 'CANONE', NULL)) AS canali;

SELECT is(split_part((SELECT canali FROM tmp_cpo_canali_c), ' / ', 1),
    'E_RIGA_CANONE_SENZA_PERIODICITA',
    '7) contratto: canale CONSTRAINT = il codice di dominio, non il nome del CHECK');

SELECT is(split_part((SELECT canali FROM tmp_cpo_canali_c), ' / ', 2),
    'periodicita',
    '8) contratto: canale COLUMN = il campo da accendere');

SELECT lives_ok(
    pg_temp.ins('contratto', 'Q', 'CANONE', 'TRIMESTRALE'),
    '9) contratto: AGGIUNTA a canone con la periodicita'' accettata');

SELECT throws_like(
    format($$UPDATE vendite.contratti_righe SET periodicita = NULL
              WHERE contratto_id = %s AND articolo_id = %L$$,
           (SELECT id FROM tmp_cpo_ctr), pg_temp.art('Q')),
    '%Manca la periodicità%',
    '10) contratto: togliere la periodicita'' alla riga a canone e'' rifiutato');

SELECT lives_ok(
    pg_temp.ins('contratto', 'S', 'UNA_TANTUM', NULL),
    '11) contratto: AGGIUNTA a una tantum senza periodicita'' accettata (la regola e'' del canone)');

-- ============================================================
-- 12..14 — offerta
-- ============================================================
SELECT throws_like(
    pg_temp.ins('offerta', 'Q', 'CANONE', NULL),
    '%Manca la periodicità%',
    '12) offerta: AGGIUNTA a canone senza periodicita'' rifiutata');

SELECT is(pg_temp.canali(pg_temp.ins('offerta', 'Q', 'CANONE', NULL)),
    'E_RIGA_CANONE_SENZA_PERIODICITA / periodicita',
    '13) offerta: canali CONSTRAINT / COLUMN = il codice e il campo');

-- Scopo: la riga si salva con la periodicita', e toglierla si rifiuta.
CREATE OR REPLACE FUNCTION pg_temp.offerta_con_e_senza()
RETURNS text LANGUAGE plpgsql AS $fx$
BEGIN
    EXECUTE pg_temp.ins('offerta', 'Q', 'CANONE', 'ANNUALE');
    BEGIN
        UPDATE vendite.offerte_commerciali_eccezioni SET periodicita = NULL
         WHERE offerta_id = (SELECT id FROM tmp_cpo_off) AND articolo_id = pg_temp.art('Q');
        RETURN 'TOLTA';
    EXCEPTION WHEN OTHERS THEN
        RETURN CASE WHEN SQLERRM LIKE '%Manca la periodicità%' THEN 'RIFIUTATA' ELSE SQLERRM END;
    END;
END;
$fx$;

SELECT is(pg_temp.offerta_con_e_senza(), 'RIFIUTATA',
    '14) offerta: con la periodicita'' accettata, e toglierla e'' rifiutato');

SELECT * FROM finish();
ROLLBACK;
