{% include-markdown "it/dbzero/dbops/manual/fn_get_pipeline_task_implementation.md" %}
# ⚙️ Funzione `fn_get_pipeline_task_implementation`

```sql
CREATE FUNCTION fn_get_pipeline_task_implementation(p_dominio_id bigint, p_task_code text, p_implementation_key text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_pipeline_task_implementation(p_dominio_id bigint, p_task_code text, p_implementation_key text DEFAULT NULL::text)
 RETURNS TABLE(handler_code text, implementation_key text, task_registry_id bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve l'implementazione valida per un task.
  --
  -- Regole:
  --   - p_dominio_id obbligatorio (>0)
  --   - p_task_code obbligatorio (non vuoto)
  --   - se p_implementation_key NULL/empty -> default
  --   - se richiesta non valida -> fallback default
  -- =========================================================

  IF p_dominio_id IS NULL OR p_dominio_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'dbops.fn_get_pipeline_task_implementation', 'E_GENERICO',
      jsonb_build_object('detail', 'p_dominio_id obbligatorio'),
      NULL::uuid,
      'p_dominio_id obbligatorio'
    );
  END IF;

  IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'dbops.fn_get_pipeline_task_implementation', 'E_GENERICO',
      jsonb_build_object('detail', 'p_task_code obbligatorio'),
      NULL::uuid,
      'p_task_code obbligatorio'
    );
  END IF;

  PERFORM dbops.fn_check_pipeline_task_registered(p_dominio_id, p_task_code);

  -- 1) Prova la richiesta esplicita se presente
  IF p_implementation_key IS NOT NULL AND btrim(p_implementation_key) <> '' THEN
    RETURN QUERY
    SELECT i.handler_code, i.implementation_key, i.task_registry_id
      FROM dbops.pipeline_task_registry r
      JOIN dbops.pipeline_task_registry_impl i
        ON i.task_registry_id = r.id
     WHERE r.dominio_id = p_dominio_id
       AND r.task_code = p_task_code
       AND r.attivo IS TRUE
       AND i.attivo IS TRUE
       AND i.implementation_key = p_implementation_key
     ORDER BY i.id
     LIMIT 1;

    IF FOUND THEN
      RETURN;
    END IF;
  END IF;

  -- 2) Fallback su default
  RETURN QUERY
  SELECT i.handler_code, i.implementation_key, i.task_registry_id
    FROM dbops.pipeline_task_registry r
    JOIN dbops.pipeline_task_registry_impl i
      ON i.task_registry_id = r.id
   WHERE r.dominio_id = p_dominio_id
     AND r.task_code = p_task_code
     AND r.attivo IS TRUE
     AND i.attivo IS TRUE
     AND i.is_default IS TRUE
   ORDER BY i.id
   LIMIT 1;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'dbops.fn_get_pipeline_task_implementation', 'E_GENERICO',
      jsonb_build_object('detail', 'Implementazione non trovata', 'dominio_id', p_dominio_id, 'task_code', p_task_code),
      NULL::uuid,
      concat('Implementazione non trovata per task: ', p_task_code)
    );
  END IF;
END;
$function$

COMMENT ON FUNCTION dbops.fn_get_pipeline_task_implementation(p_dominio_id bigint, p_task_code text, p_implementation_key text)
IS 'Risoluzione implementazione task con fallback su default.';
```

</div>

---
{% include-markdown "signature-core.md" %}
