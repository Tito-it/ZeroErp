-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la versione di listino sul modello del documento
--   Vocabolario e matrice (20261028-03, seed -27, -28), la colonna d'id e i
--   vincoli sugli id (-04), la mappa (-06), la fn_check dell'attivazione
--   (-07), il guard di transizione sulla matrice (-08), il guard per stato
--   (-09), la nascita (-10), il lettore delle precedenti (-11), il verbo
--   dell'attivazione (-12), la chiusura a scadenza (-13) e il suo registro
--   (-05, -14), la superficie della lista (-15), la fixture (-24, -25), la
--   porta (-26); il ramo «inesistente» del verbo (-32); la porta della fine
--   di una ATTIVA (20261029-07 … -09: il caso 11 chiude V1 dall'attivazione,
--   la chiusura programmata di V2 passa dal verbo «Chiudi»).
--   Brief: brief-modello-documento-vendita §16 (giro 12; L-1 … L-5 di Tid,
--   2026-10-28).
--
-- ⭐ TUTTO COSTRUITO: mondo, listino e righe dai builder dbops.fn_pgtap_crea_*,
--   le versioni scritte qui. Vale anche su un DB ricostruito da zero.
--
-- LA STORIA DEL LISTINO COSTRUITA (oggi = data operativa):
--   V1  oggi-30 .. aperta   ATTIVA dalla fixture (con la riga d'appoggio)
--   V2  oggi    .. aperta   BOZZA, senza prezzi, poi con un prezzo: ATTIVA,
--                           e V1 si chiude a oggi-1
--   V1                      ATTIVA con la fine passata: la chiusura a
--                           scadenza la porta a CHIUSA
--   V3  oggi+30 .. aperta   BOZZA che si cancella
--
-- ⭐ Prende il posto di vendite/test-listini-versioni-guard-transizione-stato-v1
--   (ritirato nel giro: provava il guard con UPDATE diretti dello stato, che la
--   porta ora rifiuta). I suoi casi stanno qui: 3 (i passaggi della matrice), 12
--   (lo stesso stato), 15-16 (la chiusura a scadenza, anche quella che non
--   tocca), 19 (da CHIUSA non si torna ATTIVA).
--
-- Elenco test (plan 21):
--   1) il vocabolario: 1 BOZZA (iniziale), 2 ATTIVA, 3 CHIUSA (terminale)
--   2) ⛔ gli id scritti nei vincoli sono quelli di ATTIVA e CHIUSA
--   3) la matrice: BOZZA -> ATTIVA manuale con attiva_listino; ATTIVA -> CHIUSA di processo
--   4) il registro della chiusura per scadenza: ogni verbo e' una funzione
--      viva senza argomenti; la versione di listino ha il suo
--   5) la fixture: V1 ATTIVA dal verbo, con la riga d'appoggio
--   6) la nascita: una versione senza stato nasce BOZZA
--   7) ⛔ una versione non nasce ATTIVA
--   8) la superficie della lista: V2 senza prezzi, «Attiva» spento col motivo
--   9) ⛔ il verbo su V2 senza prezzi: E_LISTINO_VERSIONE_SENZA_RIGHE
--  10) l'anteprima: attivare V2 chiude V1 a oggi-1
--  11) l'attivazione: V2 ATTIVA, una versione chiusa, V1 finisce a oggi-1
--  12) ⛔ un secondo «Attiva»: E_DOC_GIA_NELLO_STATO
--  13) ⛔ di una ATTIVA non si cambia il codice: E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE
--  14) ⛔ una ATTIVA non si cancella: E_LISTINO_VERSIONE_NON_ELIMINABILE
--  15) la chiusura a scadenza porta V1 a CHIUSA
--  16) ...e non tocca V2, ATTIVA con la fine nel futuro (chiusura programmata)
--  17) ⛔ di una CHIUSA non si cambia niente, neanche la fine
--  18) una BOZZA si cancella
--  19) ⛔ da CHIUSA non si torna ATTIVA: il verbo lo chiede, la matrice lo rifiuta
--  20) ⛔ la porta: UPDATE diretto dello stato
--  21) ⛔ il verbo su una versione che non c'e' (V3 cancellata):
--      E_VENDITE_LISTINO_VERSIONE_NOT_FOUND, non un errore tecnico
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo): il builder del mondo lo riapre poi sul
-- suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(21);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('listino al modello');

CREATE TEMP TABLE t_oggi AS SELECT script.fn_data_operativa() AS d;

CREATE TEMP TABLE t_lst AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM t_mondo), 'listino al modello',
    (SELECT d - 30 FROM t_oggi), NULL::date);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'attiva_listino');

-- Scopo: il codice dello stato di una versione.
CREATE OR REPLACE FUNCTION pg_temp.stato(p_id bigint)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT s.codice_interno::text
    FROM vendite.listini_versioni lv
    JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
   WHERE lv.id = p_id;
$fx$;

-- Scopo: l'inizio del messaggio di un codice, fino al primo segnaposto, per
--   throws_like.
CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT split_part(m.messaggio, '%s', 1) || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it';
$fx$;

-- ============================================================
-- 1-4) Il modello scritto
-- ============================================================
SELECT is(
    (SELECT string_agg(s.id || ':' || s.codice_interno || ':' || s.iniziale || ':' || s.terminale, ', ' ORDER BY s.id)
       FROM config.stati_doc_listino_versioni s WHERE s.attivo),
    '1:BOZZA:true:false, 2:ATTIVA:false:false, 3:CHIUSA:false:true',
    '1) il vocabolario: 1 BOZZA iniziale, 2 ATTIVA, 3 CHIUSA terminale');

SELECT ok(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'vendite.listini_versioni'::regclass AND c.conname = 'ex_listini_versioni_no_overlap')
      LIKE format('%%ARRAY[(%s)::bigint, (%s)::bigint]%%',
                  script.fn_doc_stato_id('vendite.listini_versioni'::regclass, 'ATTIVA'),
                  script.fn_doc_stato_id('vendite.listini_versioni'::regclass, 'CHIUSA'))
    AND
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'vendite.listini_versioni'::regclass AND c.conname = 'chk_listini_versioni_chiusa_con_fine')
      LIKE format('%%<> %s)%%', script.fn_doc_stato_id('vendite.listini_versioni'::regclass, 'CHIUSA')),
    '2) l''esclusione e il CHECK della chiusa nominano gli id di ATTIVA e CHIUSA del vocabolario');

SELECT is(
    (SELECT string_agg(da.codice_interno || '>' || a.codice_interno || ':'
                       || COALESCE(t.azione_processo_codename, '-') || ':' || (t.meta ->> 'manuale'),
                       ', ' ORDER BY t.id)
       FROM config.transizioni_stati_listino_versioni t
       JOIN config.stati_doc_listino_versioni da ON da.id = t.stato_da_id
       JOIN config.stati_doc_listino_versioni a  ON a.id  = t.stato_a_id
      WHERE t.attivo),
    'BOZZA>ATTIVA:attiva_listino:true, ATTIVA>CHIUSA:-:false',
    '3) la matrice: «Attiva» manuale con attiva_listino, la chiusura di processo');

SELECT is(
    (SELECT string_agg(r.nome_tabella || '=' || COALESCE(r.verbo_chiusura, '-')
                       || CASE WHEN r.verbo_chiusura IS NOT NULL
                                    AND to_regprocedure(r.verbo_chiusura || '()') IS NULL
                               THEN '(MORTO)' ELSE '' END,
                       ', ' ORDER BY r.nome_tabella)
       FROM dbops.automazione_chiusura_scadenze r WHERE r.attivo),
    'contratti=vendite.fn_cessa_contratti_scaduti, listini_versioni=vendite.fn_chiudi_versioni_listino_scadute, '
    'preventivi=vendite.fn_chiudi_preventivi_scaduti',
    '4) il registro della chiusura per scadenza dichiara i tre verbi, vivi');

-- ============================================================
-- 5-7) La fixture e la nascita
-- ============================================================
SELECT is(
    pg_temp.stato((SELECT listino_versione_id FROM t_lst)) || ':' ||
    (SELECT count(*) FROM vendite.listini_righe r
      WHERE r.listino_versione_id = (SELECT listino_versione_id FROM t_lst) AND r.attivo),
    'ATTIVA:1',
    '5) la fixture: V1 ATTIVA dal verbo, con la riga d''appoggio');

CREATE TEMP TABLE t_v2 AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
  SELECT listino_id, 'PGTAP_V2', (SELECT d FROM t_oggi) FROM t_lst
  RETURNING id)
SELECT id FROM ins;

SELECT is(pg_temp.stato((SELECT id FROM t_v2)), 'BOZZA',
    '6) una versione senza stato nasce BOZZA');

SELECT throws_like(
    format($$INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato_doc_listino_versione_id)
             VALUES (%s, 'PGTAP_VX', DATE '2099-01-01', %s)$$,
           (SELECT listino_id FROM t_lst),
           script.fn_doc_stato_id('vendite.listini_versioni'::regclass, 'ATTIVA')),
    'Il documento %non può nascere nello stato%',
    '7) una versione non nasce ATTIVA: E_DOC_STATO_INIZIALE_NON_VALIDO');

-- ============================================================
-- 8-12) L'attivazione
-- ============================================================
SELECT is(
    (SELECT v.attivazione_blocco_reason || ':' || v.attivazione_blocco_reason_key
       FROM vendite.vw_listini_versioni_azioni v WHERE v.versione_id = (SELECT id FROM t_v2)),
    'VERSIONE_SENZA_RIGHE:vendite.listini.azione_reason.versione_senza_righe',
    '8) la superficie: «Attiva» spento su V2 senza prezzi, col motivo');

SELECT throws_like(
    format($$SELECT * FROM vendite.fn_attiva_versione_listino(%s)$$, (SELECT id FROM t_v2)),
    pg_temp.msg('E_LISTINO_VERSIONE_SENZA_RIGHE'),
    '9) il verbo su V2 senza prezzi: E_LISTINO_VERSIONE_SENZA_RIGHE');

-- Un prezzo per V2: un articolo suo.
SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT id FROM t_v2),
    ARRAY[dbops.fn_pgtap_crea_articolo('PGTAP-LMV2-' || substr(md5(random()::text), 1, 8), false,
                                       p_listino_tipologia_id => (SELECT tipologia_id FROM t_lst))]);

SELECT is(
    (SELECT string_agg(d.versione_id || ':' || d.valido_al_dopo, ', ')
       FROM vendite.fn_versioni_listino_da_chiudere((SELECT id FROM t_v2)) d),
    (SELECT listino_versione_id FROM t_lst) || ':' || ((SELECT d FROM t_oggi) - 1),
    '10) l''anteprima: attivare V2 chiude V1 il giorno prima');

CREATE TEMP TABLE t_att AS
SELECT * FROM vendite.fn_attiva_versione_listino((SELECT id FROM t_v2));

SELECT is(
    (SELECT a.stato_precedente || '>' || a.stato_nuovo || ':' || a.versioni_chiuse FROM t_att a)
    || ' V1 fino a ' ||
    (SELECT lv.valido_al FROM vendite.listini_versioni lv WHERE lv.id = (SELECT listino_versione_id FROM t_lst)),
    'BOZZA>ATTIVA:1 V1 fino a ' || ((SELECT d FROM t_oggi) - 1),
    '11) l''attivazione: V2 ATTIVA, V1 chiusa a oggi-1 nella stessa transazione');

SELECT throws_like(
    format($$SELECT * FROM vendite.fn_attiva_versione_listino(%s)$$, (SELECT id FROM t_v2)),
    'Il documento è già nello stato%',
    '12) un secondo «Attiva»: E_DOC_GIA_NELLO_STATO');

-- ============================================================
-- 13-17) Che cosa si cambia, stato per stato, e la chiusura
-- ============================================================
SELECT throws_like(
    format($$UPDATE vendite.listini_versioni SET codice_versione = 'PGTAP_V2_BIS' WHERE id = %s$$,
           (SELECT id FROM t_v2)),
    pg_temp.msg('E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE'),
    '13) di una ATTIVA non si cambia il codice: E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE');

SELECT throws_like(
    format($$DELETE FROM vendite.listini_versioni WHERE id = %s$$, (SELECT id FROM t_v2)),
    pg_temp.msg('E_LISTINO_VERSIONE_NON_ELIMINABILE'),
    '14) una ATTIVA non si cancella: E_LISTINO_VERSIONE_NON_ELIMINABILE');

-- V2 prende la fine nel futuro: una chiusura programmata, dal verbo «Chiudi»
-- (la fine di una ATTIVA cambia solo dai verbi, 20261029-07).
SELECT * FROM vendite.fn_programma_chiusura_versione_listino(
    (SELECT id FROM t_v2), (SELECT d + 10 FROM t_oggi));

CREATE TEMP TABLE t_chiuse AS SELECT vendite.fn_chiudi_versioni_listino_scadute() AS n;

SELECT is(
    pg_temp.stato((SELECT listino_versione_id FROM t_lst)) || ':' || ((SELECT n FROM t_chiuse) >= 1),
    'CHIUSA:true',
    '15) la chiusura a scadenza porta V1 (fine passata) a CHIUSA');

SELECT is(pg_temp.stato((SELECT id FROM t_v2)), 'ATTIVA',
    '16) ...e non tocca V2, ATTIVA con la fine nel futuro');

SELECT throws_like(
    format($$UPDATE vendite.listini_versioni SET valido_al = valido_al - 1 WHERE id = %s$$,
           (SELECT listino_versione_id FROM t_lst)),
    pg_temp.msg('E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE'),
    '17) di una CHIUSA non si cambia niente, neanche la fine');

CREATE TEMP TABLE t_v3 AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
  SELECT listino_id, 'PGTAP_V3', (SELECT d + 30 FROM t_oggi) FROM t_lst
  RETURNING id)
SELECT id FROM ins;

SELECT lives_ok(
    format($$DELETE FROM vendite.listini_versioni WHERE id = %s$$, (SELECT id FROM t_v3)),
    '18) una BOZZA si cancella');

-- ============================================================
-- 19) Da CHIUSA non si torna ATTIVA
-- ============================================================
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_attiva_versione_listino(%s)$$,
           (SELECT listino_versione_id FROM t_lst)),
    pg_temp.msg('E_VERSIONE_STATO_TRANSIZIONE_INVALIDA'),
    '19) «Attiva» su una CHIUSA: E_VERSIONE_STATO_TRANSIZIONE_INVALIDA');

-- ============================================================
-- 20) La porta
-- ============================================================
SELECT throws_like(
    format($$UPDATE vendite.listini_versioni SET stato_doc_listino_versione_id = %s WHERE id = %s$$,
           script.fn_doc_stato_id('vendite.listini_versioni'::regclass, 'CHIUSA'),
           (SELECT id FROM t_v2)),
    'Lo stato del documento%si cambia solo dalle sue operazioni%',
    '20) UPDATE diretto dello stato della versione: E_DOC_STATO_SOLO_DAL_VERBO');

-- ============================================================
-- 21) Il verbo su una versione che non c'e'
-- ============================================================
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_attiva_versione_listino(%s)$$, (SELECT id FROM t_v3)),
    pg_temp.msg('E_VENDITE_LISTINO_VERSIONE_NOT_FOUND'),
    '21) «Attiva» su una versione che non c''e'': E_VENDITE_LISTINO_VERSIONE_NOT_FOUND');

SELECT * FROM finish();
ROLLBACK;
