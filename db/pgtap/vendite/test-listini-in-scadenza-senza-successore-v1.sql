-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: «versione in scadenza senza successore», la regola in UNA sede.
--   vendite.fn_listini_in_scadenza_senza_successore (20261031-27) e il suo
--   parametro LISTINI_SCADENZA_PREAVVISO_GIORNI (seed config/parameters.csv).
--   Brief: brief-db-liste-datatable-grezze-secondo-giro §3.1.
--
-- ⭐ TUTTO COSTRUITO: mondo e listini dai builder dbops.fn_pgtap_crea_*, i
--   successori scritti qui. N non si assume: si legge dal parametro con la
--   stessa cascata della funzione, e le date si costruiscono attorno a N. Vale
--   anche su un DB ricostruito da zero, come in CI.
--
-- I LISTINI COSTRUITI (oggi = la data operativa, N = il preavviso):
--   L1  versione ATTIVA fino a oggi+N, nessun successore            → in scadenza
--   L2  versione ATTIVA fino a oggi+N+1                             → fuori finestra
--   L3  fino a oggi+N, successore in BOZZA dal giorno dopo          → coperto
--   L4  fino a oggi+N, successore ATTIVO dal giorno dopo            → coperto
--   L5  fino a oggi+N, BOZZA che nasce PRIMA della fine             → non e' un successore
--
-- Indice test (1..9):
--    1) la funzione: STABLE, non STRICT, SECURITY INVOKER; EXECUTE all'app, non a PUBLIC
--    2) il parametro c'e' ed e' un intero positivo
--    3) L1 e' in scadenza, coi giorni rimanenti = N
--    4) L2 non e' in scadenza: la fine cade il giorno dopo la finestra
--    5) L3 non e' in scadenza: il successore in preparazione lo copre
--    6) L4 non e' in scadenza: il successore operativo lo copre
--    7) L5 e' in scadenza: una bozza che nasce prima della fine non subentra
--    8) a una data diversa da oggi i giorni rimanenti si contano da quella data
--    9) una riga per versione: nessun listino della fixture esce due volte
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_lss_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('in scadenza');

-- N con la stessa cascata della funzione: il test non assume il seed.
CREATE TEMP TABLE tmp_lss_n AS
SELECT script.fn_intero_positivo_da_testo(
           script.fn_get_parameter_di_sessione('LISTINI_SCADENZA_PREAVVISO_GIORNI', 'pgtap'),
           'LISTINI_SCADENZA_PREAVVISO_GIORNI', 'pgtap') AS n,
       script.fn_data_operativa() AS oggi;

-- Scopo: un listino della fixture con la versione ATTIVA dal builder, che
--   finisce a oggi + N + p_scarto.
CREATE OR REPLACE FUNCTION pg_temp.listino(p_etichetta text, p_scarto integer)
RETURNS TABLE(listino_id bigint, listino_versione_id bigint, tipologia_id smallint)
LANGUAGE sql AS $fx$
  SELECT * FROM dbops.fn_pgtap_crea_listino(
      (SELECT utility_id FROM tmp_lss_mondo), p_etichetta,
      (SELECT oggi - 10 FROM tmp_lss_n),
      (SELECT oggi + n + p_scarto FROM tmp_lss_n));
$fx$;

CREATE TEMP TABLE tmp_lss_l AS
SELECT 'L1'::text AS nome, * FROM pg_temp.listino('in scadenza L1', 0)
UNION ALL SELECT 'L2', * FROM pg_temp.listino('in scadenza L2', 1)
UNION ALL SELECT 'L3', * FROM pg_temp.listino('in scadenza L3', 0)
UNION ALL SELECT 'L4', * FROM pg_temp.listino('in scadenza L4', 0)
UNION ALL SELECT 'L5', * FROM pg_temp.listino('in scadenza L5', 0);

-- Scopo: una versione in BOZZA del listino p_nome, che nasce p_dal.
CREATE OR REPLACE FUNCTION pg_temp.bozza(p_nome text, p_dal date)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
  SELECT listino_id, 'PGTAP_LSS_' || p_nome || '_SUCC', p_dal FROM tmp_lss_l WHERE nome = p_nome
  RETURNING id;
$fx$;

-- L3 e L4: il successore contiguo, il giorno dopo la fine. L5: una bozza che
-- nasce dentro la versione in vigore.
CREATE TEMP TABLE tmp_lss_succ AS
SELECT 'L3'::text AS nome, pg_temp.bozza('L3', (SELECT oggi + n + 1 FROM tmp_lss_n)) AS id
UNION ALL SELECT 'L4', pg_temp.bozza('L4', (SELECT oggi + n + 1 FROM tmp_lss_n))
UNION ALL SELECT 'L5', pg_temp.bozza('L5', (SELECT oggi FROM tmp_lss_n));

-- L4: il successore diventa ATTIVO. Una versione si attiva solo con un prezzo.
CREATE TEMP TABLE tmp_lss_art AS
SELECT dbops.fn_pgtap_crea_articolo(
           'PGTAP_LSS_ART_' || substr(md5(clock_timestamp()::text || random()::text), 1, 12),
           false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_lss_l WHERE nome = 'L4')) AS id;

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
           (SELECT id FROM tmp_lss_succ WHERE nome = 'L4'), ARRAY[(SELECT id FROM tmp_lss_art)], 100);
SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni',
           (SELECT id FROM tmp_lss_succ WHERE nome = 'L4'), 'ATTIVA');

-- Scopo: il risultato della funzione per il listino p_nome alla data p_data
--   (NULL = la data operativa): i giorni rimanenti, NULL se non e' in scadenza.
CREATE OR REPLACE FUNCTION pg_temp.giorni(p_nome text, p_data date DEFAULT NULL)
RETURNS integer LANGUAGE sql STABLE AS $fx$
  SELECT s.giorni_rimanenti
    FROM vendite.fn_listini_in_scadenza_senza_successore(p_data) s
    JOIN tmp_lss_l l ON l.listino_id = s.listino_id AND l.listino_versione_id = s.versione_id
   WHERE l.nome = p_nome;
$fx$;

-- ============================================================
-- 1..2 — forma
-- ============================================================
SELECT ok(
    (SELECT provolatile = 's' AND NOT proisstrict AND NOT prosecdef
            AND has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')
            AND NOT has_function_privilege('public', p.oid, 'EXECUTE')
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_listini_in_scadenza_senza_successore(date)'::regprocedure),
    '1) fn_listini_in_scadenza_senza_successore: STABLE, non STRICT, SECURITY INVOKER; EXECUTE all''app, non a PUBLIC');

SELECT ok((SELECT n >= 1 FROM tmp_lss_n),
    '2) LISTINI_SCADENZA_PREAVVISO_GIORNI c''e'' ed e'' un intero positivo');

-- ============================================================
-- 3..7 — la regola
-- ============================================================
SELECT is(pg_temp.giorni('L1'), (SELECT n FROM tmp_lss_n),
    '3) L1 (fine a oggi+N, nessun successore) e'' in scadenza, coi giorni rimanenti = N');

SELECT is(pg_temp.giorni('L2'), NULL::integer,
    '4) L2 (fine a oggi+N+1) non e'' in scadenza: la fine cade fuori dalla finestra');

SELECT is(pg_temp.giorni('L3'), NULL::integer,
    '5) L3 non e'' in scadenza: il successore in preparazione (BOZZA dal giorno dopo) lo copre');

SELECT is(pg_temp.giorni('L4'), NULL::integer,
    '6) L4 non e'' in scadenza: il successore operativo (ATTIVA dal giorno dopo) lo copre');

SELECT is(pg_temp.giorni('L5'), (SELECT n FROM tmp_lss_n),
    '7) L5 e'' in scadenza: una bozza che nasce prima della fine non e'' un successore');

-- ============================================================
-- 8..9 — la data e la grana
-- ============================================================
SELECT is(pg_temp.giorni('L1', (SELECT oggi + 1 FROM tmp_lss_n)), (SELECT n - 1 FROM tmp_lss_n),
    '8) a domani L1 ha un giorno in meno: i giorni si contano dalla data chiesta');

SELECT is(
    (SELECT count(*)::integer
       FROM vendite.fn_listini_in_scadenza_senza_successore() s
       JOIN tmp_lss_l l ON l.listino_id = s.listino_id),
    2,
    '9) una riga per versione: della fixture escono L1 e L5, una volta ciascuno');

SELECT * FROM finish();
ROLLBACK;
