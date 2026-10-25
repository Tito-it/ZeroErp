-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_doc_stato_codice, il gemello inverso di fn_doc_stato_id
--   Il lettore id -> codice dello stato (20261025-70), e la composizione che
--   usa «Emetti» del backend: fn_doc_stato_codice(t, fn_stato_emissione_id(t)).
--   Brief: brief-modello-documento-vendita §8.11 (V-1 di Tid, 2026-10-25).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - id -> codice: il codice_interno dello stato con quell'id nel vocabolario
--     della testata; NULL per un id NULL o che il vocabolario non ha;
--   - nessun filtro sugli attivi: uno stato spento rende il suo codice (il
--     rifiuto come destinazione e' del verbo, con fn_doc_stato_id);
--   - andata e ritorno con fn_doc_stato_id su ogni stato attivo delle otto
--     testate di vendita;
--   - il codice dello stato di emissione e' quello che il vocabolario dichiara,
--     nei cinque documenti che si emettono; NULL per un documento che non si
--     emette;
--   - testata fuori mappa: chiamata non valida.
--
-- Elenco test (plan 8):
--   1) il lettore esiste: STABLE, SECURITY INVOKER
--   2) l'emissione composta, sulle cinque testate: il codice dichiarato dal vocabolario
--   3) l'emissione composta su reso, commessa e fattura: NULL
--   4) andata e ritorno su ogni stato attivo delle otto testate (e ce ne sono)
--   5) un id che il vocabolario non ha -> NULL
--   6) un id NULL -> NULL
--   7) uno stato spento rende il suo codice (nessun filtro sugli attivi)
--   8) testata fuori mappa -> chiamata non valida
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- 1) L'oggetto e la sua forma
SELECT is(
    (SELECT p.provolatile::text || ' ' || p.prosecdef::text
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_doc_stato_codice'),
    's false',
    'script.fn_doc_stato_codice esiste: STABLE, SECURITY INVOKER'
);

-- 2) La composizione di «Emetti»: il codice letto dalla colonna emissione di
--    ogni vocabolario, non scritto qui.
SELECT is(
    (SELECT string_agg(t.nome || ':' || COALESCE(
                script.fn_doc_stato_codice(t.testata, script.fn_stato_emissione_id(t.testata)), '-'),
                       ' ' ORDER BY t.nome)
       FROM (VALUES ('contratti',  'vendite.contratti'::regclass),
                    ('ddt',        'vendite.ddt'::regclass),
                    ('offerte',    'vendite.offerte_commerciali'::regclass),
                    ('ordini',     'vendite.ordini'::regclass),
                    ('preventivi', 'vendite.preventivi'::regclass)) t(nome, testata)),
    (SELECT string_agg(x, ' ' ORDER BY x) FROM (
        SELECT 'contratti:' || codice_interno AS x FROM config.stati_doc_contratti WHERE emissione
        UNION ALL SELECT 'ddt:' || codice_interno FROM config.stati_doc_ddt WHERE emissione
        UNION ALL SELECT 'offerte:' || codice_interno FROM config.stati_doc_offerte WHERE emissione
        UNION ALL SELECT 'ordini:' || codice_interno FROM config.stati_doc_ordini WHERE emissione
        UNION ALL SELECT 'preventivi:' || codice_interno FROM config.stati_doc_preventivi WHERE emissione) z),
    'fn_doc_stato_codice(t, fn_stato_emissione_id(t)): il codice di emissione che ogni vocabolario dichiara'
);

-- 3) Un documento che non si emette: niente codice
SELECT is(
    ARRAY[script.fn_doc_stato_codice('vendite.resi'::regclass,
                                     script.fn_stato_emissione_id('vendite.resi'::regclass)),
          script.fn_doc_stato_codice('vendite.commesse'::regclass,
                                     script.fn_stato_emissione_id('vendite.commesse'::regclass)),
          script.fn_doc_stato_codice('vendite.fatture'::regclass,
                                     script.fn_stato_emissione_id('vendite.fatture'::regclass))],
    ARRAY[NULL, NULL, NULL]::text[],
    'l''emissione composta su reso, commessa e fattura: NULL (non si emettono)'
);

-- 4) Andata e ritorno su ogni stato attivo delle otto testate di vendita. Il
--    vocabolario lo dice la mappa; si contano anche gli stati provati, perche'
--    un vocabolario vuoto non passi per sottrazione.
CREATE TEMP TABLE t_giro (testata regclass, provati integer, sbagliati integer);

DO $giro$
DECLARE
    v_testata regclass;
    v_voc     regclass;
    v_provati integer;
    v_sbagli  integer;
BEGIN
    FOREACH v_testata IN ARRAY ARRAY['vendite.preventivi', 'vendite.offerte_commerciali',
                                     'vendite.contratti', 'vendite.ordini', 'vendite.ddt',
                                     'vendite.resi', 'vendite.commesse', 'vendite.fatture']::regclass[]
    LOOP
        SELECT m.vocabolario INTO v_voc FROM script.fn_doc_stato_modello(v_testata) m;
        EXECUTE format(
            'SELECT count(*)::integer,
                    count(*) FILTER (WHERE script.fn_doc_stato_id($1,
                                         script.fn_doc_stato_codice($1, s.id)) IS DISTINCT FROM s.id)::integer
               FROM %s s WHERE s.attivo IS TRUE', v_voc)
           INTO v_provati, v_sbagli
          USING v_testata;
        INSERT INTO t_giro VALUES (v_testata, v_provati, v_sbagli);
    END LOOP;
END
$giro$;

SELECT is(
    (SELECT count(*)::integer FROM t_giro WHERE provati > 0 AND sbagliati = 0),
    8,
    'andata e ritorno fn_doc_stato_id(t, fn_doc_stato_codice(t, id)) = id su ogni stato attivo delle otto testate'
);

-- 5-6) Un id che il vocabolario non ha, un id NULL
SELECT ok(
    script.fn_doc_stato_codice('vendite.preventivi'::regclass, -1) IS NULL,
    'fn_doc_stato_codice: un id che il vocabolario non ha -> NULL'
);

SELECT ok(
    script.fn_doc_stato_codice('vendite.preventivi'::regclass, NULL) IS NULL,
    'fn_doc_stato_codice: un id NULL -> NULL'
);

-- 7) Uno stato spento, costruito qui: nessun documento lo usa.
INSERT INTO config.stati_doc_preventivi (id, codice_interno, codice, descrizione, attivo,
                                         fase, pdf_mode, pdf_allow_allegati)
VALUES (990611, 'PGTAP_SPENTO_COD', 'PGTAP_SPENTO_COD', 'pgTAP stato spento', false,
        'CHIUSO', 'ARCHIVE', false);

SELECT is(
    script.fn_doc_stato_codice('vendite.preventivi'::regclass, 990611),
    'PGTAP_SPENTO_COD',
    'fn_doc_stato_codice: uno stato spento rende il suo codice (il rifiuto come destinazione e'' del verbo)'
);

-- 8) Testata fuori mappa
SELECT throws_like(
    $$SELECT script.fn_doc_stato_codice('config.sorgenti'::regclass, 1)$$,
    'Chiamata non valida a script.fn_doc_stato_codice%',
    'fn_doc_stato_codice: una tabella fuori dalla mappa -> chiamata non valida'
);

SELECT * FROM finish();
ROLLBACK;
