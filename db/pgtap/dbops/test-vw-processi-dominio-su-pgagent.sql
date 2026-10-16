-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.processi, un catalogo che a
--   runtime non scrive nessuno (lo popola il mirror CSV di 80_data) e su cui il
--   ruolo applicativo ha SELECT-only (90_end/20260904-15). Verificato cercando
--   gli scrittori, non dedotto.
--
-- Test: la regola «nessun processo di DOMINIO ESEGUE dentro pgAgent»
-- Brief: brief-db-processi-automatici-identita-e-perimetro §12.12 (DB-1)
--
-- Elenco test (plan 5):
--  1) ⭐ la vista e' VUOTA: la regola vale, oggi
--  2) ⭐ ed e' vuota per il motivo giusto — chiusura_scadenze_daily e' passato
--       a CODA_AUTOMATICA, non e' stato spento
--  3) ⛔ il presidio SI ACCENDE: un processo di dominio su PGAGENT compare
--  4) ⚠️ e il motivo dice il rimedio, non il difetto
--  5) ⚠️ la MANUTENZIONE su pgAgent NON compare: il presidio non e' una tassa
--       su pgAgent
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ PERCHE' I TEST 1 E 3 VANNO LETTI INSIEME.
--   Un presidio vuoto e' indistinguibile da un presidio SPENTO: `WHERE false`
--   passerebbe il test 1 a pieni voti. Il test 3 costruisce il caso che deve
--   accendersi, e senza di lui il test 1 non prova niente.
--
-- ⭐ E il test 5 e' l'altro verso: un presidio che si accende SEMPRE viene
--   ignorato. La regola parla dei processi di DOMINIO — quelli che toccano i
--   documenti di un'azienda e hanno bisogno di un perimetro. La manutenzione
--   del database su pgAgent e' al suo posto, e deve restarci.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- 1..2. La regola vale, e vale per il motivo giusto
-- ============================================================
-- ⚠️ L'ordine conta: si misura PRIMA di seminare la fixture, altrimenti si
--   misurerebbe il proprio rumore.
SELECT is_empty(
    $$SELECT processo_codice FROM dbops.vw_processi_dominio_su_pgagent$$,
    '1. nessun processo di DOMINIO esegue dentro pgAgent'
);

-- ⭐ Una vista vuota si puo' ottenere anche spegnendo l'ultimo processo che ci
--   stava dentro: sarebbe verde e sarebbe una resa. Qui si chiede che
--   `chiusura_scadenze_daily` sia ancora VIVO, ancora di DOMINIO, e che sia
--   uscito da pgAgent passando alla coda.
SELECT is(
    (SELECT classe || '/' || canale || '/' || attivo::text
       FROM dbops.processi WHERE codice = 'chiusura_scadenze_daily'),
    'DOMINIO/CODA_AUTOMATICA/true',
    '2. chiusura_scadenze_daily e'' vivo, di dominio, e passa dalla coda'
);

-- ============================================================
-- Fixture: i due casi opposti, costruiti
-- ============================================================
DO $fixture$
BEGIN
    -- 20261016-20: chi ha una sveglia dichiara l'accensione; un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento)
    VALUES (9611, 'PGTAP-PGAGENT-DOMINIO',
            'processo di dominio che esegue dentro pgAgent: deve comparire',
            'DOMINIO', 'PGAGENT', true, true, true, 'PROGRAMMA'),
           (9612, 'PGTAP-PGAGENT-MANUTENZIONE',
            'manutenzione del database su pgAgent: e'' al suo posto',
            'MANUTENZIONE', 'PGAGENT', true, true, true, 'PROGRAMMA');
END
$fixture$;

-- ============================================================
-- 3..4. ⛔ Il presidio si accende, e dice che cosa fare
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_processi_dominio_su_pgagent
      WHERE processo_codice = 'PGTAP-PGAGENT-DOMINIO'),
    1,
    '3. un processo di dominio su PGAGENT compare nel presidio'
);

-- ⭐ Chi legge un presidio vuole sapere il GESTO, non la diagnosi: il motivo
--   nomina la strada (CODA_AUTOMATICA + il job che accoda), che e' esattamente
--   quella percorsa da chiusura_scadenze_daily.
SELECT matches(
    (SELECT motivo FROM dbops.vw_processi_dominio_su_pgagent
      WHERE processo_codice = 'PGTAP-PGAGENT-DOMINIO'),
    'CODA_AUTOMATICA',
    '4. il motivo nomina il rimedio, non solo il difetto'
);

-- ============================================================
-- 5. ⚠️ Il verso che tiene il presidio leggibile
-- ============================================================
-- Un presidio sempre acceso viene ignorato, e il giorno in cui compare la riga
-- vera nessuno la distingue dal rumore di fondo.
SELECT is_empty(
    $$SELECT processo_codice FROM dbops.vw_processi_dominio_su_pgagent
       WHERE processo_codice = 'PGTAP-PGAGENT-MANUTENZIONE'$$,
    '5. la manutenzione su pgAgent non compare: e'' al suo posto'
);

SELECT * FROM finish();

ROLLBACK;
