{% include-markdown "it/dbzero/vendite/manual/fn_check_pipeline_task_policy.md" %}
# ⚙️ Funzione `fn_check_pipeline_task_policy`

```sql
CREATE FUNCTION fn_check_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_exists boolean;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Verifica esistenza policy task attiva per pipeline.
  -- =========================================================
  IF p_pipeline_id IS NULL OR p_pipeline_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_check_pipeline_task_policy', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','pipeline_id obbligatorio','pipeline_id',p_pipeline_id)
      ),
      NULL::uuid,
      'pipeline_id obbligatorio'
    );
  END IF;

  IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_check_pipeline_task_policy', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','task_code obbligatorio','task_code',p_task_code)
      ),
      NULL::uuid,
      'task_code obbligatorio'
    );
  END IF;

  SELECT EXISTS (
    SELECT 1
    FROM vendite.fatturazione_pipeline_task_policy p
    WHERE p.pipeline_id = p_pipeline_id
      AND p.task_code = p_task_code
      AND p.attivo IS TRUE
  )
  INTO v_exists;

  IF NOT v_exists THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_check_pipeline_task_policy', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object(
          'detail','policy task non configurata',
          'pipeline_id',p_pipeline_id,
          'task_code',p_task_code
        )
      ),
      NULL::uuid,
      concat('Policy task non configurata pipeline:', p_pipeline_id::text, ' task:', p_task_code)
    );
  END IF;

  RETURN v_exists;
END
$function$

COMMENT ON FUNCTION vendite.fn_check_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying)
IS 'Verifica presenza di policy task attiva per pipeline; in assenza genera errore applicativo.';
```

---
{% include-markdown "signature-core.md" %}
