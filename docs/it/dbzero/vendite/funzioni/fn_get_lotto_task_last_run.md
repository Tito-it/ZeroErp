{% include-markdown "it/dbzero/vendite/manual/fn_get_lotto_task_last_run.md" %}
# ⚙️ Funzione `fn_get_lotto_task_last_run`

```sql
CREATE FUNCTION fn_get_lotto_task_last_run(p_lotto_id bigint, p_stato_doc_fiscale_id integer, p_task_code character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_lotto_task_last_run(p_lotto_id bigint, p_stato_doc_fiscale_id integer, p_task_code character varying)
 RETURNS TABLE(id bigint, lotto_id bigint, pipeline_id bigint, stato_doc_fiscale_id integer, task_code character varying, fase character varying, tentativo smallint, task_stato character varying, started_at timestamp with time zone, ended_at timestamp with time zone, error_code character varying, error_message text, meta jsonb)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce l'ultimo run disponibile per task+step+lotto.
  -- =========================================================
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_lotto_task_last_run', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',p_lotto_id,'fattura_id',NULL,
        'context',jsonb_build_object('detail','lotto_id obbligatorio','lotto_id',p_lotto_id)
      ),
      NULL::uuid,
      'lotto_id obbligatorio'
    );
  END IF;

  IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_lotto_task_last_run', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO','severity','C','code','E_GENERICO',
        'lotto_id',p_lotto_id,'fattura_id',NULL,
        'context',jsonb_build_object('detail','task_code obbligatorio','task_code',p_task_code)
      ),
      NULL::uuid,
      'task_code obbligatorio'
    );
  END IF;

  RETURN QUERY
  SELECT
    r.id, r.lotto_id, r.pipeline_id, r.stato_doc_fiscale_id,
    r.task_code, r.fase, r.tentativo, r.task_stato,
    r.started_at, r.ended_at, r.error_code, r.error_message, r.meta
  FROM vendite.fatturazione_lotti_task_runs r
  WHERE r.lotto_id = p_lotto_id
    AND r.task_code = p_task_code
    AND r.stato_doc_fiscale_id IS NOT DISTINCT FROM p_stato_doc_fiscale_id
  ORDER BY r.tentativo DESC, r.id DESC
  LIMIT 1;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_lotto_task_last_run(p_lotto_id bigint, p_stato_doc_fiscale_id integer, p_task_code character varying)
IS 'Restituisce l''ultimo run task per lotto/stato/task.';
```

---
{% include-markdown "signature-core.md" %}
