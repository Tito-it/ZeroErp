{% include-markdown "it/dbzero/vendite/manual/fn_get_lotto_task_last_run.md" %}
# ⚙️ Funzione `fn_get_lotto_task_last_run`

```sql
CREATE FUNCTION fn_get_lotto_task_last_run(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_lotto_task_last_run(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
 RETURNS TABLE(id bigint, lotto_id bigint, pipeline_id bigint, stato_doc_fiscale_id integer, task_code character varying, fase character varying, tentativo smallint, task_stato character varying, started_at timestamp with time zone, ended_at timestamp with time zone, error_code character varying, error_message text, meta jsonb)
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Guard: parametri obbligatori
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_lotto_task_last_run', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0'
        );
    END IF;

    IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_lotto_task_last_run', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_task_code', 'valore', p_task_code),
            NULL::uuid, 'p_task_code obbligatorio'
        );
    END IF;

    RETURN QUERY
    SELECT r.id, r.lotto_id, r.pipeline_id, r.stato_doc_fiscale_id,
           r.task_code, r.fase, r.tentativo, r.task_stato,
           r.started_at, r.ended_at, r.error_code, r.error_message, r.meta
      FROM vendite.fatturazione_lotti_task_runs r
     WHERE r.lotto_id = p_lotto_id
       AND r.task_code = p_task_code
       AND r.stato_doc_fiscale_id IS NOT DISTINCT FROM p_stato_doc_fiscale_id
     ORDER BY r.tentativo DESC, r.id DESC
     LIMIT 1;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_lotto_task_last_run(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
IS 'Ultimo run task per lotto/stato/task.';
```

</div>

---
{% include-markdown "signature-core.md" %}
