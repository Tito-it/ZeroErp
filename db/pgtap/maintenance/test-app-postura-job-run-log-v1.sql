-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test STRUTTURALE — postura di `zeroerp_app` sul giornale dei job
--   maintenance.job_run_log · maintenance.vw_job_run_da_guardare
--   script.fn_job_run_start / script.fn_job_run_end (la porta di scrittura)
--
-- Sede della postura: scripts/sql/provision_zeroerp.sql (fase post) (blocco `maintenance`
--   in fondo: USAGE sullo schema + SELECT sul giornale, dal 2026-09-19) e il
--   changeSet gemello 90_end/20260919-08 per i database già provisionati.
--
-- ⭐ PERCHÉ ESISTE. Il backend legge `maintenance.job_run_log` direttamente
--   come ruolo applicativo in cinque punti (lista dei processi automatici e
--   corse di un processo, riepilogo giri e liveness, esiti delle corsie di
--   fatturazione), ma il privilegio SELECT esisteva SOLO sul database di
--   sviluppo, dato a mano (`zeroerp_app=r/titodb`): nessun changeSet lo
--   concedeva, e il provisioning lasciava `maintenance` fuori whitelist con un
--   commento che affermava il contrario del contratto («l'app non ne legge né
--   scrive le tabelle»). È saltato fuori il 2026-09-19, quando i test Django
--   in CI sono passati a connettersi come `zeroerp_app` (9c11a485b): la CI è
--   l'unica macchina senza il grant a mano, e SEDICI test sono morti su
--   «permission denied for table job_run_log». Lo stesso rosso stava in
--   `baseline-rossi-ci.tsv` come ERRORE_FIXTURE di
--   `maintenance/test-job-run-registrazione.sql`, con la causa mai letta.
--   È la forma del `GRANT USAGE` su `maintenance` (09-09) e dello schema
--   `django` (13-09): un privilegio che esiste su UNA macchina è un ricordo,
--   non una configurazione (linee-guida-sql §11.9).
--
-- ⭐ E PERCHÉ È SOLO SELECT, che è la metà che un GRANT largo avrebbe perso.
--   Il giornale dei job non si scrive dall'applicazione: la porta è
--   `script.fn_job_run_start/end`, SECURITY DEFINER, e il canale fuori
--   transazione scrive come `zeroerp_log` (INSERT, `20260905-38`). Mettere
--   `maintenance` nella whitelist del provisioning avrebbe dato SIUD pieno e
--   aperto il giornale a chi vi è registrato. I test 3-5 pinnano il NO, non
--   solo il sì.
--
-- ⚠️ PERCHÉ GIRA COME L'APPLICAZIONE (runner di default). Il SOGGETTO è
--   `zeroerp_app`: i privilegi che ha e ciò che riesce a fare. Le asserzioni
--   di postura usano `has_*_privilege(ruolo, …)`, che legge il catalogo e non
--   dipende dal ruolo connesso — MAI `information_schema.role_table_grants`,
--   cieco fuori dal ruolo connesso. Le asserzioni di comportamento (8-9) hanno
--   senso SOLO come app: da owner la SELECT passerebbe e l'INSERT non
--   verrebbe respinto.
--
-- Elenco test (plan 11):
--   POSTURA — lo schema
--    1   : USAGE sullo schema maintenance (per risolvere i nomi)
--   POSTURA — maintenance.job_run_log, la tabella dei cinque lettori
--    2   : SELECT concesso
--    3-5 : INSERT, UPDATE, DELETE NON concessi (la porta è DEFINER)
--   POSTURA — la vista di presidio
--    6   : SELECT su maintenance.vw_job_run_da_guardare (grant in 20260905-39)
--   LA PORTA — perché la sola lettura basta
--    7   : script.fn_job_run_start e fn_job_run_end esistono e sono
--          SECURITY DEFINER: l'app scrive il giornale ATTRAVERSO di loro
--   COMPORTAMENTO — come app, davvero
--    8   : SELECT su maintenance.job_run_log non solleva — la query esatta
--          dei sedici test Django del 19-09
--    9   : INSERT diretto respinto con 42501 (insufficient_privilege)
--   10   : la SELECT della vista di presidio non solleva
--   IL RESIDUO DEL BOOTSTRAP
--   11   : maintenance.test_pgagent_log NON c'e': la tabella di collaudo
--          dell'albero v1, senza lettori ne' scrittori, rinasce a ogni
--          ricostruzione da zero e la ritira il changeSet
--          00_schema/maintenance/20261111-23. Prima il test chiedeva che
--          l'app non ci avesse privilegi; senza la tabella la domanda non
--          ha piu' oggetto.
--          rev 2026-11-09 (brief-db-revisione-dbops, giro 14, N4).
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;. Il test 9 non scrive niente:
--   viene respinto prima di toccare la riga.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file non attraversa tabelle in RLS, ma la riga sta
-- qui perché il preambolo è un contratto (guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- POSTURA — lo schema
-- ============================================================
SELECT ok(has_schema_privilege('zeroerp_app', 'maintenance', 'USAGE'),
          '1. zeroerp_app ha USAGE sullo schema maintenance');

-- ============================================================
-- POSTURA — maintenance.job_run_log
-- ============================================================
SELECT ok(has_table_privilege('zeroerp_app', 'maintenance.job_run_log', 'SELECT'),
          '2. zeroerp_app ha SELECT su maintenance.job_run_log (processi, corse, riepiloghi, esiti fatturazione)');
SELECT ok(NOT has_table_privilege('zeroerp_app', 'maintenance.job_run_log', 'INSERT'),
          '3. zeroerp_app NON ha INSERT su maintenance.job_run_log (la porta è script.fn_job_run_start)');
SELECT ok(NOT has_table_privilege('zeroerp_app', 'maintenance.job_run_log', 'UPDATE'),
          '4. zeroerp_app NON ha UPDATE su maintenance.job_run_log (la porta è script.fn_job_run_end)');
SELECT ok(NOT has_table_privilege('zeroerp_app', 'maintenance.job_run_log', 'DELETE'),
          '5. zeroerp_app NON ha DELETE su maintenance.job_run_log (un giornale non si cancella)');

-- ============================================================
-- POSTURA — la vista di presidio
-- ============================================================
SELECT ok(has_table_privilege('zeroerp_app', 'maintenance.vw_job_run_da_guardare', 'SELECT'),
          '6. zeroerp_app ha SELECT su maintenance.vw_job_run_da_guardare');

-- ============================================================
-- LA PORTA — perché la sola lettura basta
-- ============================================================
-- Due funzioni, entrambe DEFINER: se una smettesse di esserlo, l'app avrebbe
-- bisogno dell'INSERT/UPDATE che i test 3-4 le negano, e il primo run come
-- app morirebbe. `count = 2` pinna anche l'esistenza: `bool_and` su zero
-- righe direbbe sì.
SELECT is(
  (SELECT count(*) FILTER (WHERE p.prosecdef) || '/' || count(*)
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'script'
      AND p.proname IN ('fn_job_run_start', 'fn_job_run_end')),
  '2/2',
  '7. script.fn_job_run_start e fn_job_run_end esistono e sono SECURITY DEFINER');

-- ============================================================
-- COMPORTAMENTO — come app, davvero
-- ============================================================
SELECT lives_ok(
  $$SELECT count(*) FROM maintenance.job_run_log$$,
  '8. la SELECT su maintenance.job_run_log non solleva (i sedici test Django del 19-09)');

-- Respinto dal privilegio, prima di ogni guard/trigger: 42501 e non P0001.
-- Se un giorno tornasse P0001, qualcuno ha concesso l'INSERT e a rifiutare è
-- un trigger — il test 3 sarebbe già rosso, e questo dice dove.
SELECT throws_ok(
  $$INSERT INTO maintenance.job_run_log (jobname, stepname, started_at)
    VALUES ('pgtap_postura', 'pgtap_postura', now())$$,
  '42501',
  NULL,
  '9. un INSERT diretto come zeroerp_app è respinto dal privilegio (42501)');

SELECT lives_ok(
  $$SELECT count(*) FROM maintenance.vw_job_run_da_guardare$$,
  '10. la SELECT sulla vista di presidio non solleva');

-- ============================================================
-- IL RESIDUO DEL BOOTSTRAP
-- ============================================================
SELECT hasnt_table('maintenance', 'test_pgagent_log',
          '11. maintenance.test_pgagent_log e'' ritirata');

SELECT * FROM finish();
ROLLBACK;
