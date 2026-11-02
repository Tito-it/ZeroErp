-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'ADESIONE, il quarto tipo di riga di contratto e di offerta (changeSet
--       20261029-36 … -43, brief-db-contratto-righe-periodiche-in-commessa §6.10,
--       Lotto 4). Decisione G-0-ter di Tid (2026-10-28): il cliente prende un
--       articolo DEL listino al prezzo DEL listino (con la variazione globale);
--       sulla riga solo quantita' e periodicita'.
--
-- ⭐ TUTTO COSTRUITO: mondo cliente, listino con A e B, X fuori listino, un
--   contratto e un'offerta in bozza sul listino (builder dbops.fn_pgtap_*).
-- ⚠️ I codici si leggono dai canali dell'eccezione (CONSTRAINT = codice o nome del
--   vincolo, COLUMN = campo), non dalla frase.
--
-- Indice test (1..13):
--   La forma
--    1) l'enum ha ADESIONE
--   La riga
--    2) contratto: ADESIONE su A (nel listino) accettata
--    3) …senza prezzo, con l'erogazione ereditata dall'articolo
--    4) ADESIONE col prezzo: rifiutata dal CHECK del prezzo per tipo
--    5) OVERRIDE sullo stesso articolo: rifiutato (una sola fra OVERRIDE, ESCLUSIONE, ADESIONE)
--    6) ADESIONE su X (fuori listino): E_RIGA_ECCEZIONE_FUORI_LISTINO / articolo_id
--   L'anteprima delle righe
--    7) la riga di A: origine ADESIONE, azioni MODIFICA e RIMUOVI_ADESIONE
--    8) …al prezzo del listino
--    9) la riga di B (senza eccezioni) offre ADERISCI
--   Il listino
--   10) l'ADESIONE ferma la rimozione del listino, come le altre righe di listino
--   L'offerta
--   11) offerta: ADESIONE su A accettata
--   12) le righe espanse dell'offerta portano il tipo ADESIONE al prezzo del listino
--   Il prezzo
--   13) contratto attivo: il resolver da' ad A il prezzo del listino (CONTRATTO_LISTINO)
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_ade_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('adesione');

CREATE TEMP TABLE tmp_ade_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_ade_mondo), 'adesione');

CREATE TEMP TABLE tmp_ade_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-ADE-' || v.sigla,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_ade_listino)) AS id
  FROM (VALUES ('A'), ('B'), ('X')) AS v(sigla);

CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
    SELECT id FROM tmp_ade_art WHERE sigla = p_sigla;
$fx$;

DO $fx$ BEGIN
    PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(
        (SELECT listino_versione_id FROM tmp_ade_listino),
        ARRAY[pg_temp.art('A'), pg_temp.art('B')], 100);
END $fx$;

CREATE TEMP TABLE tmp_ade_ctr AS
SELECT k.contratto_id AS id
  FROM dbops.fn_pgtap_crea_contratto(
           'adesione', 'DRAFT', (SELECT billing_account_id FROM tmp_ade_mondo), NULL,
           script.fn_data_operativa(), script.fn_data_operativa() + 365, NULL,
           (SELECT listino_id FROM tmp_ade_listino)) k;

CREATE TEMP TABLE tmp_ade_off AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali
           (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
            utility_id, listino_id, validita_dal)
    SELECT 'PGTAP-ADE-O-' || substr(gen_random_uuid()::text, 1, 8),
           m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
           m.utility_id, l.listino_id, script.fn_data_operativa()
      FROM tmp_ade_mondo m, tmp_ade_listino l
    RETURNING id)
SELECT id FROM ins;

-- Scopo: la quantita' di una riga che eredita dall'articolo: 2 se la fonte di
--   default la porta (FISSA), altrimenti vuota (fonte a valle).
CREATE OR REPLACE FUNCTION pg_temp.qta(p_articolo uuid)
RETURNS numeric LANGUAGE sql STABLE AS $fx$
    SELECT 2::numeric FROM vendite.fn_articolo_erogazioni(p_articolo) e
     WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA';
$fx$;

-- Scopo: l'INSERT di una riga come testo. p_prezzo NULL = senza prezzo.
CREATE OR REPLACE FUNCTION pg_temp.ins(p_doc text, p_sigla text, p_tipo text,
                                       p_prezzo numeric DEFAULT NULL)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT format(
        $$INSERT INTO vendite.%I (%I, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa)
          VALUES (%s, %L, %L, %s, %s)$$,
        CASE p_doc WHEN 'contratto' THEN 'contratti_righe' ELSE 'offerte_commerciali_eccezioni' END,
        CASE p_doc WHEN 'contratto' THEN 'contratto_id' ELSE 'offerta_id' END,
        CASE p_doc WHEN 'contratto' THEN (SELECT id FROM tmp_ade_ctr) ELSE (SELECT id FROM tmp_ade_off) END,
        pg_temp.art(p_sigla), p_tipo,
        coalesce(p_prezzo::text, 'NULL'),
        coalesce(pg_temp.qta(pg_temp.art(p_sigla))::text, 'NULL'));
$fx$;

-- Scopo: i due canali strutturati di uno statement (CONSTRAINT, COLUMN).
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
-- 1) La forma
-- ============================================================
SELECT ok('ADESIONE' = ANY (enum_range(NULL::vendite.tipo_eccezione_contratto)::text[]),
    '1) vendite.tipo_eccezione_contratto ha ADESIONE');

-- ============================================================
-- 2-6) La riga
-- ============================================================
SELECT is(pg_temp.canali(pg_temp.ins('contratto', 'A', 'ADESIONE')), 'NESSUN ERRORE',
    '2) contratto: ADESIONE su A (nel listino) accettata');

-- ⚠️ La riga deve esserci: senza, il confronto sarebbe NULL e il test rosso per sottrazione.
SELECT is(
    (SELECT coalesce(r.prezzo_unitario::text, 'NULL') || '/' || (r.tipo_erogazione IS NOT NULL)::text
       FROM vendite.contratti_righe r
      WHERE r.contratto_id = (SELECT id FROM tmp_ade_ctr) AND r.articolo_id = pg_temp.art('A')),
    'NULL/true',
    '3) …senza prezzo, con l''erogazione ereditata dall''articolo');

SELECT is(pg_temp.canali(pg_temp.ins('contratto', 'B', 'ADESIONE', 80)),
    'chk_contrighe_prezzo_per_tipo_eccezione / -',
    '4) ADESIONE col prezzo: rifiutata (il prezzo e'' quello del listino)');

SELECT is(pg_temp.canali(pg_temp.ins('contratto', 'A', 'OVERRIDE', 80)),
    'uq_contrighe_one_eccezione_per_articolo / -',
    '5) OVERRIDE su A, che ha gia'' l''ADESIONE: rifiutato (una sola fra OVERRIDE, ESCLUSIONE e ADESIONE)');

SELECT is(pg_temp.canali(pg_temp.ins('contratto', 'X', 'ADESIONE')),
    'E_RIGA_ECCEZIONE_FUORI_LISTINO / articolo_id',
    '6) ADESIONE su X, fuori listino: rifiutata col campo articolo_id');

-- ============================================================
-- 7-9) L'anteprima delle righe
-- ============================================================
SELECT is(
    (SELECT p.origine || '|' || array_to_string(p.azioni, ',')
       FROM vendite.fn_documento_righe_preview('CONTRATTO', (SELECT id FROM tmp_ade_ctr)) p
      WHERE p.articolo_id = pg_temp.art('A')),
    'ADESIONE|MODIFICA,RIMUOVI_ADESIONE',
    '7) anteprima: la riga di A e'' un''ADESIONE, si modifica o si toglie');

SELECT is(
    (SELECT p.prezzo_finale = p.prezzo_listino AND p.prezzo_listino = 100
       FROM vendite.fn_documento_righe_preview('CONTRATTO', (SELECT id FROM tmp_ade_ctr)) p
      WHERE p.articolo_id = pg_temp.art('A')),
    true,
    '8) …al prezzo del listino');

SELECT ok(
    (SELECT 'ADERISCI' = ANY (p.azioni)
       FROM vendite.fn_documento_righe_preview('CONTRATTO', (SELECT id FROM tmp_ade_ctr)) p
      WHERE p.articolo_id = pg_temp.art('B')),
    '9) la riga di B, senza eccezioni, offre ADERISCI');

-- ============================================================
-- 10) Il listino
-- ============================================================
SELECT is(
    script.fn_check_listino_cambiabile('CONTRATTO', (SELECT id FROM tmp_ade_ctr),
        (SELECT listino_id FROM tmp_ade_listino), NULL) -> 0 ->> 'codice',
    'E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI',
    '10) l''ADESIONE vive sul listino: ne ferma la rimozione');

-- ============================================================
-- 11-12) L'offerta
-- ============================================================
SELECT is(pg_temp.canali(pg_temp.ins('offerta', 'A', 'ADESIONE')), 'NESSUN ERRORE',
    '11) offerta: ADESIONE su A accettata');

SELECT is(
    (SELECT e.tipo_eccezione::text || '|' || (e.prezzo_unitario = 100)::text
       FROM vendite.fn_offerta_righe_espanse((SELECT id FROM tmp_ade_off)) e
      WHERE e.articolo_id = pg_temp.art('A')),
    'ADESIONE|true',
    '12) le righe espanse dell''offerta: A e'' un''ADESIONE, al prezzo del listino');

-- ============================================================
-- 13) Il prezzo, dal resolver, sul contratto attivo
-- ============================================================
DO $fx$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, (SELECT id FROM tmp_ade_ctr), 'ATTIVO');
END $fx$;

SELECT is(
    (SELECT r.origine || '|' || (r.prezzo_finale = 100)::text
       FROM vendite.fn_resolve_prezzo_listino_v2(
           pg_temp.art('A'),
           (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = pg_temp.art('A')),
           script.fn_data_operativa(),
           (SELECT billing_account_id FROM tmp_ade_mondo),
           (SELECT utility_id FROM tmp_ade_mondo),
           (SELECT emittente_soggetto_ruolo_id FROM tmp_ade_mondo),
           NULL) r),
    'CONTRATTO_LISTINO|true',
    '13) contratto attivo: il resolver da'' ad A il prezzo del listino, non quello vuoto della riga');

SELECT * FROM finish();
ROLLBACK;
