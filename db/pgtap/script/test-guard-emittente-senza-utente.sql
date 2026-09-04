-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.trgfn_guard_emittente_scope — la porta chiusa dalla fase 6
-- Brief: brief-db-processi-automatici-identita-e-perimetro §7
--
-- Elenco test (plan 6):
--  1) il guard esiste ed e' SECURITY INVOKER
--  2) ⭐ IL PRESUPPOSTO: questa sessione SUBISCE la row level security
--  3) ✅ operatore nel proprio perimetro: la scrittura passa
--  4) ⛔ stessa scrittura senza utente in sessione: si ferma
--  5) ⛔ e si ferma col codice giusto, non con uno qualsiasi
--  6) ✅ un emittente FUORI perimetro continua a dare E_SCOPE_EMITTENTE
--
-- Scopo:
--  - provare i TRE esiti che il guard deve distinguere, costruendoli: chi ha
--    perimetro passa, chi non ha identita' si ferma, chi ha identita' ma non
--    quel perimetro si ferma DIVERSAMENTE. Un test che ne provasse due su tre
--    lascerebbe fondere due casi che il codice tiene separati apposta;
--  - ⭐ e proteggere il test da se stesso col test 2. Il criterio del guard e'
--    `row_security_active()`: se questo file girasse da OWNER, quella funzione
--    risponderebbe false, il guard uscirebbe subito e i test 4-5 diventerebbero
--    VERDI PER SOTTRAZIONE — verdi perche' non e' successo niente. Il test 2
--    rende quel presupposto un'asserzione invece che una speranza.
--
-- ⚠️ Runner: APPLICATIVO (nessun marcatore `pgtap-runner`). E' il punto: il
--   guard nuovo distingue proprio fra chi passa dalla RLS e chi la subisce.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1) Il guard, e la sua postura
-- ============================================================
-- ⚠️ SECURITY INVOKER non e' un dettaglio: e' la ragione per cui la
--   risoluzione dell'emittente sta in una funzione separata (rev 2026-08-22).
--   Se qualcuno la trasformasse in DEFINER, il guard tornerebbe a leggere
--   fuori dalla row security e questo file deve dirlo.
SELECT ok(
    (SELECT NOT p.prosecdef
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname = 'trgfn_guard_emittente_scope'),
    '1. il guard esiste ed e'' SECURITY INVOKER'
);

-- ============================================================
-- 2) ⭐ IL PRESUPPOSTO DEL FILE
-- ============================================================
-- Il guard nuovo passa la mano a chi bypasserebbe comunque la RLS. Se questa
-- sessione fosse una di quelle — proprietario, superuser, BYPASSRLS — i test
-- 4 e 5 non proverebbero niente e sarebbero verdi lo stesso.
SELECT ok(
    row_security_active('vendite.ordini'::regclass),
    '2. questa sessione SUBISCE la RLS: i test 4-5 hanno senso'
);

-- ============================================================
-- Fixture: gli estremi per un ordine minimo
-- ============================================================
-- ⚠️ billing_account_id = NULL apposta: cosi' non c'e' il guard di coerenza
--   emittente<->BA da soddisfare, e resta in prova SOLO il guard di scope.
-- L'emittente e' quello su cui l'operatore di contesto puo' davvero scrivere.
CREATE TEMP TABLE tmp_gsu_refs AS
SELECT
    (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1)
        AS soggetto_ruolo_id,
    script.fn_pgtap_emittente_operatore()
        AS emittente_fiscale_id,
    -- L'ALTRO emittente attivo: serve al test 6. Puo' mancare, e in quel caso
    -- il test 6 si dichiara saltato invece di fingere.
    (SELECT ef.id
       FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo
        AND ef.id <> script.fn_pgtap_emittente_operatore()
      ORDER BY ef.id LIMIT 1)
        AS emittente_altrui_id,
    (SELECT s.id FROM config.stati_doc_ordini s
      WHERE s.codice_interno = 'DRAFT' AND s.attivo ORDER BY s.id LIMIT 1)
        AS stato_draft_id,
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)
        AS valuta_id;

-- ============================================================
-- 3) ✅ Nel proprio perimetro si scrive
-- ============================================================
-- Prima del rifiuto va provato il consenso: un guard che nega tutto passerebbe
-- i test 4 e 5 senza essere corretto.
SELECT lives_ok(
    $$INSERT INTO vendite.ordini (
          soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
          stato_doc_ordine_id, valuta_id, data, storicizza, meta
      )
      SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,
             r.stato_draft_id, r.valuta_id, CURRENT_DATE, false,
             jsonb_build_object('test_scope', 'pgtap_guard_senza_utente')
        FROM tmp_gsu_refs r$$,
    '3. operatore nel proprio perimetro: la scrittura passa'
);

-- ============================================================
-- 4..5) ⛔ Senza utente in sessione ci si ferma
-- ============================================================
-- ⭐ Questo e' il caso che la fase 6 esiste per chiudere: fino al 2026-09-04
--   svuotare questa GUC bastava a spegnere il guard, e un processo automatico
--   scriveva su qualunque emittente senza dire chi fosse.
SELECT set_config('app.current_user_id', '', true);

SELECT throws_ok(
    $$INSERT INTO vendite.ordini (
          soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
          stato_doc_ordine_id, valuta_id, data, storicizza, meta
      )
      SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,
             r.stato_draft_id, r.valuta_id, CURRENT_DATE, false,
             jsonb_build_object('test_scope', 'pgtap_guard_senza_utente')
        FROM tmp_gsu_refs r$$,
    'P0001',
    NULL,
    '4. senza utente in sessione la scrittura si ferma'
);

-- ⚠️ Il test 4 da solo non basta: TUTTI gli errori applicativi passano da
--   script.fn_log_and_raise_error e sono P0001, quindi `throws_ok` sarebbe
--   verde anche se a fermare la riga fosse un guard qualunque. Qui si chiede
--   il MESSAGGIO, che nomina il codice di questa fase e non di un altro.
SELECT throws_ok(
    $$INSERT INTO vendite.ordini (
          soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
          stato_doc_ordine_id, valuta_id, data, storicizza, meta
      )
      SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,
             r.stato_draft_id, r.valuta_id, CURRENT_DATE, false,
             jsonb_build_object('test_scope', 'pgtap_guard_senza_utente')
        FROM tmp_gsu_refs r$$,
    'P0001',
    'Scrittura su vendite.ordini senza un utente in sessione: il processo non dichiara chi agisce.',
    '5. e si ferma con E_SCOPE_SENZA_UTENTE, non con un errore qualsiasi'
);

-- ============================================================
-- 6) ✅ L'altro rifiuto resta distinto
-- ============================================================
-- Non-regressione: un utente NOTO che tocca l'emittente di un altro deve
-- continuare a prendere E_SCOPE_EMITTENTE. ⛔ Se i due casi collassassero in
-- uno, chi legge il log non saprebbe piu' se manca l'identita' o il permesso.
DO $ctx2$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx2$;

SELECT CASE
    WHEN (SELECT emittente_altrui_id IS NULL FROM tmp_gsu_refs)
        THEN skip('6. un solo emittente attivo: il caso «perimetro altrui» '
                  'non e'' costruibile su questo database', 1)
    ELSE throws_ok(
        $$INSERT INTO vendite.ordini (
              soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
              stato_doc_ordine_id, valuta_id, data, storicizza, meta
          )
          SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_altrui_id,
                 r.stato_draft_id, r.valuta_id, CURRENT_DATE, false,
                 jsonb_build_object('test_scope', 'pgtap_guard_senza_utente')
            FROM tmp_gsu_refs r$$,
        'P0001',
        NULL,
        '6. emittente fuori perimetro: si ferma per SCOPE, non per identita'''
    )
END;

SELECT * FROM finish();

ROLLBACK;
