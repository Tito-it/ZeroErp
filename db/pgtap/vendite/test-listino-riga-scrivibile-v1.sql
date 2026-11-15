-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la riga di listino si scrive con una regola sola, e le superfici la
--   dicono.
--   ChangeSet: 20261115-53 (script.fn_check_listino_riga_scrivibile), -54
--   (vendite.trgfn_listini_righe_guard_stato), -55
--   (trg_listini_righe_a10_guard_stato_ins_upd_dlt), -56
--   (vendite.vw_listini_versioni_azioni, aggiunta_riga_blocco_*), -57
--   (vendite.vw_listini_righe_azioni).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 6f-bis (D-LIST (a)).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - in bozza si scrive tutto; in una versione CHIUSA niente, nemmeno una
--     riga nuova (E_RIGA_LISTINO_VERSIONE_CHIUSA); in una ATTIVA una riga
--     nuova e' una rettifica, e una riga che c'e' si cambia finche' un
--     documento non ne ha usato il prezzo (E_RIGA_LISTINO_PROPAGATA);
--   - la superficie della versione (la riga nuova) e quella delle righe (la
--     riga che c'e') dicono il primo motivo che il guard solleva;
--   - il guard non riscrive la regola: chiama la check (presidio sulla
--     FORMA, dichiarato tale).
--
-- ⭐ I CASI SI COSTRUISCONO: la versione attiva e la chiusa dal builder (la
--   chiusa dal job, con la fine passata), la bozza dall'INSERT
--   dell'applicazione, le righe dal builder delle righe, la riga propagata da
--   un'attivita' di commessa che la cita. Nessuno skip.
-- ⭐ LA MARCA SPOSTATA: iniziale si sposta da BOZZA a CHIUSA, e la versione
--   chiusa diventa la bozza per la check, per la superficie e per il guard.
-- ⚠️ Le due righe del registro config.azioni_riga (AGGIUNGI_RIGA_LISTINO,
--   MODIFICA_RIGA_LISTINO) vengono dal CSV, che la prova in transazione non
--   carica: le verifica config/test-azioni-riga-registro-v1 dopo l'apply.
--
-- Elenco test (plan 9):
--   1) contrasto: la riga nuova si aggiunge alla bozza e all'attiva, non alla
--      chiusa (superficie della versione)
--   2) contrasto: la riga che c'e' si modifica in bozza e nell'attiva se non
--      e' propagata; la propagata no, la chiusa no (superficie delle righe)
--   3) contrasto: il guard rifiuta la riga nuova nella chiusa, e la accetta
--      nell'attiva
--   4) contrasto: il guard rifiuta la modifica della propagata e
--      l'eliminazione della chiusa, accetta la modifica della non propagata
--   5) contrasto: superficie e guard dicono lo stesso codice, riga per riga
--   6) forma: il guard chiama la check e non nomina stati ne' tabelle dei
--      documenti
--   7) ⭐ iniziale su CHIUSA: la riga nuova si aggiunge alla chiusa
--   8) ⭐ ... e la riga della chiusa si modifica, dalla superficie e dal guard
--   9) ⭐ ... e la bozza, ora fuori dallo stato iniziale, tiene la sua riga
--      modificabile (nessun documento la cita): la decide la propagazione
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('riga di listino scrivibile');

-- L: l'attiva del builder e una bozza; L2: una versione nel 2020, chiusa dal job.
CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'riga scrivibile');

CREATE TEMP TABLE t_l2 AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'riga scrivibile, chiusa',
                                          '2020-01-01'::date, '2020-12-31'::date);

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT listino_versione_id FROM t_l2), 'CHIUSA');

CREATE TEMP TABLE t_bozza AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al)
    SELECT listino_id, 'PGTAP_6FB_BOZZA', '2021-01-01'::date, '2021-12-31'::date FROM t_l
    RETURNING id
)
SELECT id FROM ins;

-- Tre articoli: uno per la bozza, uno per la rettifica dell'attiva, uno da
-- provare nella chiusa. ⚠️ Il builder in un'istruzione sua.
CREATE TEMP TABLE t_art AS
SELECT s.sigla,
       dbops.fn_pgtap_crea_articolo(('PGT-6FB-' || s.sigla || '-' || substr(md5(clock_timestamp()::text || s.sigla), 1, 10))::varchar,
                                    false, p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS id
  FROM (VALUES ('B'), ('A2'), ('C2')) s(sigla);

SELECT dbops.fn_pgtap_listino_aggiungi_articoli((SELECT id FROM t_bozza),
                                                ARRAY[(SELECT id FROM t_art WHERE sigla = 'B')]);
SELECT dbops.fn_pgtap_listino_aggiungi_articoli((SELECT listino_versione_id FROM t_l),
                                                ARRAY[(SELECT id FROM t_art WHERE sigla = 'A2')]);

-- Le righe, per nome: la riga d'appoggio dell'attiva (propagata, sotto), la
-- rettifica dell'attiva, la riga della bozza, la riga d'appoggio della chiusa.
CREATE TEMP TABLE t_riga AS
SELECT 'A' AS caso, r.id, r.articolo_id, r.listino_versione_id
  FROM vendite.listini_righe r
 WHERE r.listino_versione_id = (SELECT listino_versione_id FROM t_l)
   AND r.articolo_id <> (SELECT id FROM t_art WHERE sigla = 'A2')
UNION ALL
SELECT 'A2', r.id, r.articolo_id, r.listino_versione_id
  FROM vendite.listini_righe r
 WHERE r.articolo_id = (SELECT id FROM t_art WHERE sigla = 'A2')
UNION ALL
SELECT 'B', r.id, r.articolo_id, r.listino_versione_id
  FROM vendite.listini_righe r
 WHERE r.listino_versione_id = (SELECT id FROM t_bozza)
UNION ALL
SELECT 'C', r.id, r.articolo_id, r.listino_versione_id
  FROM vendite.listini_righe r
 WHERE r.listino_versione_id = (SELECT listino_versione_id FROM t_l2);

-- La riga A propagata: un'attivita' di commessa ne cita il prezzo.
SELECT dbops.fn_pgtap_crea_commessa_attivita(
           p_commessa_id         => (SELECT commessa_id FROM t_c),
           p_articolo_id         => (SELECT articolo_id FROM t_riga WHERE caso = 'A'),
           p_listino_versione_id => (SELECT listino_versione_id FROM t_riga WHERE caso = 'A'),
           p_listino_riga_id     => (SELECT id FROM t_riga WHERE caso = 'A'));

CREATE FUNCTION pg_temp.v(p_caso text)   -- text: 'attiva', 'bozza' o 'chiusa'
RETURNS vendite.listini_versioni.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT CASE p_caso WHEN 'attiva' THEN (SELECT listino_versione_id FROM t_l)
                       WHEN 'bozza'  THEN (SELECT id FROM t_bozza)
                       WHEN 'chiusa' THEN (SELECT listino_versione_id FROM t_l2) END
$$;

CREATE FUNCTION pg_temp.r(p_caso text)   -- text: 'A', 'A2', 'B' o 'C'
RETURNS vendite.listini_righe.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT id FROM t_riga WHERE caso = p_caso
$$;

-- La superficie della versione: il motivo per cui la riga nuova non si aggiunge ('-' = si aggiunge).
CREATE FUNCTION pg_temp.aggiunta(p_caso text)   -- text: 'attiva', 'bozza' o 'chiusa'
RETURNS text LANGUAGE sql STABLE AS $$          -- text: una reason, nessuna colonna
    SELECT COALESCE(a.aggiunta_riga_blocco_reason, '-') || '|' || COALESCE(a.aggiunta_riga_blocco_reason_key, '-')
      FROM vendite.vw_listini_versioni_azioni a WHERE a.versione_id = pg_temp.v(p_caso)
$$;

-- La superficie delle righe: il motivo per cui la riga non si modifica ('-' = si modifica).
CREATE FUNCTION pg_temp.modifica(p_caso text)   -- text: 'A', 'A2', 'B' o 'C'
RETURNS text LANGUAGE sql STABLE AS $$          -- text: una reason, nessuna colonna
    SELECT COALESCE(a.modifica_blocco_reason, '-')
      FROM vendite.vw_listini_righe_azioni a WHERE a.listino_riga_id = pg_temp.r(p_caso)
$$;

-- Il codice della check per la riga (o per la riga nuova, senza): '-' se passa.
CREATE FUNCTION pg_temp.codice_check(p_versione text, p_riga text)   -- text: i casi
RETURNS text LANGUAGE sql STABLE AS $$                                -- text: un codice d'errore
    SELECT COALESCE(script.fn_check_listino_riga_scrivibile(pg_temp.v(p_versione), pg_temp.r(p_riga)) -> 0 ->> 'codice', '-')
$$;

-- Il guard: cio' che rifiuta l'istruzione, 'passa' se passa.
CREATE FUNCTION pg_temp.guard(p_sql text)   -- text: l'istruzione
RETURNS text LANGUAGE sql AS $$             -- text: un codice d'errore, nessuna colonna
    SELECT COALESCE(dbops.fn_pgtap_codice_errore(p_sql), 'passa')
$$;

CREATE FUNCTION pg_temp.nuova_riga(p_caso text)   -- text: 'attiva', 'bozza' o 'chiusa'
RETURNS text LANGUAGE sql AS $$                   -- text: l'istruzione
    SELECT format('SELECT dbops.fn_pgtap_listino_aggiungi_articoli(%s, ARRAY[%L::uuid])',
                  pg_temp.v(p_caso), (SELECT id FROM t_art WHERE sigla = 'C2'))
$$;

CREATE FUNCTION pg_temp.cambia_riga(p_caso text)   -- text: 'A', 'A2', 'B' o 'C'
RETURNS text LANGUAGE sql AS $$                    -- text: l'istruzione
    SELECT format('UPDATE vendite.listini_righe SET prezzo = prezzo + 1 WHERE id = %s', pg_temp.r(p_caso))
$$;

-- ============================================================
-- 1-5) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.aggiunta('bozza'), pg_temp.aggiunta('attiva'), pg_temp.aggiunta('chiusa')),
    '-|- -|- VERSIONE_CHIUSA|vendite.listini.azione_reason.versione_chiusa',
    '1. contrasto: la riga nuova si aggiunge alla bozza e all''attiva, non alla chiusa'
);

SELECT is(
    concat_ws(' ', pg_temp.modifica('B'), pg_temp.modifica('A2'), pg_temp.modifica('A'), pg_temp.modifica('C')),
    '- - RIGA_PROPAGATA VERSIONE_CHIUSA',
    '2. contrasto: in bozza e nell''attiva non propagata la riga si modifica; la propagata e la chiusa no'
);

SELECT is(
    concat_ws(' ', pg_temp.guard(pg_temp.nuova_riga('chiusa')), pg_temp.guard(pg_temp.nuova_riga('attiva'))),
    'E_RIGA_LISTINO_VERSIONE_CHIUSA passa',
    '3. contrasto: il guard rifiuta la riga nuova nella chiusa, e la accetta nell''attiva (una rettifica)'
);

SELECT is(
    concat_ws(' ', pg_temp.guard(pg_temp.cambia_riga('A')),
                   pg_temp.guard(format('DELETE FROM vendite.listini_righe WHERE id = %s', pg_temp.r('C'))),
                   pg_temp.guard(pg_temp.cambia_riga('A2'))),
    'E_RIGA_LISTINO_PROPAGATA E_RIGA_LISTINO_VERSIONE_CHIUSA passa',
    '4. contrasto: il guard rifiuta la propagata e la chiusa, accetta la non propagata dell''attiva'
);

SELECT is(
    concat_ws(' ', pg_temp.codice_check('attiva', 'A'), pg_temp.codice_check('chiusa', 'C'),
                   pg_temp.codice_check('chiusa', NULL), pg_temp.codice_check('bozza', 'B')),
    'E_RIGA_LISTINO_PROPAGATA E_RIGA_LISTINO_VERSIONE_CHIUSA E_RIGA_LISTINO_VERSIONE_CHIUSA -',
    '5. contrasto: la check da'' il codice che il guard solleva, riga per riga'
);

-- ============================================================
-- 6) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che la regola non e' ricopiata nel guard, non che sia giusta.
SELECT ok(
    (SELECT t ~ 'script\.fn_check_listino_riga_scrivibile\s*\('
            AND t !~ '''(BOZZA|ATTIVA|CHIUSA)'''
            AND t !~ 'listino_riga_id\s*='
       FROM (SELECT regexp_replace(pg_get_functiondef('vendite.trgfn_listini_righe_guard_stato()'::regprocedure),
                                   '--[^\n]*', '', 'g') AS t) x),
    '6. forma: il guard chiama la check e non nomina stati ne'' le tabelle dei documenti'
);

-- ============================================================
-- 7-9) ⭐ La marca spostata: iniziale su CHIUSA
-- ============================================================
UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'BOZZA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'CHIUSA';

SELECT is(
    pg_temp.aggiunta('chiusa'),
    '-|-',
    '7. con iniziale su CHIUSA, la riga nuova si aggiunge alla chiusa'
);

SELECT is(
    concat_ws(' ', pg_temp.modifica('C'), pg_temp.guard(pg_temp.cambia_riga('C'))),
    '- passa',
    '8. ... e la riga della chiusa si modifica: la superficie lo dice, il guard lo lascia fare'
);

SELECT is(
    concat_ws(' ', pg_temp.modifica('B'), pg_temp.guard(pg_temp.cambia_riga('B'))),
    '- passa',
    '9. ... la bozza, ora fuori dallo stato iniziale, tiene la sua riga modificabile: nessun documento la cita'
);

UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'CHIUSA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'BOZZA';

SELECT * FROM finish();

ROLLBACK;
