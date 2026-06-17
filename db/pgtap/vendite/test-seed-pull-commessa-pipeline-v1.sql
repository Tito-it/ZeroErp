-- ============================================================
-- Indice test
-- 1) Task pull_attivita_da_commessa registrato (dominio FATTURAZIONE) -> handler default
-- 2) MASSIVO DRAFT: primo task = pull_attivita_da_commessa
-- 3) MASSIVO DRAFT: secondo task = select_attivita (pull precede select)
-- 4) MASSIVO DRAFT: terzo task = generate_fatture_righe
-- 5) GIORNALIERO DRAFT: pipeline esiste (esattamente 1, perimetro default)
-- 6) GIORNALIERO DRAFT: primo task = pull_attivita_da_commessa
-- 7) GIORNALIERO DRAFT: sequenza di 3 task (pull -> select -> genera)
-- 8) chiude_lotto: esattamente 1 stato con flag TRUE (vincolo singleton)
-- 9) chiude_lotto: lo stato TRUE e' DEFINITIVA
-- 10) REGISTRATA: chiude_lotto = false (flag spostato)
-- 11) task_policy: 2 righe pull (pipeline MASSIVO DRAFT + GIORNALIERO DRAFT)
-- ============================================================

BEGIN;

SELECT plan(11);

-- 1) Il task pull e' registrato e risolve l'handler default tramite la
--    funzione di dispatch usata dal backend (fn_get_pipeline_task_implementation).
SELECT is(
  (
    SELECT handler_code
    FROM dbops.fn_get_pipeline_task_implementation(
      (SELECT id FROM dbops.domini_task WHERE codice = 'FATTURAZIONE'),
      'pull_attivita_da_commessa',
      NULL
    )
  ),
  'pull_attivita_da_commessa_default',
  'Task pull_attivita_da_commessa registrato (dominio FATTURAZIONE) -> handler default'
);

-- 2-4) MASSIVO DRAFT: ordine processi pull -> select -> genera.
SELECT is(
  (
    SELECT processi -> 0 ->> 'task'
    FROM vendite.fatturazione_pipeline
    WHERE tipo_lotto = 'MASSIVO' AND stato_doc_fiscale_id = 1
      AND utility_id IS NULL AND tipo_doc_fiscale_id IS NULL
  ),
  'pull_attivita_da_commessa',
  'MASSIVO DRAFT: primo task = pull_attivita_da_commessa'
);

SELECT is(
  (
    SELECT processi -> 1 ->> 'task'
    FROM vendite.fatturazione_pipeline
    WHERE tipo_lotto = 'MASSIVO' AND stato_doc_fiscale_id = 1
      AND utility_id IS NULL AND tipo_doc_fiscale_id IS NULL
  ),
  'select_attivita',
  'MASSIVO DRAFT: secondo task = select_attivita (pull precede select)'
);

SELECT is(
  (
    SELECT processi -> 2 ->> 'task'
    FROM vendite.fatturazione_pipeline
    WHERE tipo_lotto = 'MASSIVO' AND stato_doc_fiscale_id = 1
      AND utility_id IS NULL AND tipo_doc_fiscale_id IS NULL
  ),
  'generate_fatture_righe',
  'MASSIVO DRAFT: terzo task = generate_fatture_righe'
);

-- 5-7) GIORNALIERO DRAFT: pipeline iniziale equivalente alla massiva.
SELECT is(
  (
    SELECT count(*)::int
    FROM vendite.fatturazione_pipeline
    WHERE tipo_lotto = 'GIORNALIERO' AND stato_doc_fiscale_id = 1
      AND utility_id IS NULL AND tipo_doc_fiscale_id IS NULL AND attivo IS TRUE
  ),
  1,
  'GIORNALIERO DRAFT: pipeline esiste (esattamente 1, perimetro default)'
);

SELECT is(
  (
    SELECT processi -> 0 ->> 'task'
    FROM vendite.fatturazione_pipeline
    WHERE tipo_lotto = 'GIORNALIERO' AND stato_doc_fiscale_id = 1
      AND utility_id IS NULL AND tipo_doc_fiscale_id IS NULL
  ),
  'pull_attivita_da_commessa',
  'GIORNALIERO DRAFT: primo task = pull_attivita_da_commessa'
);

SELECT is(
  (
    SELECT jsonb_array_length(processi)
    FROM vendite.fatturazione_pipeline
    WHERE tipo_lotto = 'GIORNALIERO' AND stato_doc_fiscale_id = 1
      AND utility_id IS NULL AND tipo_doc_fiscale_id IS NULL
  ),
  3,
  'GIORNALIERO DRAFT: sequenza di 3 task (pull -> select -> genera)'
);

-- 8-10) chiude_lotto: flag spostato su DEFINITIVA, tolto da REGISTRATA, singleton rispettato.
SELECT is(
  (SELECT count(*)::int FROM config.stati_doc_fiscale WHERE chiude_lotto IS TRUE),
  1,
  'chiude_lotto: esattamente 1 stato con flag TRUE (vincolo singleton)'
);

SELECT is(
  (SELECT codice_interno FROM config.stati_doc_fiscale WHERE chiude_lotto IS TRUE),
  'DEFINITIVA',
  'chiude_lotto: lo stato TRUE e'' DEFINITIVA'
);

SELECT is(
  (SELECT chiude_lotto FROM config.stati_doc_fiscale WHERE codice_interno = 'REGISTRATA'),
  false,
  'REGISTRATA: chiude_lotto = false (flag spostato)'
);

-- 11) task_policy: tracing pull presente su entrambe le corsie DRAFT.
SELECT is(
  (
    SELECT count(*)::int
    FROM vendite.fatturazione_pipeline_task_policy
    WHERE task_code = 'pull_attivita_da_commessa' AND attivo IS TRUE
      AND pipeline_id IN (
        SELECT id FROM vendite.fatturazione_pipeline
        WHERE stato_doc_fiscale_id = 1
          AND utility_id IS NULL AND tipo_doc_fiscale_id IS NULL
      )
  ),
  2,
  'task_policy: 2 righe pull (pipeline MASSIVO DRAFT + GIORNALIERO DRAFT)'
);

SELECT * FROM finish();

ROLLBACK;
