{% include-markdown "it/dbzero/vendite/manual/fn_list_lotto_task_runs.md" %}
# ⚙️ Funzione `fn_list_lotto_task_runs`

```sql
CREATE FUNCTION fn_list_lotto_task_runs(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_lotto_task_runs(p_lotto_id bigint, p_stato_doc_fiscale_id bigint DEFAULT NULL::bigint, p_task_code character varying DEFAULT NULL::character varying)
 RETURNS TABLE(id bigint, lotto_id bigint, pipeline_id bigint, stato_doc_fiscale_id integer, task_code character varying, fase character varying, tentativo smallint, task_stato character varying, started_at timestamp with time zone, ended_at timestamp with time zone, error_code character varying, error_message text, meta jsonb)
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_lotto_task_runs', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    RETURN QUERY
    SELECT r.id, r.lotto_id, r.pipeline_id, r.stato_doc_fiscale_id,
           r.task_code, r.fase, r.tentativo, r.task_stato,
           r.started_at, r.ended_at, r.error_code, r.error_message, r.meta
      FROM vendite.fatturazione_lotti_task_runs r
     WHERE r.lotto_id = p_lotto_id
       AND (p_stato_doc_fiscale_id IS NULL OR r.stato_doc_fiscale_id = p_stato_doc_fiscale_id::INTEGER)
       AND (p_task_code IS NULL OR r.task_code = p_task_code)
     ORDER BY r.started_at ASC, r.id ASC;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_lotto_task_runs(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
IS 'Task run del lotto con filtri opzionali per stato/task.';
```

---
{% include-markdown "signature-core.md" %}
