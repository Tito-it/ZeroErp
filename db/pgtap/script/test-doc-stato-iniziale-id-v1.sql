-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_doc_stato_iniziale_id, lo stato iniziale dalla testata
--   Il lettore dalla testata (20261027-29), gemello di fn_stato_emissione_id
--   e fn_stato_abortito_id, che delega la regola a fn_stato_iniziale_id.
--   Brief: brief-modello-documento-vendita §15.13 (richiesta del team BE
--   sul §15.8 punto 3, Tid 2026-10-27).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - testata della mappa: l'id dello stato che il suo vocabolario dichiara
--     iniziale; il lotto di fatturazione, lo stato a cui «riporta in bozza»;
--   - la stessa risposta di fn_stato_iniziale_id(vocabolario della mappa),
--     su ogni testata della mappa (nessuna regola ricopiata);
--   - vocabolario che non dichiara uno stato iniziale: NULL;
--   - testata fuori mappa, o NULL: chiamata non valida.
--
-- Elenco test (plan 6):
--   1) il lettore esiste: STABLE, SECURITY INVOKER
--   2) lotto di fatturazione: lo stato iniziale che config.stati_doc_fiscale dichiara
--   3) ogni testata della mappa: la risposta del lettore dal vocabolario, mai NULL
--   4) testata fuori mappa -> chiamata non valida
--   5) testata NULL -> chiamata non valida
--   6) vocabolario senza stato iniziale dichiarato -> NULL
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- 1) L'oggetto e la sua forma
SELECT is(
    (SELECT p.provolatile::text || ' ' || p.prosecdef::text
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_doc_stato_iniziale_id'),
    's false',
    'script.fn_doc_stato_iniziale_id esiste: STABLE, SECURITY INVOKER'
);

-- 2) Il caso della richiesta: il lotto, stato di arrivo di «riporta in
--    bozza». Lo stato atteso e' quello che il vocabolario dichiara, non un
--    codice scritto qui.
SELECT is(
    script.fn_doc_stato_iniziale_id('vendite.fatturazione_lotti'::regclass),
    (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.iniziale),
    'lotto di fatturazione: lo stato iniziale dichiarato da config.stati_doc_fiscale'
);

-- 3) Ogni testata della mappa: stessa risposta del lettore dal vocabolario,
--    e mai NULL (ogni vocabolario della mappa dichiara il suo stato iniziale:
--    lo pretende il trigger della nascita). Si contano le testate provate,
--    perche' una lista vuota non passi per sottrazione.
SELECT is(
    (SELECT count(*)::integer
       FROM (VALUES ('vendite.preventivi'::regclass), ('vendite.offerte_commerciali'),
                    ('vendite.contratti'), ('vendite.ordini'), ('vendite.ddt'),
                    ('vendite.resi'), ('vendite.commesse'), ('vendite.fatture'),
                    ('vendite.fatturazione_lotti')) t(testata)
       CROSS JOIN LATERAL script.fn_doc_stato_modello(t.testata) m
      WHERE script.fn_doc_stato_iniziale_id(t.testata) IS NOT NULL
        AND script.fn_doc_stato_iniziale_id(t.testata)
            = script.fn_stato_iniziale_id(m.vocabolario)),
    9,
    'le nove testate della mappa: lo stato iniziale del loro vocabolario (fn_stato_iniziale_id), mai NULL'
);

-- 4-5) Fuori mappa
SELECT throws_like(
    $$SELECT script.fn_doc_stato_iniziale_id('config.sorgenti'::regclass)$$,
    'Chiamata non valida a script.fn_doc_stato_iniziale_id%',
    'fn_doc_stato_iniziale_id: una tabella fuori dalla mappa -> chiamata non valida'
);

SELECT throws_like(
    $$SELECT script.fn_doc_stato_iniziale_id(NULL)$$,
    'Chiamata non valida a script.fn_doc_stato_iniziale_id%',
    'fn_doc_stato_iniziale_id: testata NULL -> chiamata non valida'
);

-- 6) Un vocabolario che non dichiara lo stato iniziale, costruito qui: si
--    spegne la colonna iniziale del preventivo dentro la transazione del test.
UPDATE config.stati_doc_preventivi SET iniziale = false WHERE iniziale;

SELECT ok(
    script.fn_doc_stato_iniziale_id('vendite.preventivi'::regclass) IS NULL,
    'fn_doc_stato_iniziale_id: vocabolario senza stato iniziale dichiarato -> NULL'
);

SELECT * FROM finish();
ROLLBACK;
