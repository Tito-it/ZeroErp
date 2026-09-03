-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: RLS FUNZIONALE su vendite.fatture_stampa_coda
--       policy rls_fatture_stampa_coda_ef_whitelist (changeset 20260904-05/06)
--       Piano: brief-db-archiviazione-righe-code, PARTE DB sezione 8
--
-- ⭐ PERCHE' FUNZIONALE, e perche' gira come L'APPLICAZIONE.
--   Questa policy non e' pre-armata come quelle dei satelliti fattura: nasce
--   perche' il verbo «Archivia» e' la PRIMA SCRITTURA DELL'OPERATORE su questa
--   tabella. C'e' quindi un percorso applicativo vero da esercitare, e il test
--   lo esercita da li' — niente `pgtap-runner: owner`, niente FORCE locale:
--   zeroerp_app non e' owner ed e' NOBYPASSRLS, quindi la policy morde da sola.
--
-- ⚠️ IL TEST 7 E' L'UNICO MODO ONESTO DI PROVARE IL FAIL-CLOSED, e la forma
--   conta. Si svuota `app.ruolo_applicativo`, NON `app.current_user_id`:
--   svuotare l'utente non e' fail-closed — una whitelist vuota
--   script.fn_check_user_emittente_scope la legge come «nessuna restrizione»,
--   quindi il test vedrebbe TUTTO e passerebbe per la ragione opposta a quella
--   che crede. Il gate della policy e' invece un'uguaglianza sul RUOLO: senza
--   veste dichiarata non c'e' nessuna riga.
--
-- ⚠️ IL TEST 5 VUOLE UN OPERATORE VERO DI UN ALTRO PERIMETRO, per la stessa
--   ragione: un auth_user_id inventato non e' «un altro operatore», e' un
--   utente senza whitelist, cioe' — di nuovo — uno che vede tutto. Se il
--   database non ha un secondo operatore con un emittente diverso, il test si
--   dichiara saltato invece di passare a vuoto.
-- ------------------------------------------------------------
-- Indice test (1..10):
--   STRUTTURA
--   1)  la policy esiste, e' PERMISSIVE e FOR ALL (non FOR SELECT)
--   2)  la tabella ha la RLS ATTIVA (e NO FORCE, a parita' con la famiglia)
--   3)  ⭐ lo scope e' delegato alla TESTATA (fn_scope_ef_whitelist_via_fattura)
--   4)  ⛔ nessuna policy ba_ownership: la coda stampa non e' superficie portale
--   COMPORTAMENTO
--   5)  operatore di un ALTRO perimetro -> non vede la riga
--   6)  veste diversa da OPERATORE -> non vede nulla (gate)
--   7)  senza veste dichiarata -> fail-closed
--   8)  l'operatore in perimetro VEDE la sua riga
--   9)  ⭐ ARCHIVIAZIONE in perimetro -> 1 riga scritta (la policy e' FOR ALL)
--  10)  ⭐ ARCHIVIAZIONE da un altro perimetro -> 0 righe (USING nega)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ La fattura si sceglie NEL PERIMETRO (la WITH CHECK della policy la
--   pretende) e SENZA work-item vivo (l'indice unico parziale rifiuterebbe
--   l'INSERT). ORDER BY esplicito: senza, la riga scelta dipende dal piano.
CREATE TEMP TABLE _fat AS
SELECT f.id AS fattura_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'FATTURA') AS tipo_id
  FROM vendite.fatture f
 WHERE f.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
   AND NOT EXISTS (SELECT 1 FROM vendite.fatture_stampa_coda c
                    WHERE c.sorgente_id = f.id
                      AND c.stato IN ('PENDING', 'IN_CORSO'))
 ORDER BY f.id
 LIMIT 1;

-- L'operatore corrente e un operatore di un ALTRO emittente. Il secondo puo'
-- non esistere: i test che lo usano lo dichiarano saltato.
CREATE TEMP TABLE _op AS
SELECT NULLIF(current_setting('app.current_user_id', true), '')::integer AS io,
       (SELECT u.auth_user_id
          FROM config.user_emittenti_fiscali u
          JOIN anagrafiche.emittenti_fiscali e ON e.id = u.emittente_fiscale_id
         WHERE e.soggetto_ruolo_id IS DISTINCT FROM script.fn_pgtap_emittente_sr_operatore()
         ORDER BY u.auth_user_id
         LIMIT 1) AS altro;

-- La riga di coda su cui si misura tutto: nasce ERRORE, cioe' gia'
-- archiviabile, perche' qui il soggetto e' la RLS e non il guard di stato
-- (quello ha il suo test in dbops/test-coda-archiviazione.sql).
DO $fix$
DECLARE
    v_fattura_id bigint;
    v_tipo_id    bigint;
BEGIN
    SELECT fattura_id, tipo_id INTO v_fattura_id, v_tipo_id FROM _fat;
    IF v_fattura_id IS NULL OR v_tipo_id IS NULL THEN
        RETURN;
    END IF;
    INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, stato)
    VALUES (v_tipo_id, v_fattura_id, v_fattura_id::text, 'ERRORE');
END
$fix$;

CREATE TEMP TABLE _coda AS
SELECT c.id
  FROM vendite.fatture_stampa_coda c
  JOIN _fat f ON f.fattura_id = c.sorgente_id
 WHERE c.stato = 'ERRORE';

-- ============================================================
-- 1-4) Struttura
-- ============================================================
SELECT is(
    (SELECT p.permissive || '/' || p.cmd
       FROM pg_policies p
      WHERE p.schemaname = 'vendite'
        AND p.tablename  = 'fatture_stampa_coda'
        AND p.policyname = 'rls_fatture_stampa_coda_ef_whitelist'),
    'PERMISSIVE/ALL',
    '1) la policy e'' PERMISSIVE e FOR ALL: con la sola SELECT ogni scrittura operatore fallirebbe');

-- ⚠️ NO FORCE e' una scelta, non una dimenticanza: l'owner resta esente cosi'
--   le migrazioni e i job owner non si bloccano. Non significa «non morde»: il
--   runtime e' zeroerp_app, che non e' owner ed e' NOBYPASSRLS.
SELECT is(
    (SELECT c.relrowsecurity || '/' || c.relforcerowsecurity
       FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'vendite' AND c.relname = 'fatture_stampa_coda'),
    'true/false',
    '2) la RLS e'' ATTIVA e senza FORCE, a parita'' con la famiglia fatture');

-- ⭐ L'INVARIANTE: lo scope e' quello della TESTATA, mai un criterio proprio.
--   E' cio' che rende il filtro tutto-o-niente per fattura: chi vede la fattura
--   vede tutti i suoi work-item, chi non la vede non ne vede nessuno. Un
--   criterio proprio renderebbe possibili gli insiemi PARZIALI, e una coda
--   parziale non da' errore: fa sparire un work-item dal monitoraggio.
SELECT matches(
    (SELECT p.qual FROM pg_policies p
      WHERE p.policyname = 'rls_fatture_stampa_coda_ef_whitelist'),
    'fn_scope_ef_whitelist_via_fattura',
    '3) lo scope e'' delegato alla testata, non a un criterio proprio');

SELECT is(
    (SELECT count(*) FROM pg_policies p
      WHERE p.schemaname = 'vendite'
        AND p.tablename  = 'fatture_stampa_coda'),
    1::bigint,
    '4) una policy sola: la coda stampa non e'' una superficie del portale cliente');

-- ============================================================
-- 5-8) Chi vede cosa
-- ============================================================
SELECT CASE
    WHEN (SELECT count(*) FROM _coda) = 0
      THEN skip('5) nessuna fattura nel perimetro dell''operatore: fixture non costruibile', 1)
    WHEN (SELECT altro FROM _op) IS NULL
      THEN skip('5) nessun secondo operatore con un emittente diverso su questo database', 1)
    ELSE is(
        (SELECT count(*) FROM (
            SELECT set_config('app.current_user_id',
                              (SELECT altro::text FROM _op), true)) s,
            LATERAL (SELECT 1 FROM vendite.fatture_stampa_coda c
                      WHERE c.id = (SELECT id FROM _coda)) x),
        0::bigint,
        '5) un operatore di un altro perimetro non vede il work-item')
    END;

-- Si torna all'operatore di casa prima di proseguire.
SELECT set_config('app.current_user_id', (SELECT io::text FROM _op), true);

SELECT CASE WHEN (SELECT count(*) FROM _coda) = 0
    THEN skip('6) fixture non costruibile (vedi 5)', 1)
    ELSE is(
        (SELECT count(*) FROM (
            SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true)) s,
            LATERAL (SELECT 1 FROM vendite.fatture_stampa_coda c
                      WHERE c.id = (SELECT id FROM _coda)) x),
        0::bigint,
        '6) una veste diversa da OPERATORE non vede nulla: il gate della policy')
    END;

-- ⚠️ Fail-closed sul RUOLO, non sull'utente: svuotare app.current_user_id
--   NON e' fail-closed (whitelist vuota = nessuna restrizione), e un test
--   scritto cosi' passerebbe vedendo tutto.
SELECT CASE WHEN (SELECT count(*) FROM _coda) = 0
    THEN skip('7) fixture non costruibile (vedi 5)', 1)
    ELSE is(
        (SELECT count(*) FROM (
            SELECT set_config('app.ruolo_applicativo', '', true)) s,
            LATERAL (SELECT 1 FROM vendite.fatture_stampa_coda c
                      WHERE c.id = (SELECT id FROM _coda)) x),
        0::bigint,
        '7) senza veste dichiarata la policy e'' fail-closed')
    END;

SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

SELECT CASE WHEN (SELECT count(*) FROM _coda) = 0
    THEN skip('8) fixture non costruibile (vedi 5)', 1)
    ELSE is(
        (SELECT count(*) FROM vendite.fatture_stampa_coda c
          WHERE c.id = (SELECT id FROM _coda)),
        1::bigint,
        '8) l''operatore vede il work-item della propria fattura')
    END;

-- ============================================================
-- 9-10) ⭐ La scrittura — cioe' proprio il verbo che apre questo cantiere
-- ============================================================
-- ⚠️ Le due scritture si misurano in un DO e non dentro `is(...)`: una CTE che
--   MODIFICA i dati deve stare al livello superiore dell'istruzione, e infilata
--   in una sotto-select PostgreSQL la rifiuta. Il conteggio finisce in una
--   tabella d'appoggio, che le asserzioni poi leggono.
CREATE TEMP TABLE _scritture (chiave text PRIMARY KEY, righe integer);

DO $scritture$
DECLARE
    v_n     integer;
    v_altro integer;
BEGIN
    IF (SELECT count(*) FROM _coda) = 0 THEN
        RETURN;
    END IF;

    -- In perimetro: se la policy fosse FOR SELECT questa tornerebbe 0 e
    -- l'archiviazione sarebbe impossibile anche a chi ne ha diritto — e' la
    -- lezione dell'Ondata 2, pagata una volta.
    UPDATE vendite.fatture_stampa_coda SET archiviato = true
     WHERE id = (SELECT id FROM _coda);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _scritture VALUES ('in_perimetro', v_n);

    SELECT altro INTO v_altro FROM _op;
    IF v_altro IS NULL THEN
        RETURN;
    END IF;

    -- Fuori perimetro: la USING non fa vedere la riga, quindi l'UPDATE non ne
    -- tocca nessuna. Nessun errore: zero righe, che e' il modo in cui la RLS
    -- dice di no.
    PERFORM set_config('app.current_user_id', v_altro::text, true);
    UPDATE vendite.fatture_stampa_coda SET archiviato = false
     WHERE id = (SELECT id FROM _coda);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _scritture VALUES ('fuori_perimetro', v_n);

    PERFORM set_config('app.current_user_id', (SELECT io::text FROM _op), true);
END
$scritture$;

SELECT CASE WHEN (SELECT count(*) FROM _coda) = 0
    THEN skip('9) fixture non costruibile (vedi 5)', 1)
    ELSE is(
        (SELECT righe FROM _scritture WHERE chiave = 'in_perimetro'),
        1,
        '9) l''operatore ARCHIVIA il work-item della propria fattura')
    END;

SELECT CASE
    WHEN (SELECT count(*) FROM _coda) = 0
      THEN skip('10) fixture non costruibile (vedi 5)', 1)
    WHEN (SELECT altro FROM _op) IS NULL
      THEN skip('10) nessun secondo operatore con un emittente diverso', 1)
    ELSE is(
        (SELECT righe FROM _scritture WHERE chiave = 'fuori_perimetro'),
        0,
        '10) un operatore di un altro perimetro non puo'' archiviare: la USING nega')
    END;

SELECT * FROM finish();
ROLLBACK;
