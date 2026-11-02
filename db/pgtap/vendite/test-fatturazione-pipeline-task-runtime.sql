-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: runtime task policy/runs per pipeline fatturazione
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Lotto test creato
-- 3) Policy RESUME presente via get
-- 4) start run #1 (tentativo=1)
-- 5) resolve mode su IN_ESECUZIONE = RESUME
-- 6) complete run #1
-- 7) resolve mode su COMPLETATO = SKIP
-- 8) start run #2 (tentativo=2)
-- 9) fail run #2
-- 10) resolve mode su ERRORE (RESUME_TASK) = RESUME
-- 11) cancel run #2
-- 12) resolve mode su ANNULLATO = RUN
-- 13) list runs conta 2 righe
-- 14) start run RESET #1
-- 15) fail run RESET #1
-- 16) resolve mode su ERRORE (RESET_STEP) = RESET_REQUIRED
-- 17) ultimo run RESET in stato ERRORE
-- 18) il correlation_id del giro finisce sulla riga del tentativo
-- 19) il vocabolario di resume_mode e' {RESET_STEP, RESUME_TASK}: RESUME_STEP
--     e' ritirato (2026-09-12) e il CHECK lo respinge
--
-- ⚠️ Era 18: la vecchia 4 («check policy RESUME true») e' stata tolta il
--   2026-08-18 perche' `vendite.fn_check_pipeline_task_policy` non esiste piu'.
--   La proprieta' resta coperta dalla 3, che la legge dalla `get`.
--
-- ⭐ 2026-08-22: il run #1 passa un `p_correlation_id` e nasce il test 18.
--   La colonna esiste dal changeSet 20260822-61 e NESSUNA funzione la scriveva
--   (misura del backend su pg_proc): il settimo parametro di
--   `fn_start_lotto_task_run` — changeSet 20260822-67 — e' la meta' che
--   mancava. ⚠️ Il run #2 resta volutamente SENZA: la colonna e' nullable, e
--   il test 18 verifica il filo dove c'e', non che ci sia sempre.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(19);

-- ============================================================
-- 0) Costanti e riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_ptr AS
SELECT
  'pgtap_pipeline_task_runtime'::text AS test_scope,
  'pgtap_task_resume'::varchar(64) AS task_resume,
  'pgtap_task_reset'::varchar(64) AS task_reset;

CREATE TEMP TABLE tmp_refs_ptr AS
SELECT
  (
    SELECT fp.id
    FROM vendite.fatturazione_pipeline fp
    WHERE fp.attivo IS TRUE
    ORDER BY fp.id
    LIMIT 1
  ) AS pipeline_id,
  (
    SELECT m.tipo_doc_fiscale_id
    FROM vendite.tipi_doc_fiscale_registri m
    JOIN config.tipi_doc_fiscale t
      ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE
    ORDER BY m.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT u.id
    FROM config.utilities u
    ORDER BY u.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT ef.soggetto_ruolo_id
    FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (
    SELECT s.id
    FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT'
      AND s.attivo IS TRUE
    ORDER BY s.id
    LIMIT 1
  ) AS stato_doc_fiscale_id;

SELECT ok(
  (
    SELECT pipeline_id IS NOT NULL
       AND tipo_doc_fiscale_id IS NOT NULL
       AND utility_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
       AND stato_doc_fiscale_id IS NOT NULL
    FROM tmp_refs_ptr
  ),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- 1) Lotto test
-- ============================================================
CREATE TEMP TABLE tmp_lotto_ptr AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ptr),
  p_utility_id => (SELECT utility_id FROM tmp_refs_ptr),
  p_billing_account_id => NULL,
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ptr)),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ptr)
) AS lotto_id;

SELECT ok(
  (SELECT lotto_id IS NOT NULL AND lotto_id > 0 FROM tmp_lotto_ptr),
  'Lotto test creato'
);

-- ============================================================
-- 2) Seed policy test (resume/reset)
-- ============================================================
INSERT INTO vendite.fatturazione_pipeline_task_policy (
  id,
  pipeline_id,
  task_code,
  annullabile,
  resume_mode,
  attivo,
  meta
)
VALUES
(
  990001,
  (SELECT pipeline_id FROM tmp_refs_ptr),
  (SELECT task_resume FROM tmp_costanti_ptr),
  true,
  'RESUME_TASK',
  true,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ptr))
),
(
  990002,
  (SELECT pipeline_id FROM tmp_refs_ptr),
  (SELECT task_reset FROM tmp_costanti_ptr),
  true,
  'RESET_STEP',
  true,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ptr))
);

-- ============================================================
-- 3) Get/check policy
-- ============================================================
SELECT ok(
  (
    SELECT p.annullabile IS TRUE
       AND p.resume_mode = 'RESUME_TASK'
       AND p.attivo IS TRUE
    FROM vendite.fn_get_pipeline_task_policy(
      p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
      p_task_code => (SELECT task_resume FROM tmp_costanti_ptr)
    ) p
  ),
  'Policy RESUME presente via get'
);

-- 🔴 ASSERZIONE RIMOSSA IL 2026-08-18 — `fn_check_pipeline_task_policy` non esiste piu'.
--   Della coppia `get`/`check` e' sopravvissuta solo la `get`, che ritorna la
--   riga di policy; la `check`, che ne dava la sola risposta booleana, e' stata
--   ritirata. Il file moriva qui in parsing e non eseguiva NESSUNA delle 18
--   asserzioni: copertura zero, non parziale.
--   ⚠️ Non si perde niente: la proprieta' che questa asserzione verificava —
--   «la policy RESUME c'e' ed e' attiva» — e' gia' verificata dall'asserzione
--   QUI SOPRA, che legge `p.attivo IS TRUE` dalla `get`. Erano due modi di
--   chiedere la stessa cosa, e ne e' rimasto uno.

-- ============================================================
-- 4) start run #1 + resolve RESUME
-- ============================================================
CREATE TEMP TABLE tmp_run1_ptr AS
SELECT *
FROM vendite.fn_start_lotto_task_run(
  p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
  p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
  p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
  p_task_code => (SELECT task_resume FROM tmp_costanti_ptr),
  p_fase => 'Test runtime task #1',
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ptr)),
  -- ⭐ Il filo del GIRO (D-7): lo genera il runner a ogni corsa e lo scrive su
  --   eventi, task_runs e commesse_push_log. Qui e' un valore fisso perche' al
  --   test serve solo che la funzione lo porti fino alla riga — che e' la cosa
  --   che prima non faceva nessuno.
  p_correlation_id => '0198f000-0000-7000-8000-0000000000c1'::uuid
);

SELECT is(
  (SELECT tentativo::int FROM tmp_run1_ptr),
  1,
  'start run #1 (tentativo=1)'
);

SELECT is(
  (
    SELECT r.execution_mode
    FROM vendite.fn_resolve_lotto_task_execution_mode(
      p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
      p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
      p_task_code => (SELECT task_resume FROM tmp_costanti_ptr)
    ) r
  ),
  'RESUME',
  'resolve mode su IN_ESECUZIONE = RESUME'
);

-- ============================================================
-- 5) complete run #1 + resolve SKIP
-- ============================================================
SELECT vendite.fn_complete_lotto_task_run(
  p_task_run_id => (SELECT task_run_id FROM tmp_run1_ptr),
  p_meta => jsonb_build_object('step', 'done')
);

SELECT ok(
  (
    SELECT task_stato = 'COMPLETATO'
    FROM vendite.fatturazione_lotti_task_runs
    WHERE id = (SELECT task_run_id FROM tmp_run1_ptr)
  ),
  'complete run #1'
);

SELECT is(
  (
    SELECT r.execution_mode
    FROM vendite.fn_resolve_lotto_task_execution_mode(
      p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
      p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
      p_task_code => (SELECT task_resume FROM tmp_costanti_ptr)
    ) r
  ),
  'SKIP',
  'resolve mode su COMPLETATO = SKIP'
);

-- ============================================================
-- 6) start run #2 + fail + resolve RESUME
-- ============================================================
CREATE TEMP TABLE tmp_run2_ptr AS
SELECT *
FROM vendite.fn_start_lotto_task_run(
  p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
  p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
  p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
  p_task_code => (SELECT task_resume FROM tmp_costanti_ptr),
  p_fase => 'Test runtime task #2',
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ptr))
);

SELECT is(
  (SELECT tentativo::int FROM tmp_run2_ptr),
  2,
  'start run #2 (tentativo=2)'
);

SELECT vendite.fn_fail_lotto_task_run(
  p_task_run_id => (SELECT task_run_id FROM tmp_run2_ptr),
  p_error_code => 'E_TEST',
  p_error_message => 'Errore di test',
  p_meta => jsonb_build_object('case', 'forced_error')
);

SELECT ok(
  (
    SELECT task_stato = 'ERRORE'
       AND error_code = 'E_TEST'
    FROM vendite.fatturazione_lotti_task_runs
    WHERE id = (SELECT task_run_id FROM tmp_run2_ptr)
  ),
  'fail run #2'
);

SELECT is(
  (
    SELECT r.execution_mode
    FROM vendite.fn_resolve_lotto_task_execution_mode(
      p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
      p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
      p_task_code => (SELECT task_resume FROM tmp_costanti_ptr)
    ) r
  ),
  'RESUME',
  'resolve mode su ERRORE (RESUME_TASK) = RESUME'
);

-- ============================================================
-- 7) cancel run #2 + resolve RUN
-- ============================================================
SELECT vendite.fn_cancel_lotto_task_run(
  p_task_run_id => (SELECT task_run_id FROM tmp_run2_ptr),
  p_meta => jsonb_build_object('case', 'manual_cancel')
);

SELECT ok(
  (
    SELECT task_stato = 'ANNULLATO'
    FROM vendite.fatturazione_lotti_task_runs
    WHERE id = (SELECT task_run_id FROM tmp_run2_ptr)
  ),
  'cancel run #2'
);

SELECT is(
  (
    SELECT r.execution_mode
    FROM vendite.fn_resolve_lotto_task_execution_mode(
      p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
      p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
      p_task_code => (SELECT task_resume FROM tmp_costanti_ptr)
    ) r
  ),
  'RUN',
  'resolve mode su ANNULLATO = RUN'
);

SELECT is(
  (
    SELECT count(*)::int
    FROM vendite.fn_list_lotto_task_runs(
      p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
      p_task_code => (SELECT task_resume FROM tmp_costanti_ptr)
    )
  ),
  2,
  'list runs conta 2 righe'
);

-- ============================================================
-- 8) Caso RESET_REQUIRED (policy RESET_STEP)
-- ============================================================
CREATE TEMP TABLE tmp_run_reset_ptr AS
SELECT *
FROM vendite.fn_start_lotto_task_run(
  p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
  p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
  p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
  p_task_code => (SELECT task_reset FROM tmp_costanti_ptr),
  p_fase => 'Test runtime task RESET',
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ptr))
);

SELECT is(
  (SELECT tentativo::int FROM tmp_run_reset_ptr),
  1,
  'start run RESET #1'
);

SELECT vendite.fn_fail_lotto_task_run(
  p_task_run_id => (SELECT task_run_id FROM tmp_run_reset_ptr),
  p_error_code => 'E_TEST_RESET',
  p_error_message => 'Errore reset test',
  p_meta => jsonb_build_object('case', 'forced_reset_error')
);

SELECT ok(
  (
    SELECT task_stato = 'ERRORE'
    FROM vendite.fatturazione_lotti_task_runs
    WHERE id = (SELECT task_run_id FROM tmp_run_reset_ptr)
  ),
  'fail run RESET #1'
);

SELECT is(
  (
    SELECT r.execution_mode
    FROM vendite.fn_resolve_lotto_task_execution_mode(
      p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
      p_pipeline_id => (SELECT pipeline_id FROM tmp_refs_ptr),
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
      p_task_code => (SELECT task_reset FROM tmp_costanti_ptr)
    ) r
  ),
  'RESET_REQUIRED',
  'resolve mode su ERRORE (RESET_STEP) = RESET_REQUIRED'
);

SELECT is(
  (
    SELECT r.task_stato
    FROM vendite.fn_get_lotto_task_last_run(
      p_lotto_id => (SELECT lotto_id FROM tmp_lotto_ptr),
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr),
      p_task_code => (SELECT task_reset FROM tmp_costanti_ptr)
    ) r
  ),
  'ERRORE'::varchar,
  'ultimo run RESET in stato ERRORE'
);

-- ============================================================
-- 18) Il filo del giro arriva sulla riga
-- ============================================================
--   ⛔ La colonna esisteva dal 20260822-61 e nessuna funzione la scriveva: una
--   colonna che nessuno riempie non e' meta' lavoro, e' un buco che sembra
--   chiuso. Questo test e' cio' che impedisce che torni a esserlo.
SELECT is(
  (
    SELECT r.correlation_id
    FROM vendite.fatturazione_lotti_task_runs r
    WHERE r.id = (SELECT task_run_id FROM tmp_run1_ptr)
  ),
  '0198f000-0000-7000-8000-0000000000c1'::uuid,
  'correlation_id del giro scritto sul task run'
);

-- ============================================================
-- 19) RESUME_STEP e' ritirato: il CHECK lo respinge
-- ============================================================
-- ⭐ Era una distinzione senza differenza: il resolver trattava RESUME_STEP
--   come RESUME_TASK e il backend non lo leggeva (00_schema/20260912-32,
--   brief-db-rilancio-step-non-rivede-le-proprie-commesse §10.3). Un valore
--   dichiarato e morto rientra dalla finestra alla prima riga di CSV copiata
--   da una vecchia: il CHECK e' il cancello, e questo test e' il suo presidio.
--   ⚠️ Si prova sul VINCOLO (23514), non sull'assenza di righe: «nessuna riga
--   oggi» e' una fotografia, «il vincolo lo respinge» e' il modello.
SELECT throws_ok(
  $$ UPDATE vendite.fatturazione_pipeline_task_policy
        SET resume_mode = 'RESUME_STEP'
      WHERE id = (SELECT min(id) FROM vendite.fatturazione_pipeline_task_policy) $$,
  '23514', NULL,
  'resume_mode = RESUME_STEP respinto dal CHECK: il valore e'' ritirato'
);

SELECT * FROM finish();

ROLLBACK;
