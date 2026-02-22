{% include-markdown "it/dbzero/vendite/manual/fn_list_attivita_lotto_task_runs.md" %}
# ⚙️ Funzione `fn_list_attivita_lotto_task_runs`

```sql
CREATE FUNCTION fn_list_attivita_lotto_task_runs(p_lotto_attivita_id bigint, p_branch_code character varying, p_task_code character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_attivita_lotto_task_runs(p_lotto_attivita_id bigint, p_branch_code character varying DEFAULT NULL::character varying, p_task_code character varying DEFAULT NULL::character varying)
 RETURNS TABLE(id bigint, lotto_attivita_id bigint, pipeline_id bigint, sorgente_tipo_id bigint, branch_code character varying, task_code character varying, fase character varying, tentativo smallint, task_stato character varying, block_scope character varying, depends_on jsonb, started_at timestamp with time zone, ended_at timestamp with time zone, error_code character varying, error_message text, meta jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_branch vendite.attivita_fatturabili_lotti_task_runs.branch_code%TYPE;
BEGIN
  -- Scopo: restituire i task-runs di un lotto attivita con filtri opzionali.
  IF p_lotto_attivita_id IS NULL OR p_lotto_attivita_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_attivita_lotto_task_runs', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_attivita_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto_attivita_id obbligatorio')),
      NULL::uuid,
      'lotto_attivita_id obbligatorio'
    );
  END IF;

  v_branch := NULLIF(btrim(p_branch_code), '');

  RETURN QUERY
  SELECT r.id,
         r.lotto_attivita_id,
         r.pipeline_id,
         r.sorgente_tipo_id,
         r.branch_code,
         r.task_code,
         r.fase,
         r.tentativo,
         r.task_stato,
         r.block_scope,
         r.depends_on,
         r.started_at,
         r.ended_at,
         r.error_code,
         r.error_message,
         r.meta
  FROM vendite.attivita_fatturabili_lotti_task_runs r
  WHERE r.lotto_attivita_id = p_lotto_attivita_id
    AND (v_branch IS NULL OR r.branch_code = v_branch)
    AND (p_task_code IS NULL OR r.task_code = p_task_code)
  ORDER BY r.started_at DESC, r.id DESC;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_attivita_lotto_task_runs(p_lotto_attivita_id bigint, p_branch_code character varying, p_task_code character varying)
IS 'Elenca task-runs runtime del lotto attivita con filtri opzionali per branch e task_code.';
```

---
{% include-markdown "signature-core.md" %}
