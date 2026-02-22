{% include-markdown "it/dbzero/vendite/manual/fn_get_attivita_pipeline_task_policy.md" %}
# ⚙️ Funzione `fn_get_attivita_pipeline_task_policy`

```sql
CREATE FUNCTION fn_get_attivita_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying, p_branch_code character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_attivita_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying, p_branch_code character varying DEFAULT 'DEFAULT'::character varying)
 RETURNS TABLE(annullabile boolean, resume_mode character varying, block_scope character varying, depends_on jsonb, attivo boolean, meta jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_branch vendite.attivita_fatturabili_pipeline_task_policy.branch_code%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire la policy runtime task per pipeline attivita,
  --   con fallback branch-specific -> DEFAULT.
  --
  -- Regole:
  --   - p_pipeline_id e p_task_code obbligatori
  --   - priorita` branch richiesto
  --   - fallback su branch_code='DEFAULT'
  -- =========================================================
  IF p_pipeline_id IS NULL OR p_pipeline_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_attivita_pipeline_task_policy', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','pipeline_id obbligatorio','pipeline_id',p_pipeline_id)),
      NULL::uuid,
      'pipeline_id obbligatorio'
    );
  END IF;

  IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_attivita_pipeline_task_policy', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','task_code obbligatorio')),
      NULL::uuid,
      'task_code obbligatorio'
    );
  END IF;

  v_branch := COALESCE(NULLIF(btrim(p_branch_code), ''), 'DEFAULT');

  RETURN QUERY
  SELECT p.annullabile, p.resume_mode, p.block_scope, p.depends_on, p.attivo, p.meta
  FROM vendite.attivita_fatturabili_pipeline_task_policy p
  WHERE p.pipeline_id = p_pipeline_id
    AND p.task_code = p_task_code
    AND p.branch_code IN (v_branch, 'DEFAULT')
    AND p.attivo IS TRUE
  ORDER BY CASE WHEN p.branch_code = v_branch THEN 0 ELSE 1 END
  LIMIT 1;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_attivita_pipeline_task_policy', 'E_GENERICO',
      jsonb_build_object(
        'scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','policy task non trovata','pipeline_id',p_pipeline_id,'task_code',p_task_code,'branch_code',v_branch)
      ),
      NULL::uuid,
      'Policy task pipeline attivita non trovata'
    );
  END IF;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_attivita_pipeline_task_policy(p_pipeline_id bigint, p_task_code character varying, p_branch_code character varying)
IS 'Restituisce policy runtime task per pipeline attivita con fallback branch specifico -> DEFAULT.';
```

---
{% include-markdown "signature-core.md" %}
