-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la variazione percentuale dei prezzi di una versione di listino
--   passa dal suo verbo, che la giudica dalla versione e non dalle righe che
--   prende: anche a righe zero.
--   ChangeSet: 20261115-79 (vendite.fn_varia_prezzi_versione_listino), -80 e
--   -81 (i COMMENT della check e della superficie).
--   Brief: brief-db-stati-documento-dal-vocabolario, dopo il giro 6f-ter
--   (richiesta del BE del 2026-11-15).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - si varia solo in bozza: CHIUSA E_RIGA_LISTINO_VERSIONE_CHIUSA, fuori
--     dalla bozza E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA, anche quando il gesto
--     non prende nessuna riga (filtro che non prende, filtro vuoto), e anche
--     nell'anteprima;
--   - i parametri obbligatori (E_VENDITE_CHIAMATA_NON_VALIDA), la versione
--     nel perimetro (E_VENDITE_LISTINO_VERSIONE_NOT_FOUND), gli intervalli
--     -99 ... 1000 e 0 ... 10 (E_LISTINO_VARIAZIONE_FUORI_INTERVALLO);
--   - l'anteprima calcola e non scrive; il gesto scrive lo stesso prezzo e
--     lascia la traccia in meta.variazioni_percentuali[], anche a righe zero;
--   - il verbo dice lo stesso motivo della superficie (variazione_blocco_*).
--
-- ⭐ IL CONTROESEMPIO DEL BE: una ATTIVA e un filtro che non prende righe.
--   Prima del -79 l'anteprima passava a 0 righe e il gesto cadeva sulla
--   traccia, con E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE.
-- ⭐ I CASI SI COSTRUISCONO: la bozza dal builder con due articoli a 50,
--   l'attiva dal builder, la chiusa dal job. Nessuno skip.
-- ⭐ LA MARCA SPOSTATA: iniziale su ATTIVA, e l'attiva si varia.
-- ⚠️ La riga VARIA_PREZZI_LISTINO del registro config.azioni_riga, col verbo
--   nuovo, viene dal CSV: la verifica config/test-azioni-riga-registro-v1
--   dopo l'apply.
--
-- Elenco test (plan 13):
--   1) contrasto, anteprima: bozza, attiva (tutte, filtro che non prende,
--      filtro vuoto), chiusa
--   2) contrasto, gesto vero: gli stessi codici, e l'attiva resta com'era
--   3) il verbo dice il motivo della superficie, sull'attiva e sulla chiusa
--   4) parametri mancanti, versione inesistente
--   5) gli intervalli, coi loro estremi
--   6) l'anteprima calcola il prezzo e non scrive niente
--   7) il gesto col filtro prende una riga, al prezzo dell'anteprima
--   8) il gesto scrive il prezzo calcolato, solo sulla riga presa
--   9) la traccia: percentuale, decimali, righe, filtro, operatore
--  10) senza filtro prende tutte le righe attive, e la traccia si appende
--  11) a righe zero in bozza: niente prezzi, la traccia c'e'
--  12) forma e sicurezza: il verbo chiama la check; DEFINER, EXECUTE all'app
--  13) ⭐ iniziale su ATTIVA: l'attiva si varia, la bozza no
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('variazione percentuale di listino');

-- B: la bozza, coi due articoli X e Y. A: l'attiva. C: una versione nel
-- 2020, chiusa dal job.
CREATE TEMP TABLE t_b AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_m), 'variazione, bozza',
                                          p_in_bozza => true);
CREATE TEMP TABLE t_a AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_m), 'variazione, attiva');
CREATE TEMP TABLE t_ch AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_m), 'variazione, chiusa',
                                          '2020-01-01'::date, '2020-12-31'::date);
SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT listino_versione_id FROM t_ch), 'CHIUSA');

-- ⚠️ Il builder in un'istruzione sua.
CREATE TEMP TABLE t_art AS
SELECT s.sigla,
       dbops.fn_pgtap_crea_articolo(('PGT-VAR-' || s.sigla || '-' || substr(md5(clock_timestamp()::text || s.sigla), 1, 10))::varchar,
                                    false, p_listino_tipologia_id => (SELECT tipologia_id FROM t_b)) AS id
  FROM (VALUES ('X'), ('Y')) s(sigla);

SELECT dbops.fn_pgtap_listino_aggiungi_articoli((SELECT listino_versione_id FROM t_b),
                                                ARRAY(SELECT id FROM t_art ORDER BY sigla), 50);

CREATE FUNCTION pg_temp.v(p_caso text)   -- text: 'B', 'A' o 'C'
RETURNS vendite.listini_versioni.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT CASE p_caso WHEN 'B' THEN (SELECT listino_versione_id FROM t_b)
                       WHEN 'A' THEN (SELECT listino_versione_id FROM t_a)
                       WHEN 'C' THEN (SELECT listino_versione_id FROM t_ch) END
$$;

CREATE FUNCTION pg_temp.art(p_sigla text)   -- text: 'X' o 'Y'
RETURNS uuid LANGUAGE sql STABLE AS $$      -- uuid: l'id di catalogo.articoli
    SELECT id FROM t_art WHERE sigla = p_sigla
$$;

CREATE FUNCTION pg_temp.prezzo(p_sigla text)   -- text: 'X' o 'Y'
RETURNS vendite.listini_righe.prezzo%TYPE LANGUAGE sql STABLE AS $$
    SELECT r.prezzo FROM vendite.listini_righe r
     WHERE r.listino_versione_id = pg_temp.v('B') AND r.articolo_id = pg_temp.art(p_sigla)
$$;

-- Il verbo, come istruzione. Il filtro e' un letterale SQL: 'NULL', o un array.
CREATE FUNCTION pg_temp.varia(p_caso text, p_pct numeric, p_dec integer, p_filtro text, p_dry boolean)
RETURNS text LANGUAGE sql AS $$   -- text: l'istruzione
    SELECT format('SELECT * FROM vendite.fn_varia_prezzi_versione_listino(%s, %s, %s, %s, %s)',
                  COALESCE(pg_temp.v(p_caso)::text, '999999999999'), COALESCE(p_pct::text, 'NULL'),
                  COALESCE(p_dec::text, 'NULL'), p_filtro,
                  -- ⚠️ format('%s', true) scrive «t», che l'SQL legge come una colonna.
                  COALESCE(p_dry::text, 'NULL'))
$$;

-- Un filtro che non prende righe: un articolo che la versione non ha.
CREATE FUNCTION pg_temp.filtro_vuoto()
RETURNS text LANGUAGE sql STABLE AS $$   -- text: un letterale SQL
    SELECT format('ARRAY[%L]::uuid[]', gen_random_uuid())
$$;

-- Cio' che rifiuta l'istruzione, 'passa' se passa.
CREATE FUNCTION pg_temp.esito(p_sql text)   -- text: l'istruzione
RETURNS text LANGUAGE sql AS $$             -- text: un codice d'errore, nessuna colonna
    SELECT COALESCE(dbops.fn_pgtap_codice_errore(p_sql), 'passa')
$$;

CREATE TEMP TABLE t_a_prima AS
SELECT (SELECT lv.meta FROM vendite.listini_versioni lv WHERE lv.id = pg_temp.v('A')) AS meta,
       (SELECT array_agg(r.prezzo ORDER BY r.id) FROM vendite.listini_righe r
         WHERE r.listino_versione_id = pg_temp.v('A')) AS prezzi;

-- ============================================================
-- 1-3) I contrasti
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.esito(pg_temp.varia('B', 10, 2, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('A', 10, 2, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('A', 10, 2, pg_temp.filtro_vuoto(), true)),
                   pg_temp.esito(pg_temp.varia('A', 10, 2, 'ARRAY[]::uuid[]', true)),
                   pg_temp.esito(pg_temp.varia('C', 10, 2, 'NULL', true))),
    'passa E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA '
    || 'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_CHIUSA',
    '1. contrasto, anteprima: si varia solo in bozza, anche quando il gesto non prende righe'
);

SELECT is(
    concat_ws(' ', pg_temp.esito(pg_temp.varia('A', 10, 2, 'NULL', false)),
                   pg_temp.esito(pg_temp.varia('A', 10, 2, pg_temp.filtro_vuoto(), false)),
                   pg_temp.esito(pg_temp.varia('A', 10, 2, 'ARRAY[]::uuid[]', false)),
                   pg_temp.esito(pg_temp.varia('C', 10, 2, 'NULL', false)),
                   (SELECT (lv.meta = p.meta)::text FROM vendite.listini_versioni lv, t_a_prima p
                     WHERE lv.id = pg_temp.v('A')),
                   (SELECT (array_agg(r.prezzo ORDER BY r.id) = (SELECT prezzi FROM t_a_prima))::text
                      FROM vendite.listini_righe r WHERE r.listino_versione_id = pg_temp.v('A'))),
    'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA '
    || 'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_CHIUSA true true',
    '2. contrasto, gesto vero: gli stessi codici; l''attiva resta com''era, prezzi e meta'
);

SELECT is(
    (SELECT count(*)::int
       FROM (VALUES ('A'), ('C')) c(caso)
       JOIN vendite.vw_listini_versioni_azioni s ON s.versione_id = pg_temp.v(c.caso)
      WHERE s.variazione_blocco_reason = (script.fn_check_listino_riga_scrivibile(pg_temp.v(c.caso)) -> 0 ->> 'reason')
        AND pg_temp.esito(pg_temp.varia(c.caso, 10, 2, pg_temp.filtro_vuoto(), true))
            = (script.fn_check_listino_riga_scrivibile(pg_temp.v(c.caso)) -> 0 ->> 'codice')),
    2,
    '3. il verbo dice il motivo della superficie, sull''attiva e sulla chiusa'
);

-- ============================================================
-- 4-5) Parametri e intervalli
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.esito(pg_temp.varia('B', NULL, 2, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('B', 10, NULL, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('B', 10, 2, 'NULL', NULL)),
                   pg_temp.esito('SELECT * FROM vendite.fn_varia_prezzi_versione_listino(0, 10, 2)'),
                   pg_temp.esito(pg_temp.varia('?', 10, 2, 'NULL', true))),
    'E_VENDITE_CHIAMATA_NON_VALIDA E_VENDITE_CHIAMATA_NON_VALIDA E_VENDITE_CHIAMATA_NON_VALIDA '
    || 'E_VENDITE_CHIAMATA_NON_VALIDA E_VENDITE_LISTINO_VERSIONE_NOT_FOUND',
    '4. i parametri sono obbligatori, la versione deve esserci'
);

SELECT is(
    concat_ws(' ', pg_temp.esito(pg_temp.varia('B', -100, 2, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('B', 1000.01, 2, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('B', 10, -1, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('B', 10, 11, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('B', -99, 0, 'NULL', true)),
                   pg_temp.esito(pg_temp.varia('B', 1000, 10, 'NULL', true))),
    'E_LISTINO_VARIAZIONE_FUORI_INTERVALLO E_LISTINO_VARIAZIONE_FUORI_INTERVALLO '
    || 'E_LISTINO_VARIAZIONE_FUORI_INTERVALLO E_LISTINO_VARIAZIONE_FUORI_INTERVALLO passa passa',
    '5. la percentuale da -99 a 1000, i decimali da 0 a 10, estremi compresi'
);

-- ============================================================
-- 6-11) Anteprima, gesto, traccia
-- ============================================================
-- 50 * 1.0333 = 51.665: a due decimali 51.67.
SELECT is(
    (SELECT string_agg((x.articolo_id = pg_temp.art('X'))::text || '|' || (x.prezzo_precedente = 50)::text
                       || '|' || (x.prezzo_nuovo = 51.67)::text, ',')
       FROM vendite.fn_varia_prezzi_versione_listino(pg_temp.v('B'), 3.33, 2, ARRAY[pg_temp.art('X')], true) x)
    || ' ' || (pg_temp.prezzo('X') = 50)::text
    || ' ' || COALESCE((SELECT lv.meta -> 'variazioni_percentuali' FROM vendite.listini_versioni lv
                         WHERE lv.id = pg_temp.v('B'))::text, 'nessuna traccia'),
    'true|true|true true nessuna traccia',
    '6. l''anteprima calcola il prezzo e non scrive niente'
);

SELECT is(
    (SELECT count(*)::text || '|' || bool_and(x.prezzo_nuovo = 51.67)::text
       FROM vendite.fn_varia_prezzi_versione_listino(pg_temp.v('B'), 3.33, 2, ARRAY[pg_temp.art('X')], false) x),
    '1|true',
    '7. il gesto col filtro prende una riga, al prezzo dell''anteprima'
);

SELECT is(
    concat_ws(' ', (pg_temp.prezzo('X') = 51.67)::text, (pg_temp.prezzo('Y') = 50)::text),
    'true true',
    '8. il gesto scrive il prezzo calcolato, solo sulla riga presa'
);

SELECT is(
    (SELECT jsonb_array_length(lv.meta -> 'variazioni_percentuali') || '|'
            || (lv.meta -> 'variazioni_percentuali' -> 0 ->> 'variazione_percentuale') || '|'
            || (lv.meta -> 'variazioni_percentuali' -> 0 ->> 'arrotondamento_decimali') || '|'
            || (lv.meta -> 'variazioni_percentuali' -> 0 ->> 'righe_aggiornate') || '|'
            || ((lv.meta -> 'variazioni_percentuali' -> 0 -> 'filtro_articoli')
                 = jsonb_build_array(pg_temp.art('X')))::text || '|'
            || ((lv.meta -> 'variazioni_percentuali' -> 0 ->> 'operatore')
                 = current_setting('app.current_user_id', true))::text || '|'
            || (lv.meta -> 'variazioni_percentuali' -> 0 ? 'data')::text
       FROM vendite.listini_versioni lv WHERE lv.id = pg_temp.v('B')),
    '1|3.33|2|1|true|true|true',
    '9. la traccia: percentuale, decimali, righe, filtro, operatore, data'
);

-- Senza filtro, in un'istruzione sua: tutte le righe attive della bozza.
CREATE TEMP TABLE t_tutte AS
SELECT count(*)::int AS n FROM vendite.fn_varia_prezzi_versione_listino(pg_temp.v('B'), 0, 4, NULL, false);

SELECT is(
    (SELECT t.n = (SELECT count(*)::int FROM vendite.listini_righe r
                    WHERE r.listino_versione_id = pg_temp.v('B') AND r.attivo)
       FROM t_tutte t)::text
    || '|' || (SELECT jsonb_array_length(lv.meta -> 'variazioni_percentuali') || '|'
                      || ((lv.meta -> 'variazioni_percentuali' -> 1 ->> 'righe_aggiornate')::int
                          = (SELECT n FROM t_tutte))::text || '|'
                      || jsonb_typeof(lv.meta -> 'variazioni_percentuali' -> 1 -> 'filtro_articoli')
                 FROM vendite.listini_versioni lv WHERE lv.id = pg_temp.v('B')),
    'true|2|true|null',
    '10. senza filtro prende tutte le righe attive; la traccia si appende'
);

DO $z$ BEGIN
    PERFORM vendite.fn_varia_prezzi_versione_listino(pg_temp.v('B'), 50, 2, ARRAY[gen_random_uuid()], false);
END $z$;

SELECT is(
    (SELECT jsonb_array_length(lv.meta -> 'variazioni_percentuali') || '|'
            || (lv.meta -> 'variazioni_percentuali' -> 2 ->> 'righe_aggiornate')
       FROM vendite.listini_versioni lv WHERE lv.id = pg_temp.v('B'))
    || ' ' || (pg_temp.prezzo('X') = 51.67)::text,
    '3|0 true',
    '11. a righe zero in bozza: nessun prezzo cambia, la traccia c''e'''
);

-- ============================================================
-- 12) La forma e la sicurezza — presidi sulla FORMA, dichiarati tali
-- ============================================================
SELECT is(
    (SELECT (regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g')
               ~ 'script\.fn_check_listino_riga_scrivibile\s*\(')::text || '|'
            || p.prosecdef::text || '|'
            || has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')::text || '|'
            || EXISTS (SELECT 1 FROM aclexplode(p.proacl) a WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE')::text
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_varia_prezzi_versione_listino(bigint,numeric,integer,uuid[],boolean)'::regprocedure),
    'true|true|true|false',
    '12. forma e sicurezza: chiama la check; SECURITY DEFINER, EXECUTE all''applicazione, non a PUBLIC'
);

-- ============================================================
-- 13) ⭐ La marca spostata: iniziale su ATTIVA
-- ============================================================
UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'BOZZA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'ATTIVA';

SELECT is(
    concat_ws(' ', pg_temp.esito(pg_temp.varia('A', 10, 2, pg_temp.filtro_vuoto(), true)),
                   pg_temp.esito(pg_temp.varia('B', 10, 2, pg_temp.filtro_vuoto(), true))),
    'passa E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA',
    '13. con iniziale su ATTIVA l''attiva si varia, la bozza no: la bozza la dice il vocabolario'
);

UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'ATTIVA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'BOZZA';

SELECT * FROM finish();

ROLLBACK;
