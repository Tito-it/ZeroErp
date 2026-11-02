-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.trgfn_guard_emittente_scope — la porta chiusa dalla fase 6
-- Brief: brief-db-processi-automatici-identita-e-perimetro §7
--
-- Elenco test (plan 10):
--  1) il guard esiste ed e' SECURITY INVOKER
--  2) ⭐ IL PRESUPPOSTO: questa sessione SUBISCE la row level security
--  3) ✅ operatore nel proprio perimetro: la scrittura passa
--  4) ⛔ stessa scrittura senza utente in sessione: si ferma
--  5) ⛔ e si ferma col codice giusto, non con uno qualsiasi
--  6) ✅ un emittente FUORI perimetro continua a dare E_SCOPE_EMITTENTE
--  7) ⭐ rev 2026-09-18 (magazzino Lotto 2, C1): una DEFINER del proprietario
--     chiamata SENZA identita' scrive una riga SENZA padrone (email di sistema,
--     emittente NULL) e PASSA — il caso su cui il reset password conta
--  8) ...ma la stessa DEFINER dentro il ramo «senza padrone» non e' la porta:
--     la regola e' che row_security_active dentro una DEFINER risponde per il
--     proprietario, e il guard lo sa (la funzione lo dichiara nel corpo)
--  9) ✅ rev 2026-10-04 (Q-1): la LETTURA nel proprio perimetro vede l'ordine
--     del test 3 — il controllo del 10
-- 10) ⛔ la stessa lettura con la veste OPERATORE e l'utente vuoto non vede
--     niente: prima la policy rispondeva «tutto» (utente NULL = job batch)
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

SELECT plan(10);

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
-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-1): fino a questo giorno gli
--   ordini nascevano con billing_account_id = NULL «cosi' non c'e' il guard di
--   coerenza emittente<->BA da soddisfare». L'ordine senza BA non esiste piu'.
--   Ora il cliente si FABBRICA, col BA legato dal trigger z90 all'emittente
--   dell'operatore: il guard emittente<->BA e' soddisfatto, e resta in prova
--   SOLO il guard di scope (test 3-5, 9-10). Il test 6 (emittente ALTRUI) passa
--   su un DDT senza BA: su un ordine parlerebbe prima il guard emittente<->BA.
CREATE TEMP TABLE tmp_gsu_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guard emittente senza utente');
SET CONSTRAINTS ALL IMMEDIATE;

-- L'emittente e' quello su cui l'operatore di contesto puo' davvero scrivere.
CREATE TEMP TABLE tmp_gsu_refs AS
SELECT
    (SELECT c.soggetto_ruolo_id FROM tmp_gsu_cli c)
        AS soggetto_ruolo_id,
    (SELECT c.billing_account_id FROM tmp_gsu_cli c)
        AS billing_account_id,
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
      SELECT r.soggetto_ruolo_id, r.billing_account_id, r.emittente_fiscale_id,
             r.stato_draft_id, r.valuta_id, script.fn_data_operativa(), false,
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
      SELECT r.soggetto_ruolo_id, r.billing_account_id, r.emittente_fiscale_id,
             r.stato_draft_id, r.valuta_id, script.fn_data_operativa(), false,
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
      SELECT r.soggetto_ruolo_id, r.billing_account_id, r.emittente_fiscale_id,
             r.stato_draft_id, r.valuta_id, script.fn_data_operativa(), false,
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
        -- rev 2026-10-09: su un DDT SENZA BA (in bozza, senza causale: il
        --   destinatario e' libero), perche' il guard emittente<->BA esca
        --   subito e a parlare sia SOLO lo scope. Su un ordine, che il BA ce
        --   l'ha sempre, parlerebbe prima lui (b < s) e il test diventerebbe
        --   verde per la ragione sbagliata.
        $$INSERT INTO vendite.ddt (
              destinatario_soggetto_ruolo_id, stato_doc_ddt_id, emittente_fiscale_id,
              storicizza, meta
          )
          SELECT r.soggetto_ruolo_id,
                 (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'DRAFT'),
                 r.emittente_altrui_id, false,
                 jsonb_build_object('test_scope', 'pgtap_guard_senza_utente')
            FROM tmp_gsu_refs r$$,
        'P0001',
        NULL,
        '6. emittente fuori perimetro: si ferma per SCOPE, non per identita'''
    )
END;

-- ============================================================
-- 7..8) ⭐ Dentro una DEFINER (rev 2026-09-18, C1 del Lotto 2 di magazzino)
-- ============================================================
-- row_security_active() risponde per il current_user, che dentro una SECURITY
-- DEFINER e' il PROPRIETARIO: false sempre. Provato il 18-09: la stessa riga
-- senza GUC era rifiutata diretta e passava via config.fn_accoda_email_sistema.
-- La rev del guard: dentro una DEFINER (current_user diverso dal ruolo di
-- sessione: il parametro role, o session_user se none — rev 2026-10-15,
-- 20261015-06, perche' un utente personale che lavora come proprietario con
-- SET role non e' una DEFINER), senza
-- identita', si risolve comunque l'emittente e ci si ferma se la riga HA un
-- padrone; una riga SENZA padrone passa come prima — ed e' il caso delle email
-- di sistema (emittente NULL), da cui dipende il reset password senza sessione.
-- Il caso «con padrone» lo prova la primitiva di magazzino
-- (magazzino/test-porta-ledger-v1, test 13-14): qui si pinna che il ramo
-- «senza padrone» NON si e' chiuso per sbaglio.
SELECT set_config('app.current_user_id', '', true);
SELECT lives_ok(
    $$SELECT config.fn_accoda_email_sistema('pgtap-guard@example.com', 'pgTAP guard senza utente', '<p>prova</p>')$$,
    '7. una DEFINER senza identita'' che scrive una riga SENZA padrone (email di sistema) passa'
);
SELECT ok(
    (SELECT pg_get_functiondef(p.oid) LIKE '%current_user = coalesce(nullif(current_setting(''role''), ''none''), session_user)%'
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'trgfn_guard_emittente_scope'),
    '8. il guard distingue «dentro una DEFINER» (current_user diverso dal ruolo di sessione): la rev C1 e'' in servizio'
);
DO $ctx3$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx3$;

-- ============================================================
-- 9..10) ⛔ La lettura senza utente (rev 2026-10-04, Q-1)
-- ============================================================
-- Fino al 2026-10-04 script.fn_check_user_emittente_scope rispondeva TRUE con
-- l'utente NULL («job batch»): la policy rls_ordini_ef_whitelist restava
-- chiusa solo per la veste, e una sessione con la veste OPERATORE e l'utente
-- vuoto vedeva gli ordini di TUTTE le aziende. La scrittura l'aveva chiusa la
-- fase 6 (test 4-5); qui si prova la lettura, che e' rimasta indietro un mese.
-- Il 9 e' il controllo: senza, un 10 verde potrebbe venire da un ordine mai
-- scritto.
SELECT is(
    (SELECT count(*)::int FROM vendite.ordini o
      WHERE o.meta ->> 'test_scope' = 'pgtap_guard_senza_utente'),
    1,
    '9. operatore nel proprio perimetro: vede l''ordine del test 3'
);

SELECT set_config('app.current_user_id', '', true);
SELECT is(
    (SELECT count(*)::int FROM vendite.ordini o
      WHERE o.meta ->> 'test_scope' = 'pgtap_guard_senza_utente'),
    0,
    '10. veste OPERATORE e utente vuoto: la policy non vede niente (era: tutte le aziende)'
);
DO $ctx4$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx4$;

SELECT * FROM finish();

ROLLBACK;
