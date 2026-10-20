{% include-markdown "it/dbzero/vendite/manual/fn_get_pipeline_task_policy.md" %}
# ⚙️ Funzione `fn_get_pipeline_task_policy`

```sql
CREATE FUNCTION fn_get_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying)
 RETURNS TABLE(annullabile boolean, resume_mode character varying, attivo boolean, meta jsonb)
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF p_pipeline_id IS NULL OR p_pipeline_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_pipeline_task_policy', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_pipeline_id', 'valore', p_pipeline_id), NULL::uuid, 'p_pipeline_id obbligatorio e > 0');
    END IF;
    IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_pipeline_task_policy', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_task_code', 'valore', p_task_code), NULL::uuid, 'p_task_code obbligatorio');
    END IF;

    RETURN QUERY
    SELECT p.annullabile, p.resume_mode, p.attivo, p.meta
      FROM vendite.fatturazione_pipeline_task_policy p
     WHERE p.pipeline_id = p_pipeline_id AND p.task_code = p_task_code AND p.attivo IS TRUE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_pipeline_task_policy', 'E_CONFIG_MANCANTE',
            jsonb_build_object('pipeline_id', p_pipeline_id, 'task_code', p_task_code), NULL::uuid,
            concat('policy task pipeline:', p_pipeline_id, ' task:', p_task_code));
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying)
IS 'Policy attiva del task per pipeline (annullabile/resume_mode/meta).';
```

</div>

---
{% include-markdown "signature-core.md" %}
