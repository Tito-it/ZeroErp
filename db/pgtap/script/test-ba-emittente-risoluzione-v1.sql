-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Fase E del cantiere «perimetro emittente», R-5: la risoluzione
--   «quale emittente fattura questo billing account?»
-- Brief: brief-db-perimetro-emittente-fase-e-e-ricerca.md
--
-- Elenco test (plan 13):
--   0) PRECONDIZIONE: esiste almeno un mapping BA->emittente da esercitare
--   1) script.fn_get_ba_emittente_sr_id esiste
--   2) * BA NULL -> NULL, e NON l'emittente di default
--   3) BA con mapping specifico -> quell'emittente (livello 1)
--   4) BA senza mapping -> l'emittente di default (livello 2)
--   5) * equivalenza col check: l'emittente risolto E' fra i visibili
--   6) equivalenza rovescia: un emittente estraneo NON rende visibile
--   7) fail-closed: scope '{}' -> false
--   8) fail-closed: scope NULL -> false
--   9) * BA NULL + scope valido -> false (il buco che il CASE chiude)
--  10) legacy script.fn_get_emittenti_scope: DISMESSA
--  11) la ricerca universale DICHIARA emittente_ragione_sociale
--  12) ...e la colonna e' davvero interrogabile
--
-- Scopo, e perche' i test con l'asterisco sono quelli che contano:
--
--  ⭐ Il 5 e il 6 sono la ragione per cui questo file esiste. Il changeSet
--     20260818-59 ha fatto delegare fn_check_ba_visible_for_emittenti alla
--     nuova funzione, cioe' ha sostituito DUE EXISTS con una risoluzione + un
--     confronto. L'equivalenza e' dimostrabile a tavolino (i due indici
--     univoci uq_emittenti_fiscali_ba e uq_emittenti_fiscali_ba_default), ma
--     una dimostrazione non e' un presidio: se domani qualcuno togliesse uno
--     dei due indici, la dimostrazione cadrebbe e nessuno se ne accorgerebbe.
--     Qui l'equivalenza si esercita sui dati veri.
--
--  ⚠️ Il 2 e il 9 sono la stessa trappola vista da due lati, ed e' la piu'
--     insidiosa dell'intera estrazione. La regola ha un fallback: «BA senza
--     mapping -> emittente di default». Un billing account NULLO non e' un BA
--     senza mapping: e' l'ASSENZA di un billing account. Se il fallback
--     scattasse anche li', un cliente senza BA risulterebbe fatturato
--     dall'emittente di default — e quindi VISIBILE a chi ha quel default in
--     whitelist. Sarebbe un fail-open, e silenzioso: piu' righe del dovuto non
--     danno errore. Il CASE in testa alla funzione esiste solo per questo, e
--     senza questi due test nessuno saprebbe che serve.
--
--  ⚠️ Il 4 e' scritto per NON essere data-dependent: confronta con
--     «qualunque cosa sia il default», non con un valore atteso. Se
--     sull'istanza non c'e' nessun emittente di default, entrambi i lati sono
--     NULL e il test passa dicendo il vero — non c'e' fallback da esercitare.
--
--  ⚠️ Il 10 e' un presidio anti-resurrezione, non un test di comportamento.
--     Vive anche in test-permessi-fn-check-emittente-scope.sql e in
--     test-permessi-funzioni-risoluzione.sql: e' voluto che sia in tre posti.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ ORDER BY obbligatorio: senza, quale mapping esca dipende dal piano e il
--   test verificherebbe una riga diversa a ogni corsa.
-- ⚠️ is_default IS FALSE: serve un mapping SPECIFICO, altrimenti il test 3
--   passerebbe anche col solo fallback e non distinguerebbe i due livelli.
CREATE TEMP TABLE _t_map ON COMMIT DROP AS
SELECT efba.billing_account_id          AS ba_id,
       efba.emittente_soggetto_ruolo_id AS ef_sr_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba
 WHERE efba.billing_account_id IS NOT NULL
   AND efba.is_default IS FALSE
 ORDER BY efba.billing_account_id
 LIMIT 1;

-- L'emittente di default, se c'e'. Al massimo uno: uq_emittenti_fiscali_ba_default.
CREATE TEMP TABLE _t_def ON COMMIT DROP AS
SELECT efba.emittente_soggetto_ruolo_id AS ef_sr_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba
 WHERE efba.is_default;

-- Un soggetto_ruolo_id che NON esiste: per costruzione estraneo a qualunque
-- mapping, senza dipendere da quanti emittenti ci siano sull'istanza.
CREATE TEMP TABLE _t_fuori ON COMMIT DROP AS
SELECT COALESCE(MAX(sr.id), 0) + 1000000 AS sr_id
  FROM anagrafiche.soggetti_ruoli sr;

-- Un billing_account_id che NON esiste: serve a esercitare il LIVELLO 2 senza
-- leggere anagrafiche.billing_account, che ha RLS — sotto contesto operatore
-- un conteggio li' sopra misurerebbe la RLS, non i mapping.
CREATE TEMP TABLE _t_ba_ignoto ON COMMIT DROP AS
SELECT COALESCE(MAX(efba.billing_account_id), 0) + 1000000 AS ba_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 0) Senza un mapping specifico i test 3, 5 e 6 sarebbero vacui.
SELECT ok(
    EXISTS (SELECT 1 FROM _t_map),
    '0. PRECONDIZIONE: esiste almeno un mapping BA->emittente specifico da esercitare'
);

SELECT has_function(
    'script', 'fn_get_ba_emittente_sr_id', ARRAY['bigint'],
    '1. script.fn_get_ba_emittente_sr_id esiste'
);

-- 2) * «Nessun billing account» NON e' «billing account non ancora mappato».
SELECT is(
    script.fn_get_ba_emittente_sr_id(NULL::bigint),
    NULL::bigint,
    '2. * BA NULL -> NULL: l''assenza di BA non cade nel fallback default'
);

-- 3) Livello 1: il mapping specifico vince.
SELECT is(
    script.fn_get_ba_emittente_sr_id((SELECT ba_id FROM _t_map)),
    (SELECT ef_sr_id FROM _t_map),
    '3. BA con mapping specifico -> quell''emittente (livello 1)'
);

-- 4) Livello 2: un BA senza mapping ricade sul default, qualunque esso sia.
--    ⚠️ Il confronto e' con «cio' che il default e'», non con un valore
--    atteso: se non c'e' default entrambi i lati sono NULL e il test dice
--    comunque il vero.
SELECT is(
    script.fn_get_ba_emittente_sr_id((SELECT ba_id FROM _t_ba_ignoto)),
    (SELECT ef_sr_id FROM _t_def),
    '4. BA senza mapping -> l''emittente di default (livello 2), o NULL se non ce n''e'''
);

-- 5) * L'equivalenza con il check, dal lato che deve dire SI'.
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        (SELECT ba_id FROM _t_map),
        ARRAY[(SELECT ef_sr_id FROM _t_map)]::bigint[]
    ),
    true,
    '5. * l''emittente RISOLTO rende il BA visibile: il check e la risoluzione dicono la stessa cosa'
);

-- 6) ...e dal lato che deve dire NO.
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        (SELECT ba_id FROM _t_map),
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[]
    ),
    false,
    '6. un emittente estraneo NON rende il BA visibile'
);

-- 7) Scope vuoto = «nessun emittente autorizzato». Non «nessuna restrizione».
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        (SELECT ba_id FROM _t_map),
        '{}'::bigint[]
    ),
    false,
    '7. scope ''{}'' -> false (fail-closed: vuoto non degrada a "tutti")'
);

-- 8) Scope NULL su questa funzione = nessun autorizzato, e non «tutti»: la
--    convenzione a tre stati si legge nel CHIAMANTE, non qui.
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        (SELECT ba_id FROM _t_map),
        NULL::bigint[]
    ),
    false,
    '8. scope NULL -> false: la convenzione a tre stati la legge il chiamante'
);

-- 9) * Il rovescio del test 2, dal lato che conta davvero: se il BA nullo
--    cadesse nel fallback, un cliente SENZA billing account risulterebbe
--    visibile a chi ha in whitelist l'emittente di default.
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        NULL::bigint,
        ARRAY[COALESCE((SELECT ef_sr_id FROM _t_def), (SELECT ef_sr_id FROM _t_map))]::bigint[]
    ),
    false,
    '9. * BA NULL non e'' visibile nemmeno per l''emittente di default (niente fail-open)'
);

-- 10) Presidio anti-resurrezione della legacy fail-open.
SELECT hasnt_function(
    'script', 'fn_get_emittenti_scope', ARRAY['integer'],
    '10. legacy fn_get_emittenti_scope: DISMESSA (era «senza whitelist -> tutti gli emittenti»)'
);

-- 11) R-5: la colonna e' DICHIARATA nel contratto della funzione.
-- ⚠️ `= ANY(<sottoquery>)` NON e' `= ANY(<array>)`: con una sottoquery a
--   destra, PostgreSQL confronta l'operando sinistro con ogni RIGA — e qui
--   ogni riga e' un text[], quindi tenta di leggere la stringa come letterale
--   di array e fallisce con «il letterale array non e' definito in modo
--   corretto». La forma giusta e' avere `proargnames` come RIFERIMENTO A
--   COLONNA dentro l'EXISTS: li' e' un array, e ANY e' quello che serve.
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'script'
           AND p.proname = 'fn_search_soggetti_universale'
           AND 'emittente_ragione_sociale' = ANY(p.proargnames)
    ),
    '11. la ricerca universale dichiara emittente_ragione_sociale nel RETURNS TABLE (R-5)'
);

-- 12) ...e la colonna e' interrogabile per nome. Dichiararla e non poterla
--     leggere sarebbe lo stesso difetto della colonna di catalogo senza vista.
CREATE TEMP TABLE _t_cl ON COMMIT DROP AS
SELECT tr.id AS tipo_ruolo_id
  FROM config.tipi_ruoli tr
 WHERE tr.codice_interno = 'CL';

SELECT lives_ok(
    format(
        $$SELECT emittente_ragione_sociale
            FROM script.fn_search_soggetti_universale('zzz', %s)$$,
        (SELECT tipo_ruolo_id FROM _t_cl)
    ),
    '12. la colonna emittente_ragione_sociale e'' interrogabile per nome'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
