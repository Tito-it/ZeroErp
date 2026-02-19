{% include-markdown "it/dbzero/vendite/manual/fn_resolve_lotto_task_execution_mode.md" %}
# ⚙️ Funzione `fn_resolve_lotto_task_execution_mode`

```sql
CREATE FUNCTION fn_resolve_lotto_task_execution_mode(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_lotto_task_execution_mode(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
 RETURNS TABLE(execution_mode text, annullabile boolean, resume_mode character varying, last_task_stato character varying, last_tentativo smallint, policy_meta jsonb, run_meta jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_policy vendite.fatturazione_pipeline_task_policy%ROWTYPE;
  v_last_run vendite.fatturazione_lotti_task_runs%ROWTYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve la modalita` di esecuzione task per lotto:
  --   RUN | SKIP | RESUME | RESET_REQUIRED.
  -- =========================================================
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_resolve_lotto_task_execution_mode', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',p_lotto_id,'fattura_id',NULL,
        'context',jsonb_build_object('detail','lotto_id obbligatorio','lotto_id',p_lotto_id)
      ),
      NULL::uuid,
      'lotto_id obbligatorio'
    );
  END IF;

  IF p_pipeline_id IS NULL OR p_pipeline_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_resolve_lotto_task_execution_mode', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',p_lotto_id,'fattura_id',NULL,
        'context',jsonb_build_object('detail','pipeline_id obbligatorio','pipeline_id',p_pipeline_id)
      ),
      NULL::uuid,
      'pipeline_id obbligatorio'
    );
  END IF;

  IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_resolve_lotto_task_execution_mode', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',p_lotto_id,'fattura_id',NULL,
        'context',jsonb_build_object('detail','task_code obbligatorio','task_code',p_task_code)
      ),
      NULL::uuid,
      'task_code obbligatorio'
    );
  END IF;

  SELECT p.*
    INTO v_policy
    FROM vendite.fatturazione_pipeline_task_policy p
   WHERE p.pipeline_id = p_pipeline_id
     AND p.task_code = p_task_code
     AND p.attivo IS TRUE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_resolve_lotto_task_execution_mode', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',p_lotto_id,'fattura_id',NULL,
        'context',jsonb_build_object(
          'detail','policy task non trovata',
          'pipeline_id',p_pipeline_id,
          'task_code',p_task_code
        )
      ),
      NULL::uuid,
      concat('Policy task non trovata pipeline:', p_pipeline_id::text, ' task:', p_task_code)
    );
  END IF;

  SELECT r.*
    INTO v_last_run
    FROM vendite.fatturazione_lotti_task_runs r
   WHERE r.lotto_id = p_lotto_id
     AND r.task_code = p_task_code
     AND r.stato_doc_fiscale_id IS NOT DISTINCT FROM p_stato_doc_fiscale_id
   ORDER BY r.tentativo DESC, r.id DESC
   LIMIT 1;

  IF NOT FOUND THEN
    RETURN QUERY
    SELECT
      'RUN'::text,
      v_policy.annullabile,
      v_policy.resume_mode,
      NULL::character varying,
      NULL::smallint,
      COALESCE(v_policy.meta, '{}'::jsonb),
      '{}'::jsonb;
    RETURN;
  END IF;

  RETURN QUERY
  SELECT
    CASE
      WHEN v_last_run.task_stato = 'COMPLETATO' THEN 'SKIP'
      WHEN v_last_run.task_stato = 'IN_ESECUZIONE' THEN
        CASE
          WHEN v_policy.resume_mode IN ('RESUME_TASK', 'RESUME_STEP') THEN 'RESUME'
          ELSE 'RESET_REQUIRED'
        END
      WHEN v_last_run.task_stato = 'ERRORE' THEN
        CASE
          WHEN v_policy.resume_mode IN ('RESUME_TASK', 'RESUME_STEP') THEN 'RESUME'
          ELSE 'RESET_REQUIRED'
        END
      WHEN v_last_run.task_stato = 'ANNULLATO' THEN 'RUN'
      ELSE 'RUN'
    END::text,
    v_policy.annullabile,
    v_policy.resume_mode,
    v_last_run.task_stato,
    v_last_run.tentativo,
    COALESCE(v_policy.meta, '{}'::jsonb),
    COALESCE(v_last_run.meta, '{}'::jsonb);
END
$function$

COMMENT ON FUNCTION vendite.fn_resolve_lotto_task_execution_mode(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
IS 'Risoluzione modalita` di esecuzione task lotto: RUN/SKIP/RESUME/RESET_REQUIRED.';
```

---
{% include-markdown "signature-core.md" %}
