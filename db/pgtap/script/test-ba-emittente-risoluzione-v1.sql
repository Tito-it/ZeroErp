-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Fase E del cantiere «perimetro emittente», R-5: la risoluzione
--   «quale emittente fattura questo billing account?»
-- Brief: brief-db-perimetro-emittente-fase-e-e-ricerca.md
-- ⭐ Rev 2026-09-13 (D13, brief-db-ba-riserva-emittente-operatore-d13.md):
--   la regola ha TRE livelli — il test 4 si spezza in due (in sessione /
--   senza sessione) e il mondo SI COSTRUISCE invece di cercarlo: il file
--   stava nel registro dei rossi della CI perche' la fixture pescava un
--   mapping esistente, e su un database ricostruito dai changelog non ce n'e'.
--
-- Elenco test (plan 14):
--   0) PRECONDIZIONE: il BA costruito e' legato a B, e B NON e' il default
--   1) script.fn_get_ba_emittente_sr_id esiste
--   2) * BA NULL -> NULL, e NON un emittente
--   3) BA con mapping specifico -> quell'emittente (livello 1)
--   4) ⭐ BA senza mapping, IN SESSIONE -> l'emittente dell'operatore (livello 2)
--   5) ⭐ BA senza mapping, SENZA sessione -> l'emittente di default (livello 3)
--   6) * equivalenza col check: l'emittente risolto E' fra i visibili
--   7) equivalenza rovescia: un emittente estraneo NON rende visibile
--   8) fail-closed: scope '{}' -> false
--   9) fail-closed: scope NULL -> false
--  10) * BA NULL + scope valido -> false (il buco che il CASE chiude)
--  11) legacy script.fn_get_emittenti_scope: DISMESSA
--  12) la ricerca universale DICHIARA emittente_ragione_sociale
--  13) ...e la colonna e' davvero interrogabile
--
-- Scopo, e perche' i test con l'asterisco sono quelli che contano:
--
--  ⭐ Il 6 e il 7 sono la ragione per cui questo file esiste. Il changeSet
--     20260818-59 ha fatto delegare fn_check_ba_visible_for_emittenti alla
--     nuova funzione, cioe' ha sostituito DUE EXISTS con una risoluzione + un
--     confronto. L'equivalenza e' dimostrabile a tavolino (i due indici
--     univoci uq_emittenti_fiscali_ba e uq_emittenti_fiscali_ba_default), ma
--     una dimostrazione non e' un presidio: se domani qualcuno togliesse uno
--     dei due indici, la dimostrazione cadrebbe e nessuno se ne accorgerebbe.
--     Qui l'equivalenza si esercita su dati costruiti.
--
--  ⚠️ Il 2 e il 10 sono la stessa trappola vista da due lati, ed e' la piu'
--     insidiosa dell'intera estrazione. La regola ha una riserva: «BA senza
--     mapping -> l'emittente di chi agisce, altrimenti il default». Un billing
--     account NULLO non e' un BA senza mapping: e' l'ASSENZA di un billing
--     account. Se la riserva scattasse anche li', un cliente senza BA
--     risulterebbe fatturato da un emittente — e quindi VISIBILE a chi ha quel
--     emittente in whitelist. Sarebbe un fail-open, e silenzioso: piu' righe
--     del dovuto non danno errore. Il CASE in testa alla funzione esiste solo
--     per questo, e senza questi due test nessuno saprebbe che serve.
--
--  ⭐ Il 4 e il 5 sono la coppia nuova (D13). Fino al 20260913-01 la riserva
--     era UNA — il default — e il test 4 lo pinnava CON il contesto operatore
--     aperto: passava perche' l'operatore di contesto era quello del default,
--     cioe' per coincidenza. Ora la riserva in sessione e' l'emittente di chi
--     agisce (la stessa risposta che il trigger z90 sta per scrivere), e il
--     default resta per chi una sessione non ce l'ha. Le due asserzioni si
--     distinguono solo se l'operatore di contesto NON e' quello del default:
--     per questo le aziende costruite sono DUE e il contesto e' quello della
--     seconda — sullo scratch della CI la prima creata diventa il default per
--     bootstrap, su dbdev il default e' un terzo. Il test 0 lo asserisce.
--
--  ⚠️ Il 11 e' un presidio anti-resurrezione, non un test di comportamento.
--     Vive anche in test-permessi-fn-check-emittente-scope.sql e in
--     test-permessi-funzioni-risoluzione.sql: e' voluto che sia in tre posti.
-- ------------------------------------------------------------

BEGIN;

-- ⛔ LE DUE AZIENDE SI COSTRUISCONO, in DUE istruzioni: l'ordine di creazione
--   e' portante (sullo scratch la prima diventa il default) e in una UNION
--   ALL l'ordine dei rami e' del planner, non del test.
CREATE TEMP TABLE _mondi AS
SELECT 'A'::text AS lato, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

INSERT INTO _mondi
SELECT 'B'::text, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- Contesto applicativo: l'operatore di B (ruolo OPERATORE + RLS attiva).
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'B'));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
-- Un cliente costruito NEL contesto di B: il legame lo scrive il trigger z90
-- verso l'emittente di chi agisce (l'helper, dalla rev 20260912-38, lo
-- rispetta). E' il mapping SPECIFICO che i test 3, 6 e 7 esercitano.
CREATE TEMP TABLE _t_cli ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('risoluzione emittente');

CREATE TEMP TABLE _t_map ON COMMIT DROP AS
SELECT efba.billing_account_id          AS ba_id,
       efba.emittente_soggetto_ruolo_id AS ef_sr_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba
  JOIN _t_cli c ON c.billing_account_id = efba.billing_account_id
 WHERE efba.is_default IS FALSE;

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

-- Un billing_account_id che NON esiste: serve a esercitare la RISERVA senza
-- leggere anagrafiche.billing_account, che ha RLS — sotto contesto operatore
-- un conteggio li' sopra misurerebbe la RLS, non i mapping.
CREATE TEMP TABLE _t_ba_ignoto ON COMMIT DROP AS
SELECT COALESCE(MAX(efba.billing_account_id), 0) + 1000000 AS ba_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 0) Senza un mapping specifico verso B i test 3, 6 e 7 sarebbero vacui; e
--    senza «B non e' il default» i test 4 e 5 direbbero la stessa cosa.
SELECT ok(
    (SELECT ef_sr_id FROM _t_map) = (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B')
    AND (SELECT ef_sr_id FROM _t_def) IS DISTINCT FROM (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
    '0. PRECONDIZIONE: il BA costruito e'' legato a B, e B non e'' l''emittente di default'
);

SELECT has_function(
    'script', 'fn_get_ba_emittente_sr_id', ARRAY['bigint'],
    '1. script.fn_get_ba_emittente_sr_id esiste'
);

-- 2) * «Nessun billing account» NON e' «billing account non ancora collegato».
SELECT is(
    script.fn_get_ba_emittente_sr_id(NULL::bigint),
    NULL::bigint,
    '2. * BA NULL -> NULL: l''assenza di BA non cade nella riserva'
);

-- 3) Livello 1: il mapping specifico vince.
SELECT is(
    script.fn_get_ba_emittente_sr_id((SELECT ba_id FROM _t_map)),
    (SELECT ef_sr_id FROM _t_map),
    '3. BA con mapping specifico -> quell''emittente (livello 1)'
);

-- 4) ⭐ Livello 2 (D13): un BA senza mapping, in sessione, e' di chi agisce.
SELECT is(
    script.fn_get_ba_emittente_sr_id((SELECT ba_id FROM _t_ba_ignoto)),
    (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
    '4. * BA senza mapping, IN SESSIONE -> l''emittente dell''operatore (livello 2), non il default'
);

-- 5) ⭐ Livello 3: senza sessione la riserva e' ancora il default, qualunque
--    esso sia. Si svuota la sola GUC dell'utente (transazionale) e la si
--    rimette subito dopo: i test seguenti vogliono il contesto di B.
SELECT set_config('app.current_user_id', '', true);

SELECT is(
    script.fn_get_ba_emittente_sr_id((SELECT ba_id FROM _t_ba_ignoto)),
    (SELECT ef_sr_id FROM _t_def),
    '5. * BA senza mapping, SENZA sessione -> l''emittente di default (livello 3)'
);

SELECT set_config('app.current_user_id',
                  (SELECT auth_user_id::text FROM _mondi WHERE lato = 'B'),
                  true);

-- 6) * L'equivalenza con il check, dal lato che deve dire SI'.
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        (SELECT ba_id FROM _t_map),
        ARRAY[(SELECT ef_sr_id FROM _t_map)]::bigint[]
    ),
    true,
    '6. * l''emittente RISOLTO rende il BA visibile: il check e la risoluzione dicono la stessa cosa'
);

-- 7) ...e dal lato che deve dire NO.
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        (SELECT ba_id FROM _t_map),
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[]
    ),
    false,
    '7. un emittente estraneo NON rende il BA visibile'
);

-- 8) Scope vuoto = «nessun emittente autorizzato». Non «nessuna restrizione».
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        (SELECT ba_id FROM _t_map),
        '{}'::bigint[]
    ),
    false,
    '8. scope ''{}'' -> false (fail-closed: vuoto non degrada a "tutti")'
);

-- 9) Scope NULL su questa funzione = nessun autorizzato, e non «tutti»: la
--    convenzione a tre stati si legge nel CHIAMANTE, non qui.
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        (SELECT ba_id FROM _t_map),
        NULL::bigint[]
    ),
    false,
    '9. scope NULL -> false: la convenzione a tre stati la legge il chiamante'
);

-- 10) * Il rovescio del test 2, dal lato che conta davvero: se il BA nullo
--     cadesse nella riserva, un cliente SENZA billing account risulterebbe
--     visibile a chi ha in whitelist l'emittente di chi agisce, o il default.
SELECT is(
    script.fn_check_ba_visible_for_emittenti(
        NULL::bigint,
        ARRAY[(SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
              COALESCE((SELECT ef_sr_id FROM _t_def), (SELECT ef_sr_id FROM _t_map))]::bigint[]
    ),
    false,
    '10. * BA NULL non e'' visibile nemmeno per l''operatore in sessione o per il default (niente fail-open)'
);

-- 11) Presidio anti-resurrezione della legacy fail-open.
SELECT hasnt_function(
    'script', 'fn_get_emittenti_scope', ARRAY['integer'],
    '11. legacy fn_get_emittenti_scope: DISMESSA (era «senza whitelist -> tutti gli emittenti»)'
);

-- 12) R-5: la colonna e' DICHIARATA nel contratto della funzione.
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
    '12. la ricerca universale dichiara emittente_ragione_sociale nel RETURNS TABLE (R-5)'
);

-- 13) ...e la colonna e' interrogabile per nome. Dichiararla e non poterla
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
    '13. la colonna emittente_ragione_sociale e'' interrogabile per nome'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
