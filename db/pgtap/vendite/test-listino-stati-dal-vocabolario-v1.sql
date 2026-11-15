-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la versione di listino legge la sua bozza dal vocabolario.
--   ChangeSet: 20261115-42 (script.fn_check_versione_listino_eliminabile), -43
--   (vendite.fn_check_listino_provenienza_emittente), -44
--   (vendite.fn_listino_ha_storia), -45 (vendite.fn_listino_versione_in_vigore),
--   -46 (vendite.fn_prezzi_legame_oltre_la_fine), -47
--   (vendite.fn_resolve_prezzo_listino_v2_esito), -48
--   (vendite.trgfn_listini_kit_guard), -49
--   (vendite.trgfn_listini_righe_comp_guard_immutabilita_v5), -50
--   (vendite.trgfn_listini_righe_guard_periodicita_quota_fissa), -51
--   (vendite.trgfn_listini_righe_guard_stato), -52
--   (vendite.trgfn_listini_versioni_guard_per_stato).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 6f (S-2, S-3).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la bozza di una versione di listino e' lo stato che il vocabolario marca
--     iniziale: si elimina solo lei, un prezzo non ne proviene, il resolver
--     non ne prende prezzi, non da' storia al listino, non e' in vigore, e in
--     bozza la versione si cambia tutta;
--   - ATTIVA e CHIUSA restano col codice: sono le destinazioni dei processi di
--     attivazione e di chiusura (S-3);
--   - i lettori di significato non nominano BOZZA, e la versione in vigore non
--     nomina ATTIVA e CHIUSA (presidio sulla FORMA, dichiarato tale).
--
-- ⭐ LA MARCA SPOSTATA: iniziale si sposta in transazione da BOZZA ad ATTIVA, e
--   le risposte devono seguirla. Ogni contrasto e' letto prima dello
--   spostamento. L'indice unico parziale su iniziale e' immediato: prima si
--   spegne la marca di partenza, poi si accende l'altra.
-- ⭐ I CASI SI COSTRUISCONO: la versione attiva dal builder (che la attiva dal
--   verbo), la bozza con l'INSERT dell'applicazione (nasce nello stato
--   iniziale). Nessuno skip.
-- ⚠️ Il kit, i componenti e la periodicita' della quota fissa (-46, -48 … -50)
--   hanno solo il presidio sulla forma: la correzione e' la stessa lettura,
--   e costruirne i casi chiede un composito e una tipologia di quota fissa.
--
-- Elenco test (plan 13):
--   1) contrasto: si elimina la bozza, non l'attiva (VERSIONE_NON_IN_BOZZA)
--   2) contrasto: un prezzo non proviene dalla bozza, dall'attiva si'
--   3) contrasto: i due listini hanno storia
--   4) contrasto: in vigore l'attiva, non la bozza
--   5) contrasto: il resolver rifiuta la bozza come versione preferita
--   6) contrasto: la bozza si cambia, l'attiva no
--   7) forma: i lettori non nominano BOZZA; la versione in vigore non nomina
--      ATTIVA e CHIUSA
--   8) ⭐ iniziale su ATTIVA: si elimina l'attiva, non la bozza
--   9) ⭐ ... un prezzo proviene dalla bozza, non dall'attiva
--  10) ⭐ ... il listino con la sola attiva non ha storia
--  11) ⭐ ... in vigore la bozza, non l'attiva
--  12) ⭐ ... il resolver rifiuta l'attiva come versione preferita
--  13) ⭐ ... l'attiva si cambia, la bozza no
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
-- La commessa da' il billing account, l'utility e l'emittente al resolver.
CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('listino dal vocabolario');

-- L: la versione attiva del builder e una bozza; L2: la sola attiva.
CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'listino dal vocabolario');

CREATE TEMP TABLE t_l2 AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'listino dal vocabolario, senza bozza');

-- La bozza, in un periodo che l'attiva non copre (nasce nello stato iniziale).
CREATE TEMP TABLE t_bozza AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al)
    SELECT listino_id, 'PGTAP_6F_BOZZA', '2021-01-01'::date, '2021-12-31'::date FROM t_l
    RETURNING id
)
SELECT id FROM ins;

-- Un articolo qualunque: il percorso rapido rifiuta la bozza prima di
-- cercarlo nella versione. ⚠️ Il builder in un'istruzione sua: in una WHERE
-- girerebbe per ogni riga, e nessuna sarebbe l'articolo appena nato.
CREATE TEMP TABLE t_art0 AS
SELECT dbops.fn_pgtap_crea_articolo(
           ('PGT-6F-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar, false) AS id;

CREATE TEMP TABLE t_art AS
SELECT a.id, a.uom_id FROM catalogo.articoli a JOIN t_art0 USING (id);

CREATE FUNCTION pg_temp.v(p_caso text)   -- text: 'attiva' o 'bozza'
RETURNS vendite.listini_versioni.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT CASE p_caso WHEN 'attiva' THEN (SELECT listino_versione_id FROM t_l)
                       WHEN 'bozza'  THEN (SELECT id FROM t_bozza) END
$$;

-- Il primo motivo per cui la versione non si elimina; '-' se si elimina.
CREATE FUNCTION pg_temp.eliminabile(p_caso text)   -- text: 'attiva' o 'bozza'
RETURNS text LANGUAGE sql STABLE AS $$             -- text: una reason, nessuna colonna
    SELECT COALESCE(script.fn_check_versione_listino_eliminabile(pg_temp.v(p_caso)) -> 0 ->> 'reason', '-')
$$;

-- Il motivo per cui un prezzo non proviene dalla versione; 'ammessa' se proviene.
CREATE FUNCTION pg_temp.provenienza(p_caso text)   -- text: 'attiva' o 'bozza'
RETURNS text LANGUAGE sql STABLE AS $$             -- text: un codice d'errore, nessuna colonna
    SELECT COALESCE(vendite.fn_check_listino_provenienza_emittente(
               (SELECT l.emittente_soggetto_ruolo_id FROM vendite.listini l
                 WHERE l.id = (SELECT listino_id FROM t_l)),
               NULL, NULL, pg_temp.v(p_caso), NULL), 'ammessa')
$$;

-- La versione in vigore a una data, col nome del caso.
CREATE FUNCTION pg_temp.in_vigore(p_data date)
RETURNS text LANGUAGE sql STABLE AS $$   -- text: 'attiva', 'bozza' o 'nessuna'
    SELECT CASE vendite.fn_listino_versione_in_vigore((SELECT listino_id FROM t_l), p_data)
               WHEN pg_temp.v('attiva') THEN 'attiva'
               WHEN pg_temp.v('bozza')  THEN 'bozza'
               ELSE 'nessuna' END
$$;

-- L'esito del resolver con la versione del caso come preferita.
CREATE FUNCTION pg_temp.resolver(p_caso text)   -- text: 'attiva' o 'bozza'
RETURNS text LANGUAGE sql STABLE AS $$          -- text: esito_codice, nessuna colonna
    SELECT r.esito_codice
      FROM t_c c, t_art a,
           vendite.fn_resolve_prezzo_listino_v2_esito(
               a.id, a.uom_id, script.fn_data_operativa(), c.billing_account_id, c.utility_id,
               c.emittente_soggetto_ruolo_id, NULL, NULL, pg_temp.v(p_caso)) r
$$;

-- Un campo della versione cambiato: cio' che l'ha rifiutato, 'passa' se passa.
CREATE FUNCTION pg_temp.cambia(p_caso text)   -- text: 'attiva' o 'bozza'
RETURNS text LANGUAGE sql AS $$               -- text: un codice d'errore, nessuna colonna
    SELECT COALESCE(dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.listini_versioni SET meta = meta || jsonb_build_object(%L, clock_timestamp()) WHERE id = %s',
        'pgtap_6f', pg_temp.v(p_caso))), 'passa')
$$;

-- ============================================================
-- 1-6) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.eliminabile('bozza'), pg_temp.eliminabile('attiva')),
    '- VERSIONE_NON_IN_BOZZA',
    '1. contrasto: si elimina la bozza, non l''attiva'
);

SELECT is(
    concat_ws(' ', pg_temp.provenienza('bozza'), pg_temp.provenienza('attiva')),
    'E_ATTIVITA_LISTINO_VERSIONE_BOZZA ammessa',
    '2. contrasto: un prezzo non proviene dalla bozza, dall''attiva si'''
);

SELECT is(
    concat_ws(' ', vendite.fn_listino_ha_storia((SELECT listino_id FROM t_l)),
                   vendite.fn_listino_ha_storia((SELECT listino_id FROM t_l2))),
    't t',
    '3. contrasto: i due listini hanno una versione uscita dalla bozza'
);

SELECT is(
    concat_ws(' ', pg_temp.in_vigore('2021-06-01'), pg_temp.in_vigore(script.fn_data_operativa())),
    'nessuna attiva',
    '4. contrasto: nel periodo della bozza non c''e'' una versione in vigore, oggi c''e'' l''attiva'
);

SELECT is(
    pg_temp.resolver('bozza'),
    'E_PREZZO_LISTINO_VERSIONE_BOZZA',
    '5. contrasto: il resolver non prende prezzi dalla bozza preferita'
);

SELECT is(
    concat_ws(' ', pg_temp.cambia('bozza'), pg_temp.cambia('attiva')),
    'passa E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE',
    '6. contrasto: la bozza si cambia, l''attiva no'
);

-- ============================================================
-- 7) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che i codici non sono scritti nei corpi (commenti tolti), non che
--   il comportamento sia giusto. Il conteggio in testa fa fallire il test se
--   una funzione del perimetro cambia nome: senza, passerebbe a vuoto.
SELECT is(
    (SELECT count(*) || ' ' || COALESCE(string_agg(x.oggetto, ',' ORDER BY x.oggetto)
                                            FILTER (WHERE x.colpa), '-')
       FROM (SELECT n.nspname || '.' || p.proname AS oggetto,
                    regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g') ~ '''BOZZA'''
                    OR (p.proname = 'fn_listino_versione_in_vigore'
                        AND regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g')
                            ~ '''(ATTIVA|CHIUSA)''') AS colpa
               FROM pg_proc p
               JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname || '.' || p.proname IN (
                    'script.fn_check_versione_listino_eliminabile',
                    'vendite.fn_check_listino_provenienza_emittente',
                    'vendite.fn_listino_ha_storia',
                    'vendite.fn_listino_versione_in_vigore',
                    'vendite.fn_prezzi_legame_oltre_la_fine',
                    'vendite.fn_resolve_prezzo_listino_v2_esito',
                    'vendite.trgfn_listini_kit_guard',
                    'vendite.trgfn_listini_righe_comp_guard_immutabilita_v5',
                    'vendite.trgfn_listini_righe_guard_periodicita_quota_fissa',
                    'vendite.trgfn_listini_righe_guard_stato',
                    'vendite.trgfn_listini_versioni_guard_per_stato')) x),
    '11 -',
    '7. forma: gli undici lettori non nominano BOZZA, la versione in vigore non nomina ATTIVA e CHIUSA'
);

-- ============================================================
-- 8-13) ⭐ La marca spostata: iniziale su ATTIVA
-- ============================================================
UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'BOZZA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'ATTIVA';

SELECT is(
    concat_ws(' ', pg_temp.eliminabile('bozza'), pg_temp.eliminabile('attiva')),
    'VERSIONE_NON_IN_BOZZA -',
    '8. con iniziale su ATTIVA, si elimina l''attiva e non la bozza'
);

SELECT is(
    concat_ws(' ', pg_temp.provenienza('bozza'), pg_temp.provenienza('attiva')),
    'ammessa E_ATTIVITA_LISTINO_VERSIONE_BOZZA',
    '9. ... un prezzo proviene dalla bozza, non dall''attiva'
);

SELECT is(
    concat_ws(' ', vendite.fn_listino_ha_storia((SELECT listino_id FROM t_l)),
                   vendite.fn_listino_ha_storia((SELECT listino_id FROM t_l2))),
    't f',
    '10. ... il listino con la sola attiva non ha storia, quello con la bozza si'''
);

SELECT is(
    concat_ws(' ', pg_temp.in_vigore('2021-06-01'), pg_temp.in_vigore(script.fn_data_operativa())),
    'bozza nessuna',
    '11. ... in vigore la bozza nel suo periodo, e oggi nessuna'
);

SELECT is(
    concat_ws(' ', pg_temp.resolver('attiva'),
                   pg_temp.resolver('bozza') IS DISTINCT FROM 'E_PREZZO_LISTINO_VERSIONE_BOZZA'),
    'E_PREZZO_LISTINO_VERSIONE_BOZZA t',
    '12. ... il resolver rifiuta l''attiva come preferita, e la bozza non piu'''
);

SELECT is(
    concat_ws(' ', pg_temp.cambia('attiva'), pg_temp.cambia('bozza')),
    'passa E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE',
    '13. ... l''attiva si cambia, la bozza no'
);

UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'ATTIVA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'BOZZA';

SELECT * FROM finish();

ROLLBACK;
