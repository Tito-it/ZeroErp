-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_doc_azioni_permesse, i passaggi manuali permessi da uno stato
--   Il BB comune (20261027-40) che le otto capability di vendita leggono al
--   posto del predicato ricopiato (-41 … -48), e i due vincoli che ne tolgono
--   le ambiguita' (-49 manuale dichiarato, -50 tipo_lotto solo sui passaggi di
--   processo). Brief: brief-modello-documento-vendita §15.14 (richiesta del
--   team BE; D-1 … D-4 di Tid, 2026-10-27).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - dallo stato di un documento: i passaggi vivi, manuali, il cui permesso
--     l'utente della sessione ha; un passaggio senza azione resta (decide il
--     livello sul documento);
--   - il lotto: EMESSA senza numera_fatture_lotti -> nessuno; con -> numera e
--     riporta in bozza; DRAFT -> annulla (riga senza azione), senza concessioni;
--   - la stessa risposta del predicato che le capability scrivevano da se',
--     su ogni stato delle otto testate di vendita, con e senza l'azione;
--   - stato NULL: nessuna riga; testata fuori mappa: chiamata non valida;
--   - una riga di matrice senza manuale, o con tipo_lotto su un passaggio
--     manuale, non si scrive.
--
-- Elenco test (plan 11):
--   1) il lettore esiste: STABLE, SECURITY INVOKER
--   2) lotto EMESSA senza numera_fatture_lotti: nessun passaggio
--   3) lotto DRAFT senza concessioni: annulla, senza azione
--   4) equivalenza col predicato di prima, senza concessioni (e ci sono stati provati)
--   5) lotto EMESSA con numera_fatture_lotti: numera, riporta_a_draft
--   6) ... e l'azione che chiedono e' numera_fatture_lotti
--   7) equivalenza col predicato di prima, con la concessione
--   8) stato NULL: nessuna riga
--   9) testata fuori mappa -> chiamata non valida
--  10) una riga di matrice senza meta.manuale: rifiutata
--  11) tipo_lotto su un passaggio manuale: rifiutato
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- 1) L'oggetto e la sua forma
SELECT is(
    (SELECT p.provolatile::text || ' ' || p.prosecdef::text
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_doc_azioni_permesse'),
    's false',
    'script.fn_doc_azioni_permesse esiste: STABLE, SECURITY INVOKER'
);

-- ── Fixture ─────────────────────────────────────────────────────────
-- Due lotti vuoti: la lista passa lo stato della sua riga.
CREATE TEMP TABLE t_draft  AS SELECT * FROM dbops.fn_pgtap_crea_lotto('azioni permesse bozza');
CREATE TEMP TABLE t_emesso AS SELECT * FROM dbops.fn_pgtap_crea_lotto('azioni permesse emesso', 'EMESSA');

CREATE FUNCTION pg_temp.chiavi(p_lotto_id bigint) RETURNS text LANGUAGE sql AS $f$
    SELECT COALESCE(string_agg(COALESCE(a.action_key, '-'), ' ' ORDER BY a.action_key), '')
      FROM vendite.fatturazione_lotti l,
           script.fn_doc_azioni_permesse('vendite.fatturazione_lotti'::regclass, l.stato_doc_fiscale_id) a
     WHERE l.id = p_lotto_id
$f$;

-- Il predicato di prima, come le capability lo scrivevano (matrice viva e
-- filtro dalla mappa, manuale e azione da fn_doc_passaggio, permesso =>
-- nascondi), su ogni stato di ogni testata: righe di troppo o mancanti nei
-- due versi. Si contano anche gli stati provati, perche' un vocabolario
-- vuoto non passi per sottrazione.
CREATE FUNCTION pg_temp.scarti() RETURNS TABLE(provati integer, scarti integer)
LANGUAGE plpgsql AS $f$
DECLARE
    v_testata regclass;
    v_m       record;
    v_stato   bigint;
    v_utente  integer := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    v_n       integer;
BEGIN
    provati := 0; scarti := 0;
    FOREACH v_testata IN ARRAY ARRAY['vendite.preventivi', 'vendite.offerte_commerciali',
                                     'vendite.contratti', 'vendite.ordini', 'vendite.ddt',
                                     'vendite.resi', 'vendite.commesse',
                                     'vendite.fatturazione_lotti']::regclass[]
    LOOP
        SELECT * INTO v_m FROM script.fn_doc_stato_modello(v_testata);
        FOR v_stato IN EXECUTE format('SELECT s.id FROM %s s', v_m.vocabolario) LOOP
            EXECUTE format(
                'WITH prima AS (
                     SELECT t.%2$I::bigint AS a, pz.azione_processo_codename AS az
                       FROM %3$s t
                       CROSS JOIN LATERAL script.fn_doc_passaggio($1, t.%1$I, t.%2$I) pz
                      WHERE t.%1$I = $2 AND t.%4$I IS TRUE %5$s
                        AND pz.manuale IS TRUE
                        AND (pz.azione_processo_codename IS NULL
                             OR script.fn_check_azione_processo($3, pz.azione_processo_codename))),
                      dopo AS (
                     SELECT d.stato_a_id AS a, d.azione_processo_codename AS az
                       FROM script.fn_doc_azioni_permesse($1, $2) d)
                 SELECT count(*)::integer FROM (
                     (SELECT * FROM prima EXCEPT ALL SELECT * FROM dopo)
                     UNION ALL
                     (SELECT * FROM dopo EXCEPT ALL SELECT * FROM prima)) x',
                v_m.colonna_da, v_m.colonna_a, v_m.matrice, v_m.colonna_vivo, v_m.filtro)
               INTO v_n
              USING v_testata, v_stato, v_utente;
            provati := provati + 1;
            scarti  := scarti + v_n;
        END LOOP;
    END LOOP;
    RETURN NEXT;
END
$f$;

-- 2-3) Senza concessioni
SELECT is(pg_temp.chiavi((SELECT lotto_id FROM t_emesso)), '',
    'lotto EMESSA senza numera_fatture_lotti: nessun passaggio permesso');

SELECT is(
    (SELECT string_agg(a.action_key || ':' || COALESCE(a.azione_processo_codename, '-'), ' ')
       FROM vendite.fatturazione_lotti l,
            script.fn_doc_azioni_permesse('vendite.fatturazione_lotti'::regclass, l.stato_doc_fiscale_id) a
      WHERE l.id = (SELECT lotto_id FROM t_draft)),
    'annulla:-',
    'lotto DRAFT senza concessioni: annulla, una riga senza azione (decide il livello sul documento)'
);

-- 4) Equivalenza, senza concessioni
SELECT ok(
    (SELECT s.provati > 0 AND s.scarti = 0 FROM pg_temp.scarti() s),
    'senza concessioni: la stessa risposta del predicato di prima su ogni stato delle otto testate'
);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'numera_fatture_lotti');

-- 5-6) Con l'azione
SELECT is(pg_temp.chiavi((SELECT lotto_id FROM t_emesso)), 'numera riporta_a_draft',
    'lotto EMESSA con numera_fatture_lotti: numera e riporta in bozza');

SELECT is(
    (SELECT string_agg(DISTINCT a.azione_processo_codename, ' ')
       FROM vendite.fatturazione_lotti l,
            script.fn_doc_azioni_permesse('vendite.fatturazione_lotti'::regclass, l.stato_doc_fiscale_id) a
      WHERE l.id = (SELECT lotto_id FROM t_emesso)),
    'numera_fatture_lotti',
    'i due passaggi del lotto emesso chiedono numera_fatture_lotti'
);

-- 7) Equivalenza, con la concessione
SELECT ok(
    (SELECT s.provati > 0 AND s.scarti = 0 FROM pg_temp.scarti() s),
    'con numera_fatture_lotti: la stessa risposta del predicato di prima su ogni stato delle otto testate'
);

-- 8-9) Stato NULL, testata fuori mappa
SELECT is(
    (SELECT count(*)::integer FROM script.fn_doc_azioni_permesse('vendite.ordini'::regclass, NULL)),
    0,
    'stato NULL: nessuna riga'
);

SELECT throws_like(
    $$SELECT * FROM script.fn_doc_azioni_permesse('config.sorgenti'::regclass, 1)$$,
    'Chiamata non valida a script.fn_doc_azioni_permesse%',
    'fn_doc_azioni_permesse: una tabella fuori dalla mappa -> chiamata non valida'
);

-- 10-11) I due vincoli
SELECT throws_ok(
    $$UPDATE config.transizioni_stati_ordini t SET meta = t.meta - 'manuale'
       WHERE t.id = (SELECT min(x.id) FROM config.transizioni_stati_ordini x)$$,
    '23514',
    NULL,
    'una riga di matrice senza meta.manuale: rifiutata (ck_*_meta_manuale_dichiarato)'
);

SELECT throws_ok(
    $$UPDATE config.stati_doc_fiscale_transizioni t
         SET meta = t.meta || '{"tipo_lotto": "GIORNALIERO"}'::jsonb
       WHERE t.id = (SELECT min(x.id) FROM config.stati_doc_fiscale_transizioni x
                      WHERE (x.meta ->> 'manuale')::boolean)$$,
    '23514',
    NULL,
    'tipo_lotto su un passaggio manuale: rifiutato (ck_stati_doc_fiscale_transizioni_tipo_lotto_solo_processo)'
);

SELECT * FROM finish();
ROLLBACK;
