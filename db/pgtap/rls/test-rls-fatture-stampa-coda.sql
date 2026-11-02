-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce DUE aziende e una fattura, e una
--   fattura pretende un billing account. Come `zeroerp_app` l'INSERT del BA
--   muore al RETURNING quando l'emittente di chi agisce non e' quello di
--   default (la policy di lettura risolve il BA non ancora mappato sul default;
--   il legame lo scrive un trigger AFTER). Da owner la policy si esercita con
--   `FORCE ROW LEVEL SECURITY` locale alla transazione, acceso DOPO i test di
--   struttura — cosi' il test 2 continua a misurare la postura di esercizio.
-- pgTAP test per Zero ERP
-- Test: RLS FUNZIONALE su vendite.fatture_stampa_coda
--       policy rls_fatture_stampa_coda_ef_whitelist (changeset 20260904-05/06)
--       Piano: brief-db-archiviazione-righe-code, PARTE DB sezione 8
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno il
--   file cercava una fattura ESISTENTE nel perimetro dell'operatore e un secondo
--   operatore su un altro emittente, e senza di loro SALTAVA i test 5-10: su un
--   database ricostruito dai changelog moriva nella fixture, e il verbo
--   «Archivia» — la prima scrittura dell'operatore su questa tabella — restava
--   collaudato solo su dbdev. Ora: due aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()`, un cliente della prima con
--   `dbops.fn_pgtap_crea_cliente_ba(..., A)`, il suo registro
--   (`script.fn_pgtap_registro_fattura`) e la sua fattura. Niente piu' `skip`.
--   ⚠️ Fino a quel giorno il file girava come `zeroerp_app` senza DDL: il costo
--   del cambio e' scritto nel marcatore.
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
--   utente senza whitelist, cioe' — di nuovo — uno che vede tutto. E' l'operatore
--   dell'azienda B, costruita apposta.
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

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture: il mondo, POI il contesto
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'IO'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRO' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⛔ Il BA va LEGATO al proprio emittente (terzo parametro): senza, la fattura
--   ricadrebbe sull'emittente di DEFAULT dell'installazione.
CREATE TEMP TABLE _cliente AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba(
    'RLS stampa coda', NULL, (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'IO')) c;

-- ⚠️ La fattura si costruisce NEL PERIMETRO (la WITH CHECK della policy la
--   pretende) e nasce SENZA work-item vivo.
CREATE TEMP TABLE _fat AS
WITH f AS (
    INSERT INTO vendite.fatture
        (registro_id, emittente_soggetto_ruolo_id, billing_account_id)
    SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id),
           m.soggetto_ruolo_id, c.billing_account_id
      FROM _mondi m, _cliente c
     WHERE m.lato = 'IO'
    RETURNING id
)
SELECT f.id AS fattura_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'FATTURA') AS tipo_id
  FROM f;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'IO'));
END $ctx$;

-- L'operatore corrente e l'operatore dell'ALTRA azienda.
CREATE TEMP TABLE _op AS
SELECT (SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'IO')    AS io,
       (SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'ALTRO') AS altro;

-- La riga di coda su cui si misura tutto: nasce ERRORE, cioe' gia'
-- archiviabile, perche' qui il soggetto e' la RLS e non il guard di stato
-- (quello ha il suo test in dbops/test-coda-archiviazione.sql).
CREATE TEMP TABLE _coda AS
WITH c AS (
    INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, stato)
    SELECT f.tipo_id, f.fattura_id, f.fattura_id::text, 'ERRORE'
      FROM _fat f
    RETURNING id
)
SELECT id FROM c;

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
-- ⭐ Rev 2026-10-18 (D-3b-2 giro 1b, 20261018-33): la rotta si legge nel modo di
--   script.fn_resolve_emittente_fiscale_id, non piu' nel nome dell'adattatore.
SELECT matches(
    (SELECT p.qual FROM pg_policies p
      WHERE p.policyname = 'rls_fatture_stampa_coda_ef_whitelist'),
    'fn_resolve_emittente_fiscale_id\(''fattura''',
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
-- Da owner la policy non morde: si accende ORA, dopo che il test 2 ha misurato
-- la postura di esercizio, e per la sola durata della transazione.
ALTER TABLE vendite.fatture_stampa_coda FORCE ROW LEVEL SECURITY;

SELECT is(
    (SELECT count(*) FROM (
        SELECT set_config('app.current_user_id',
                          (SELECT altro::text FROM _op), true)) s,
        LATERAL (SELECT 1 FROM vendite.fatture_stampa_coda c
                  WHERE c.id = (SELECT id FROM _coda)) x),
    0::bigint,
    '5) un operatore di un altro perimetro non vede il work-item');

-- Si torna all'operatore di casa prima di proseguire.
SELECT set_config('app.current_user_id', (SELECT io::text FROM _op), true);

SELECT is(
    (SELECT count(*) FROM (
        SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true)) s,
        LATERAL (SELECT 1 FROM vendite.fatture_stampa_coda c
                  WHERE c.id = (SELECT id FROM _coda)) x),
    0::bigint,
    '6) una veste diversa da OPERATORE non vede nulla: il gate della policy');

-- ⚠️ Fail-closed sul RUOLO, non sull'utente: svuotare app.current_user_id
--   NON e' fail-closed (whitelist vuota = nessuna restrizione), e un test
--   scritto cosi' passerebbe vedendo tutto.
SELECT is(
    (SELECT count(*) FROM (
        SELECT set_config('app.ruolo_applicativo', '', true)) s,
        LATERAL (SELECT 1 FROM vendite.fatture_stampa_coda c
                  WHERE c.id = (SELECT id FROM _coda)) x),
    0::bigint,
    '7) senza veste dichiarata la policy e'' fail-closed');

SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

SELECT is(
    (SELECT count(*) FROM vendite.fatture_stampa_coda c
      WHERE c.id = (SELECT id FROM _coda)),
    1::bigint,
    '8) l''operatore vede il work-item della propria fattura');

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
    -- In perimetro: se la policy fosse FOR SELECT questa tornerebbe 0 e
    -- l'archiviazione sarebbe impossibile anche a chi ne ha diritto — e' la
    -- lezione dell'Ondata 2, pagata una volta.
    UPDATE vendite.fatture_stampa_coda SET archiviato = true
     WHERE id = (SELECT id FROM _coda);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _scritture VALUES ('in_perimetro', v_n);

    SELECT altro INTO v_altro FROM _op;

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

SELECT is(
    (SELECT righe FROM _scritture WHERE chiave = 'in_perimetro'),
    1,
    '9) l''operatore ARCHIVIA il work-item della propria fattura');

SELECT is(
    (SELECT righe FROM _scritture WHERE chiave = 'fuori_perimetro'),
    0,
    '10) un operatore di un altro perimetro non puo'' archiviare: la USING nega');

ALTER TABLE vendite.fatture_stampa_coda NO FORCE ROW LEVEL SECURITY;

SELECT * FROM finish();
ROLLBACK;
