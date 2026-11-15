-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la rettifica del prezzo di una riga del listino in uso passa dal
--   verbo, col motivo e la traccia; fuori dal verbo il prezzo non cambia.
--   ChangeSet: 20261115-66 (script.fn_check_listino_riga_rettificabile), -67
--   (vendite.fn_rettifica_riga_listino), -68 (la porta nel guard
--   vendite.trgfn_listini_righe_guard_stato), -71
--   (vendite.vw_listini_righe_azioni, rettifica_blocco_*).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 6f-ter (§6.28, R-L1).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - si rettifica solo una riga della versione in vigore alla data operativa,
--     non usata da un documento: in bozza E_RIGA_LISTINO_RETTIFICA_IN_BOZZA
--     (si modifica), CHIUSA E_RIGA_LISTINO_VERSIONE_CHIUSA, ATTIVA non ancora
--     iniziata E_RIGA_LISTINO_RETTIFICA_NON_IN_VIGORE, citata
--     E_RIGA_LISTINO_PROPAGATA;
--   - il motivo e' obbligatorio, al piu' 500 caratteri
--     (E_RIGA_LISTINO_RETTIFICA_MOTIVO_OBBLIGATORIO);
--   - la rettifica scrive il prezzo e appende la traccia in
--     meta.rettifiche_controllate[] (motivo, prezzi, operatore);
--   - fuori dal verbo il prezzo di una riga ATTIVA non cambia
--     (E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA), e la porta aperta a mano non
--     lascia cambiare altro che prezzo e meta;
--   - la superficie dice lo stesso motivo della check.
--
-- ⭐ I CASI SI COSTRUISCONO: l'attiva in vigore dal builder (nata in bozza con
--   le sue righe), una seconda attiva che comincia fra trenta giorni, la chiusa
--   dal job, la bozza dall'INSERT; la riga propagata da un'attivita' di commessa
--   che la cita. Nessuno skip.
-- ⭐ LA MARCA SPOSTATA: iniziale su ATTIVA, e la riga in vigore diventa «in
--   bozza» per la check e per il verbo.
-- ⚠️ La riga RETTIFICA_RIGA_LISTINO del registro config.azioni_riga viene dal
--   CSV: la verifica config/test-azioni-riga-registro-v1 dopo l'apply.
--
-- Elenco test (plan 12):
--   1) contrasto: la check su bozza, chiusa, futura, propagata, libera
--   2) contrasto: il verbo solleva gli stessi codici
--   3) il motivo: assente, di soli spazi, di 501 caratteri; il prezzo assente
--   4) la rettifica della riga libera ritorna prezzo di prima, nuovo, motivo
--   5) la riga ha il prezzo nuovo e una traccia con motivo, prezzi, operatore
--   6) una seconda rettifica appende la sua traccia
--   7) la porta: l'UPDATE diretto del prezzo di una riga ATTIVA e' rifiutato
--   8) la porta aperta a mano cambia solo prezzo e meta: con un'altra colonna no
--   9) la superficie dice il motivo della check, riga per riga
--  10) forma: il verbo e il guard chiamano la check
--  11) sicurezza: SECURITY DEFINER, EXECUTE all'applicazione e non a PUBLIC
--  12) ⭐ iniziale su ATTIVA: la riga in vigore e' «in bozza», e non si rettifica
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('rettifica riga di listino');

-- L: l'attiva in vigore, nata in bozza per prendere le righe P e R.
CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'rettifica', p_in_bozza => true);

-- L2: una versione nel 2020, chiusa dal job. L3: un'attiva che comincia fra trenta giorni.
CREATE TEMP TABLE t_l2 AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'rettifica, chiusa',
                                          '2020-01-01'::date, '2020-12-31'::date);
SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT listino_versione_id FROM t_l2), 'CHIUSA');

CREATE TEMP TABLE t_l3 AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c), 'rettifica, futura',
                                          script.fn_data_operativa() + 30);

CREATE TEMP TABLE t_bozza AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al)
    SELECT listino_id, 'PGTAP_6FT_RETT_BOZZA', '2021-01-01'::date, '2021-12-31'::date FROM t_l
    RETURNING id
)
SELECT id FROM ins;

-- ⚠️ Il builder in un'istruzione sua.
CREATE TEMP TABLE t_art AS
SELECT s.sigla,
       dbops.fn_pgtap_crea_articolo(('PGT-RET-' || s.sigla || '-' || substr(md5(clock_timestamp()::text || s.sigla), 1, 10))::varchar,
                                    false, p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS id
  FROM (VALUES ('P'), ('R'), ('B')) s(sigla);

SELECT dbops.fn_pgtap_listino_aggiungi_articoli((SELECT listino_versione_id FROM t_l),
                                                ARRAY(SELECT id FROM t_art WHERE sigla IN ('P', 'R')), 50);
SELECT dbops.fn_pgtap_listino_aggiungi_articoli((SELECT id FROM t_bozza),
                                                ARRAY[(SELECT id FROM t_art WHERE sigla = 'B')], 50);
SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT listino_versione_id FROM t_l), 'ATTIVA');

-- Le righe del caso: P (propagata) e R (libera) dell'attiva, B della bozza,
-- C della chiusa e F della futura (le righe d'appoggio del builder).
CREATE TEMP TABLE t_riga AS
SELECT s.sigla AS caso, r.id
  FROM t_art s JOIN vendite.listini_righe r ON r.articolo_id = s.id
UNION ALL
SELECT 'C', min(r.id) FROM vendite.listini_righe r WHERE r.listino_versione_id = (SELECT listino_versione_id FROM t_l2)
UNION ALL
SELECT 'F', min(r.id) FROM vendite.listini_righe r WHERE r.listino_versione_id = (SELECT listino_versione_id FROM t_l3);

CREATE FUNCTION pg_temp.r(p_caso text)   -- text: 'P', 'R', 'B', 'C' o 'F'
RETURNS vendite.listini_righe.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT id FROM t_riga WHERE caso = p_caso
$$;

-- La riga P propagata: un'attivita' di commessa ne cita il prezzo.
SELECT dbops.fn_pgtap_crea_commessa_attivita(
           p_commessa_id         => (SELECT commessa_id FROM t_c),
           p_articolo_id         => (SELECT id FROM t_art WHERE sigla = 'P'),
           p_listino_versione_id => (SELECT listino_versione_id FROM t_l),
           p_listino_riga_id     => pg_temp.r('P'));

-- Il codice della check per la riga: '-' se si rettifica.
CREATE FUNCTION pg_temp.codice_check(p_caso text)   -- text: il caso
RETURNS text LANGUAGE sql STABLE AS $$               -- text: un codice d'errore
    SELECT COALESCE(script.fn_check_listino_riga_rettificabile(pg_temp.r(p_caso)) -> 0 ->> 'codice', '-')
$$;

-- Il verbo, come istruzione.
CREATE FUNCTION pg_temp.rettifica(p_caso text, p_prezzo numeric, p_motivo text)   -- il caso, il prezzo, il motivo
RETURNS text LANGUAGE sql AS $$                                                   -- text: l'istruzione
    SELECT format('SELECT * FROM vendite.fn_rettifica_riga_listino(%s, %s, %L)',
                  pg_temp.r(p_caso), COALESCE(p_prezzo::text, 'NULL'), p_motivo)
$$;

-- Cio' che rifiuta l'istruzione, 'passa' se passa.
CREATE FUNCTION pg_temp.esito(p_sql text)   -- text: l'istruzione
RETURNS text LANGUAGE sql AS $$             -- text: un codice d'errore, nessuna colonna
    SELECT COALESCE(dbops.fn_pgtap_codice_errore(p_sql), 'passa')
$$;

-- ============================================================
-- 1-3) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.codice_check('B'), pg_temp.codice_check('C'), pg_temp.codice_check('F'),
                   pg_temp.codice_check('P'), pg_temp.codice_check('R')),
    'E_RIGA_LISTINO_RETTIFICA_IN_BOZZA E_RIGA_LISTINO_VERSIONE_CHIUSA E_RIGA_LISTINO_RETTIFICA_NON_IN_VIGORE '
    || 'E_RIGA_LISTINO_PROPAGATA -',
    '1. contrasto: si rettifica solo la riga libera della versione in vigore'
);

SELECT is(
    concat_ws(' ', pg_temp.esito(pg_temp.rettifica('B', 60, 'pgTAP')), pg_temp.esito(pg_temp.rettifica('C', 60, 'pgTAP')),
                   pg_temp.esito(pg_temp.rettifica('F', 60, 'pgTAP')), pg_temp.esito(pg_temp.rettifica('P', 60, 'pgTAP'))),
    'E_RIGA_LISTINO_RETTIFICA_IN_BOZZA E_RIGA_LISTINO_VERSIONE_CHIUSA E_RIGA_LISTINO_RETTIFICA_NON_IN_VIGORE '
    || 'E_RIGA_LISTINO_PROPAGATA',
    '2. contrasto: il verbo solleva gli stessi codici della check'
);

SELECT is(
    concat_ws(' ', pg_temp.esito(pg_temp.rettifica('R', 60, NULL)), pg_temp.esito(pg_temp.rettifica('R', 60, '   ')),
                   pg_temp.esito(pg_temp.rettifica('R', 60, repeat('x', 501))),
                   pg_temp.esito(pg_temp.rettifica('R', NULL, 'pgTAP'))),
    'E_RIGA_LISTINO_RETTIFICA_MOTIVO_OBBLIGATORIO E_RIGA_LISTINO_RETTIFICA_MOTIVO_OBBLIGATORIO '
    || 'E_RIGA_LISTINO_RETTIFICA_MOTIVO_OBBLIGATORIO E_VENDITE_CHIAMATA_NON_VALIDA',
    '3. il motivo e'' obbligatorio, al piu'' 500 caratteri; il prezzo anche'
);

-- ============================================================
-- 4-6) La rettifica e la traccia
-- ============================================================
-- ⚠️ I prezzi si confrontano come numeri: il verbo rende e traccia il prezzo
--   nuovo come e' arrivato (55), quello di prima alla scala della colonna
--   (50.0000000000). Segnalato al team DB (giro 6f-ter), non e' il contratto.
SELECT is(
    (SELECT (x.prezzo_precedente = 50)::text || '|' || (x.prezzo_nuovo = 55)::text || '|' || x.motivo
       FROM vendite.fn_rettifica_riga_listino(pg_temp.r('R'), 55, '  errore di battitura  ') x),
    'true|true|errore di battitura',
    '4. la rettifica ritorna il prezzo di prima, quello nuovo e il motivo ripulito'
);

SELECT is(
    (SELECT r.prezzo::text || '|' || jsonb_array_length(r.meta -> 'rettifiche_controllate') || '|'
            || (r.meta -> 'rettifiche_controllate' -> 0 ->> 'motivo') || '|'
            || ((r.meta -> 'rettifiche_controllate' -> 0 ->> 'prezzo_precedente')::numeric = 50)::text || '|'
            || ((r.meta -> 'rettifiche_controllate' -> 0 ->> 'prezzo_nuovo')::numeric = 55)::text || '|'
            || ((r.meta -> 'rettifiche_controllate' -> 0 ->> 'operatore')
                 = current_setting('app.current_user_id', true))::text
       FROM vendite.listini_righe r WHERE r.id = pg_temp.r('R')),
    '55.0000000000|1|errore di battitura|true|true|true',
    '5. la riga ha il prezzo nuovo e una traccia: motivo, prezzi, operatore'
);

-- La seconda in un'istruzione sua: letta nella stessa, la riga sarebbe quella
-- di prima (lo snapshot dell'istruzione).
DO $r2$ BEGIN PERFORM vendite.fn_rettifica_riga_listino(pg_temp.r('R'), 0, 'omaggio'); END $r2$;

SELECT is(
    (SELECT jsonb_array_length(r.meta -> 'rettifiche_controllate') || '|'
            || ((r.meta -> 'rettifiche_controllate' -> 1 ->> 'prezzo_precedente')::numeric = 55)::text
            || '|' || (r.prezzo = 0)::text
       FROM vendite.listini_righe r WHERE r.id = pg_temp.r('R')),
    '2|true|true',
    '6. una seconda rettifica (a zero: e'' un prezzo) appende la sua traccia'
);

-- ============================================================
-- 7-8) La porta
-- ============================================================
SELECT is(
    pg_temp.esito(format('UPDATE vendite.listini_righe SET prezzo = 70 WHERE id = %s', pg_temp.r('R'))),
    'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA',
    '7. fuori dal verbo il prezzo di una riga ATTIVA non cambia'
);

-- ⚠️ La porta la onora il proprietario della tabella: la prova gira da
--   proprietario, quindi la GUC aperta a mano e' la porta vera. Anche cosi'
--   cambia solo prezzo e meta.
SELECT is(
    pg_temp.esito(format(
        'DO $d$ BEGIN PERFORM set_config(''zeroerp.listino_riga_rettifica'', %L, true); '
        || 'UPDATE vendite.listini_righe SET prezzo = 70, periodicita = %L WHERE id = %s; END $d$',
        pg_temp.r('R')::text, 'MENSILE', pg_temp.r('R'))),
    'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA',
    '8. la porta aperta cambia solo prezzo e meta: con un''altra colonna ricade nella regola'
);
SELECT set_config('zeroerp.listino_riga_rettifica', '', true);

-- ============================================================
-- 9) La superficie
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM t_riga t
       JOIN vendite.vw_listini_righe_azioni a ON a.listino_riga_id = t.id
      WHERE a.rettifica_blocco_reason IS NOT DISTINCT FROM
            (script.fn_check_listino_riga_rettificabile(t.id) -> 0 ->> 'reason')
        AND a.rettifica_blocco_reason_key IS NOT DISTINCT FROM
            (script.fn_check_listino_riga_rettificabile(t.id) -> 0 ->> 'reason_key')),
    5,
    '9. la superficie dice il motivo della check, sulle cinque righe'
);

-- ============================================================
-- 10-11) La forma e la sicurezza — presidi sulla FORMA, dichiarati tali
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM unnest(ARRAY['vendite.fn_rettifica_riga_listino(bigint,numeric,text)',
                         'vendite.trgfn_listini_righe_guard_stato()']) g(f)
      WHERE regexp_replace(pg_get_functiondef(g.f::regprocedure), '--[^\n]*', '', 'g')
            ~ 'script\.fn_check_listino_riga_rettificabile\s*\('),
    2,
    '10. forma: il verbo e il guard chiamano la check della rettifica'
);

SELECT is(
    (SELECT p.prosecdef::text || '|'
            || has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')::text || '|'
            || EXISTS (SELECT 1 FROM aclexplode(p.proacl) a WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE')::text
       FROM pg_proc p WHERE p.oid = 'vendite.fn_rettifica_riga_listino(bigint,numeric,text)'::regprocedure),
    'true|true|false',
    '11. sicurezza: SECURITY DEFINER, EXECUTE all''applicazione, non a PUBLIC'
);

-- ============================================================
-- 12) ⭐ La marca spostata: iniziale su ATTIVA
-- ============================================================
UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'BOZZA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'ATTIVA';

SELECT is(
    concat_ws(' ', pg_temp.codice_check('R'), pg_temp.esito(pg_temp.rettifica('R', 80, 'pgTAP'))),
    'E_RIGA_LISTINO_RETTIFICA_IN_BOZZA E_RIGA_LISTINO_RETTIFICA_IN_BOZZA',
    '12. con iniziale su ATTIVA la riga in vigore e'' «in bozza»: si modifica, non si rettifica'
);

UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'ATTIVA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'BOZZA';

SELECT * FROM finish();

ROLLBACK;
