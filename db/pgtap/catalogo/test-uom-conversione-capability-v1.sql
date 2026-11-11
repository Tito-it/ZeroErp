-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la capability di una mappatura e di una conversione generale
--   (catalogo.fn_uom_conversione_capability) dice quello che il guard della
--   storia (catalogo.trgfn_uom_guard_storia) fa davvero, e le due viste di
--   dettaglio la pubblicano.
--
-- Elenco test (plan 16):
--  1) BB, inizio vuoto («da sempre») e nessuna fine: in vigore, si chiude da ieri
--  2) BB, inizio fra cinque giorni: si cancella, si spegne, si chiude dall'inizio
--  3) BB, inizio oggi: si cancella, si spegne, si chiude da oggi
--  4) BB, finita dieci giorni fa: niente, coi due motivi
--  5) BB, in vigore con una fine futura: la fine si sposta, da ieri
--  6) BB, in vigore con fine oggi: la fine si sposta ancora
--  7) vista della mappatura, riga base: niente, coi motivi della base
--  8) vista della mappatura: sulle righe non base e' il BB
--  9) vista delle conversioni: e' il BB
-- 10) mappatura: la cancellazione riesce dove puo_eliminarsi, e solo li'
-- 11) mappatura: lo spegnimento (o la riaccensione) riesce dove puo_cambiare_attivo, e solo li'
-- 12) mappatura: la fine a data_min_chiusura riesce su ogni riga che si chiude
-- 13) mappatura: la fine un giorno prima di data_min_chiusura e' rifiutata
-- 14) mappatura: su una riga che non si chiude la fine non si sposta
-- 15) conversione generale: cancellazione e spegnimento come puo_eliminarsi e puo_cambiare_attivo
-- 16) la lista catalogo.conversioni_uom legge la vista, e ogni sua colonna c'e'
--
-- Scopo:
--  - G2 (Q33, 2026-11-11): prima la vista della mappatura diceva puo_eliminarsi
--    su ogni riga non base, mentre il guard rifiuta la cancellazione di una
--    mappatura con giorni passati; e le conversioni non avevano una vista. Il
--    giudizio sta ora in un BB, che leggono guard e viste: i test 10-15 provano
--    che le due risposte non divergono, riga per riga, sulle righe costruite.
--
-- Mondo: unita', articolo, mappature e conversioni costruiti; le tipologie per
--   codice_interno. Nessuna riga di dominio esistente.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

CREATE OR REPLACE FUNCTION pg_temp.oggi() RETURNS date LANGUAGE sql STABLE AS
$fx$ SELECT script.fn_data_operativa() $fx$;

-- Scopo: la riga del BB come testo, per confronti leggibili (i booleani
--   escono t/f, come li rende concat_ws).
CREATE OR REPLACE FUNCTION pg_temp.cap(p_dal date, p_al date) RETURNS text
LANGUAGE sql STABLE AS $fx$
  SELECT concat_ws('|', c.puo_eliminarsi, c.puo_cambiare_attivo, c.puo_chiudersi,
                   coalesce((c.data_min_chiusura - pg_temp.oggi())::text, '-'),
                   coalesce((c.data_default_chiusura - pg_temp.oggi())::text, '-'),
                   coalesce(c.motivo_non_eliminabile, '-'), coalesce(c.motivo_non_chiudibile, '-'))
    FROM catalogo.fn_uom_conversione_capability(p_dal, p_al) c
$fx$;

-- Scopo: la scrittura riesce? La si esegue e la si annulla sempre (l'eccezione
--   PGTCAP_OK riporta indietro il blocco), cosi' una prova non cambia il mondo
--   della prova dopo.
CREATE OR REPLACE FUNCTION pg_temp.riesce(p_sql text) RETURNS boolean
LANGUAGE plpgsql AS $fx$
BEGIN
    EXECUTE p_sql;
    RAISE EXCEPTION 'PGTCAP_OK';
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM = 'PGTCAP_OK';
END $fx$;

CREATE OR REPLACE FUNCTION pg_temp.unita(p_codice text, p_tipo text) RETURNS bigint
LANGUAGE sql AS $fx$
    INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id)
    SELECT p_codice, p_codice, t.id FROM catalogo.uom_tipi t WHERE t.codice_interno = p_tipo
    RETURNING id
$fx$;

CREATE TEMP TABLE tmp_uc_u AS
SELECT v.k, pg_temp.unita('PGTUC-' || v.k, v.t) AS id
  FROM (VALUES ('G', 'MASSA'), ('KG', 'MASSA'), ('T', 'MASSA'), ('Q', 'MASSA'),
               ('A', 'IMBALLAGGIO'), ('B', 'IMBALLAGGIO'), ('C', 'IMBALLAGGIO'),
               ('D', 'IMBALLAGGIO'), ('E', 'IMBALLAGGIO'), ('F', 'IMBALLAGGIO')) v(k, t);

CREATE OR REPLACE FUNCTION pg_temp.u(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_uc_u WHERE k = p $fx$;

CREATE TEMP TABLE tmp_uc_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTUC-X', p_uom_id => pg_temp.u('G')) AS x;

-- Le mappature: da sempre (A), futura (B), da oggi (C), finita (D), in vigore con
-- fine futura (E), in vigore con fine oggi (F). Una unita' per riga: niente
-- sovrapposizioni.
INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal, valido_al)
SELECT (SELECT x FROM tmp_uc_art), pg_temp.u(v.k), 6,
       pg_temp.oggi() + v.dal, pg_temp.oggi() + v.al
  FROM (VALUES ('A', NULL::integer, NULL::integer), ('B', 5, NULL), ('C', 0, NULL),
               ('D', -60, -10), ('E', -30, 10), ('F', -30, 0)) v(k, dal, al);

-- Le conversioni generali: in vigore (KG -> G), futura (T -> KG), finita (Q -> G).
INSERT INTO catalogo.unita_misura_conversioni (uom_from_id, uom_to_id, fattore, valido_dal, valido_al)
VALUES (pg_temp.u('KG'), pg_temp.u('G'), 1000, pg_temp.oggi() - 30, NULL),
       (pg_temp.u('T'), pg_temp.u('KG'), 1000, pg_temp.oggi() + 5, NULL),
       (pg_temp.u('Q'), pg_temp.u('G'), 100000, pg_temp.oggi() - 60, pg_temp.oggi() - 10);

CREATE TEMP TABLE tmp_uc_m AS
SELECT v.* FROM catalogo.vw_articoli_uom_operativa_dettaglio v
 WHERE v.articolo_id = (SELECT x FROM tmp_uc_art) AND NOT v.is_base;

CREATE TEMP TABLE tmp_uc_c AS
SELECT v.* FROM catalogo.vw_unita_misura_conversioni_dettaglio v
 WHERE v.uom_from_id IN (pg_temp.u('KG'), pg_temp.u('T'), pg_temp.u('Q'));

-- ============================================================
-- Il BB, sulle date (giorni contati da oggi)
-- ============================================================

-- 1
SELECT is(pg_temp.cap(NULL, NULL), 'f|f|t|-1|0|UOM_STORIA_IN_VIGORE|-',
    '1) inizio vuoto, nessuna fine: in vigore, non si cancella ne'' si spegne; si chiude da ieri, proposta oggi');
-- 2
SELECT is(pg_temp.cap(pg_temp.oggi() + 5, NULL), 't|t|t|5|5|-|-',
    '2) inizio fra cinque giorni: si cancella e si spegne; la fine non prima dell''inizio');
-- 3
SELECT is(pg_temp.cap(pg_temp.oggi(), NULL), 't|t|t|0|0|-|-',
    '3) inizio oggi: nessun giorno passato, si cancella; la fine da oggi');
-- 4
SELECT is(pg_temp.cap(pg_temp.oggi() - 60, pg_temp.oggi() - 10), 'f|f|f|-|-|UOM_STORIA_IN_VIGORE|UOM_STORIA_CHIUSA',
    '4) finita dieci giorni fa: niente, coi due motivi');
-- 5
SELECT is(pg_temp.cap(pg_temp.oggi() - 30, pg_temp.oggi() + 10), 'f|f|t|-1|0|UOM_STORIA_IN_VIGORE|-',
    '5) in vigore con una fine futura: la fine si sposta, da ieri');
-- 6
SELECT is(pg_temp.cap(pg_temp.oggi() - 30, pg_temp.oggi()), 'f|f|t|-1|0|UOM_STORIA_IN_VIGORE|-',
    '6) in vigore con fine oggi: oggi non e'' ancora passato, la fine si sposta');

-- ============================================================
-- Le viste
-- ============================================================

-- 7
SELECT is(
    (SELECT concat_ws('|', v.puo_eliminarsi, v.motivo_non_eliminabile, v.puo_cambiare_attivo, v.puo_chiudersi,
                      coalesce(v.data_min_chiusura::text, '-'), v.motivo_non_chiudibile)
       FROM catalogo.vw_articoli_uom_operativa_dettaglio v
      WHERE v.articolo_id = (SELECT x FROM tmp_uc_art) AND v.is_base),
    'f|UOM_BASE_NON_ELIMINABILE|f|f|-|UOM_BASE',
    '7) riga base: non si cancella, attivo e fine non si offrono');

-- 8
SELECT is(
    (SELECT count(*)::int FROM tmp_uc_m m
      WHERE pg_temp.cap(m.valido_dal, m.valido_al)
            IS DISTINCT FROM concat_ws('|', m.puo_eliminarsi, m.puo_cambiare_attivo, m.puo_chiudersi,
                   coalesce((m.data_min_chiusura - pg_temp.oggi())::text, '-'),
                   coalesce((m.data_default_chiusura - pg_temp.oggi())::text, '-'),
                   coalesce(m.motivo_non_eliminabile, '-'), coalesce(m.motivo_non_chiudibile, '-'))),
    0,
    '8) vista della mappatura: le sei righe non base dicono quello che dice il BB');

-- 9
SELECT is(
    (SELECT count(*)::int FROM tmp_uc_c c
      WHERE pg_temp.cap(c.valido_dal, c.valido_al)
            IS DISTINCT FROM concat_ws('|', c.puo_eliminarsi, c.puo_cambiare_attivo, c.puo_chiudersi,
                   coalesce((c.data_min_chiusura - pg_temp.oggi())::text, '-'),
                   coalesce((c.data_default_chiusura - pg_temp.oggi())::text, '-'),
                   coalesce(c.motivo_non_eliminabile, '-'), coalesce(c.motivo_non_chiudibile, '-')))
    + (3 - (SELECT count(*)::int FROM tmp_uc_c)),
    0,
    '9) vista delle conversioni: le tre righe ci sono e dicono quello che dice il BB');

-- ============================================================
-- Il BB e il guard dicono la stessa cosa (riga per riga)
-- ============================================================

-- 10
SELECT is(
    (SELECT string_agg(m.uom_id::text, ',') FROM tmp_uc_m m
      WHERE pg_temp.riesce(format('DELETE FROM catalogo.articoli_uom_operativa WHERE id = %s', m.id))
            IS DISTINCT FROM m.puo_eliminarsi),
    NULL,
    '10) mappatura: si cancella dove puo_eliminarsi, e solo li''');

-- 11
SELECT is(
    (SELECT string_agg(m.uom_id::text, ',') FROM tmp_uc_m m
      WHERE pg_temp.riesce(format('UPDATE catalogo.articoli_uom_operativa SET attivo = NOT attivo WHERE id = %s', m.id))
            IS DISTINCT FROM m.puo_cambiare_attivo),
    NULL,
    '11) mappatura: si spegne dove puo_cambiare_attivo, e solo li''');

-- 12
SELECT is(
    (SELECT string_agg(m.uom_id::text, ',') FROM tmp_uc_m m
      WHERE m.puo_chiudersi
        AND NOT pg_temp.riesce(format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
                                      m.data_min_chiusura, m.id))),
    NULL,
    '12) mappatura: la fine a data_min_chiusura passa su ogni riga che si chiude');

-- 13
SELECT is(
    (SELECT string_agg(m.uom_id::text, ',') FROM tmp_uc_m m
      WHERE m.puo_chiudersi
        AND pg_temp.riesce(format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
                                  m.data_min_chiusura - 1, m.id))),
    NULL,
    '13) mappatura: la fine un giorno prima di data_min_chiusura e'' rifiutata');

-- 14
SELECT is(
    (SELECT count(*)::int FROM tmp_uc_m m
      WHERE NOT m.puo_chiudersi
        AND NOT pg_temp.riesce(format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
                                      pg_temp.oggi() + 10, m.id))),
    (SELECT count(*)::int FROM tmp_uc_m m WHERE NOT m.puo_chiudersi),
    '14) mappatura: su una riga che non si chiude la fine non si sposta');

-- 15
SELECT is(
    (SELECT string_agg(c.id::text, ',') FROM tmp_uc_c c
      WHERE pg_temp.riesce(format('DELETE FROM catalogo.unita_misura_conversioni WHERE id = %s', c.id))
            IS DISTINCT FROM c.puo_eliminarsi
         OR pg_temp.riesce(format('UPDATE catalogo.unita_misura_conversioni SET attivo = NOT attivo WHERE id = %s', c.id))
            IS DISTINCT FROM c.puo_cambiare_attivo),
    NULL,
    '15) conversione generale: cancellazione e spegnimento come dice la vista');

-- ============================================================
-- La lista
-- ============================================================

-- 16
SELECT is(
    (SELECT concat_ws('|', d.vista_sql,
            (SELECT count(*) FROM ui.lista_colonna lc
              WHERE lc.lista_id = d.id
                AND NOT EXISTS (SELECT 1 FROM pg_attribute a
                                 WHERE a.attrelid = 'catalogo.vw_unita_misura_conversioni_dettaglio'::regclass
                                   AND a.attname = lc.campo_sorgente AND a.attnum > 0 AND NOT a.attisdropped)))
       FROM ui.lista_definizione d WHERE d.codice = 'catalogo.conversioni_uom'),
    'vw_unita_misura_conversioni_dettaglio|0',
    '16) la lista delle conversioni legge la vista, e ogni sua colonna c''e''');

SELECT * FROM finish();
ROLLBACK;
