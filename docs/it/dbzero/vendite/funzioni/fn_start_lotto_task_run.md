{% include-markdown "it/dbzero/vendite/manual/fn_start_lotto_task_run.md" %}
# ⚙️ Funzione `fn_start_lotto_task_run`

```sql
CREATE FUNCTION fn_start_lotto_task_run(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying, p_fase character varying, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_start_lotto_task_run(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying, p_fase character varying DEFAULT NULL::character varying, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS TABLE(task_run_id bigint, tentativo smallint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tentativo vendite.fatturazione_lotti_task_runs.tentativo%TYPE;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_start_lotto_task_run', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;
    IF p_pipeline_id IS NULL OR p_pipeline_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_start_lotto_task_run', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_pipeline_id', 'valore', p_pipeline_id), NULL::uuid, 'p_pipeline_id obbligatorio e > 0');
    END IF;
    IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_start_lotto_task_run', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_task_code', 'valore', p_task_code), NULL::uuid, 'p_task_code obbligatorio');
    END IF;

    SELECT COALESCE(MAX(r.tentativo), 0)::SMALLINT + 1 INTO v_tentativo
      FROM vendite.fatturazione_lotti_task_runs r
     WHERE r.lotto_id = p_lotto_id AND r.task_code = p_task_code
       AND r.stato_doc_fiscale_id IS NOT DISTINCT FROM p_stato_doc_fiscale_id::INTEGER;

    RETURN QUERY
    INSERT INTO vendite.fatturazione_lotti_task_runs AS r (
        lotto_id, pipeline_id, stato_doc_fiscale_id, task_code, fase, tentativo,
        task_stato, started_at, ended_at, error_code, error_message, meta,
        attivo, data_insert, user_insert, data_update, user_update
    ) VALUES (
        p_lotto_id, p_pipeline_id, p_stato_doc_fiscale_id::INTEGER, p_task_code, p_fase, v_tentativo,
        'IN_ESECUZIONE', now(), NULL, NULL, NULL, COALESCE(p_meta, '{}'::JSONB),
        TRUE, now(), current_user, now(), current_user
    ) RETURNING r.id, r.tentativo;
END;
$function$

COMMENT ON FUNCTION vendite.fn_start_lotto_task_run(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying, p_fase character varying, p_meta jsonb)
IS 'Apre task run lotto in stato IN_ESECUZIONE e incrementa tentativo.';
```

---
{% include-markdown "signature-core.md" %}
