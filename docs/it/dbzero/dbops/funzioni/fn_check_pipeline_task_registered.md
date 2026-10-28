{% include-markdown "it/dbzero/dbops/manual/fn_check_pipeline_task_registered.md" %}
# ⚙️ Funzione `fn_check_pipeline_task_registered`

```sql
CREATE FUNCTION fn_check_pipeline_task_registered(p_dominio_id bigint, p_task_code text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_check_pipeline_task_registered(p_dominio_id bigint, p_task_code text)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_exists boolean;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Verifica esistenza task attivo nel registry per dominio.
  --
  -- Regole:
  --   - p_dominio_id obbligatorio (>0)
  --   - p_task_code obbligatorio (non vuoto)
  -- =========================================================

  IF p_dominio_id IS NULL OR p_dominio_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'dbops.fn_check_pipeline_task_registered', 'E_GENERICO',
      jsonb_build_object('detail', 'p_dominio_id obbligatorio'),
      NULL::uuid,
      'p_dominio_id obbligatorio'
    );
  END IF;

  IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'dbops.fn_check_pipeline_task_registered', 'E_GENERICO',
      jsonb_build_object('detail', 'p_task_code obbligatorio'),
      NULL::uuid,
      'p_task_code obbligatorio'
    );
  END IF;

  SELECT TRUE
    INTO v_exists
    FROM dbops.pipeline_task_registry r
    JOIN dbops.domini_task d
      ON d.id = r.dominio_id
   WHERE r.dominio_id = p_dominio_id
     AND r.task_code = p_task_code
     AND r.attivo IS TRUE
     AND d.attivo IS TRUE
   LIMIT 1;

  IF v_exists IS NOT TRUE THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'dbops.fn_check_pipeline_task_registered', 'E_GENERICO',
      jsonb_build_object('detail', 'Task non registrato', 'dominio_id', p_dominio_id, 'task_code', p_task_code),
      NULL::uuid,
      concat('Task non registrato: ', p_task_code)
    );
  END IF;

  RETURN TRUE;
END;
$function$

COMMENT ON FUNCTION dbops.fn_check_pipeline_task_registered(p_dominio_id bigint, p_task_code text)
IS 'Verifica che un task sia registrato e attivo nel registry per dominio.';
```

</div>

---
{% include-markdown "signature-core.md" %}
