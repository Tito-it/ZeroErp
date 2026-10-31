-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le liste delle note restano gemelle.
--   Ogni tabella `<schema>.note` ha la stessa forma (vendite, catalogo,
--   acquisti, magazzino) e il FE le legge con un BB solo (NoteDrawer). Il
--   catalogo liste ha un codice per tabella-madre (`vendite.note`,
--   `catalogo.note`: D-2 di Tid, 2026-10-31), perche' la definizione porta
--   proprieta' della SEDE (schema_dati, perimetro_emittente). Le COLONNE invece
--   sono le stesse per contratto del modello: due codici con le stesse colonne
--   divergono al primo ritocco fatto da una parte sola, senza errore.
--   Brief: brief-db-liste-datatable-grezze-secondo-giro §3.3.
--
-- ⭐ L'ELENCO SI RICAVA DALLA STRUTTURA, non dai seed: le tabelle `note` degli
--   schemi applicativi (pg_class), e per ognuna la lista col codice
--   `<schema>.note`, se c'e'. Quando acquisti o magazzino avranno la loro
--   lista, ci entrano da sole.
--
-- Il riferimento e' `vendite.note`. Il confronto e' sull'insieme di
--   (codice, campo_sorgente, tipo_colonna, tipo_dato, ordinabile, filtrabile)
--   delle colonne attive: cio' che il BB legge e cio' che il BE ordina.
--   Etichette e chiavi i18n restano libere.
--
-- Indice test (1..4):
--    1) la lista di riferimento `vendite.note` e' a catalogo, con colonne
--    2) ogni lista `<schema>.note` ha lo schema_dati della sua tabella
--    3) ⛔ ogni lista `<schema>.note` ha le stesse colonne di `vendite.note`
--    4) il confronto non e' a vuoto: almeno un'altra tabella note ha la lista
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- Le liste delle note, dalla struttura: una tabella `note` (madre partizionata
-- o tabella semplice) e la lista col codice `<schema>.note`.
CREATE TEMP TABLE tmp_lng_liste AS
SELECT n.nspname::text AS schema_tabella, ld.id AS lista_id, ld.codice::text AS codice,
       ld.schema_dati::text AS schema_dati
  FROM pg_catalog.pg_class c
  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
  JOIN ui.lista_definizione ld ON ld.codice = n.nspname || '.note' AND ld.attivo IS TRUE
 WHERE c.relname = 'note'
   AND c.relkind IN ('p', 'r')
   AND NOT c.relispartition;

-- Scopo: la forma delle colonne attive di una lista, come insieme di righe testo.
CREATE OR REPLACE FUNCTION pg_temp.forma(p_lista_id integer)
RETURNS SETOF text LANGUAGE sql STABLE AS $fx$
  SELECT concat_ws('|', lc.codice, COALESCE(lc.campo_sorgente, '-'), lc.tipo_colonna,
                   lc.tipo_dato, lc.ordinabile, lc.filtrabile)
    FROM ui.lista_colonna lc
   WHERE lc.lista_id = p_lista_id AND lc.attivo IS TRUE;
$fx$;

SELECT ok(
    EXISTS (SELECT 1 FROM tmp_lng_liste l
             WHERE l.codice = 'vendite.note'
               AND EXISTS (SELECT 1 FROM pg_temp.forma(l.lista_id))),
    '1) la lista di riferimento vendite.note e'' a catalogo, con colonne');

SELECT is(
    (SELECT COALESCE(array_agg(l.codice ORDER BY l.codice), '{}'::text[])
       FROM tmp_lng_liste l WHERE l.schema_dati <> l.schema_tabella),
    '{}'::text[],
    '2) ogni lista <schema>.note ha lo schema_dati della sua tabella');

-- ⛔ Le differenze nei due versi, col nome della lista: il rosso dice QUALE
--    colonna diverge e DOVE.
SELECT is(
    (SELECT COALESCE(array_agg(d ORDER BY d), '{}'::text[]) FROM (
        SELECT l.codice || ' in piu'': ' || f AS d
          FROM tmp_lng_liste l, LATERAL (
               SELECT pg_temp.forma(l.lista_id)
               EXCEPT
               SELECT pg_temp.forma((SELECT lista_id FROM tmp_lng_liste WHERE codice = 'vendite.note'))) x(f)
        UNION ALL
        SELECT l.codice || ' manca: ' || f
          FROM tmp_lng_liste l, LATERAL (
               SELECT pg_temp.forma((SELECT lista_id FROM tmp_lng_liste WHERE codice = 'vendite.note'))
               EXCEPT
               SELECT pg_temp.forma(l.lista_id)) x(f)) diff),
    '{}'::text[],
    '3) ogni lista <schema>.note ha le stesse colonne di vendite.note (codice, campo, tipo, ordinabile, filtrabile)');

-- ⚠️ Senza una seconda lista il test 3 passa a vuoto: lo si dice.
SELECT cmp_ok(
    (SELECT count(*)::integer FROM tmp_lng_liste WHERE codice <> 'vendite.note'),
    '>=', 1,
    '4) il confronto non e'' a vuoto: almeno un''altra tabella note ha la sua lista');

SELECT * FROM finish();
ROLLBACK;
