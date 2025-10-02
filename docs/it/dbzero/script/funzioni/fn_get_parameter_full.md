{% include-markdown "it/dbzero/script/manual/fn_get_parameter_full.md" %}
# ⚙️ Funzione `fn_get_parameter_full`

```sql
CREATE FUNCTION fn_get_parameter_full(p_code text, p_tenant_id integer, p_django_user_id integer, p_group_ids integer[], p_session_key text, p_function_name text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_parameter_full(p_code text, p_tenant_id integer DEFAULT NULL::integer, p_django_user_id integer DEFAULT NULL::integer, p_group_ids integer[] DEFAULT NULL::integer[], p_session_key text DEFAULT NULL::text, p_function_name text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_param_id  BIGINT;
    v_default   TEXT;
    v_override  TEXT;
BEGIN
    
    SELECT id, default_value
      INTO v_param_id, v_default
    FROM config.parameters
    WHERE code = p_code;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_get_parameter_full',
            'ERRORE_PARAMETRI_TABELLA',
            jsonb_build_object(
                'codice_parametro', p_code,
                'nome_tabella',      'config.parameters'
            ),
            NULL::uuid,
            'config.parameters',
            p_code::text
        );
        RAISE EXCEPTION 'Parametro % non trovato in config.parameters', p_code
          USING ERRCODE = '22023';
    END IF;

    
    
    SELECT po.overridden_value
      INTO v_override
    FROM config.parameter_overrides po
    WHERE po.parameter_id = v_param_id
      AND (
        (p_django_user_id IS NOT NULL AND po.django_user_id = p_django_user_id) OR
        (p_group_ids     IS NOT NULL AND po.django_group_id = ANY(p_group_ids)) OR
        (p_tenant_id     IS NOT NULL AND po.tenant_id       = p_tenant_id) OR
        (p_session_key   IS NOT NULL AND po.session_key     = p_session_key) OR
        (p_function_name IS NOT NULL AND po.function_name   = p_function_name)
      )
    ORDER BY
      CASE
        WHEN po.django_user_id = p_django_user_id THEN 1
        WHEN (p_group_ids IS NOT NULL AND po.django_group_id = ANY(p_group_ids)) THEN 2
        WHEN po.tenant_id   = p_tenant_id   THEN 3
        WHEN po.session_key = p_session_key THEN 4
        WHEN po.function_name = p_function_name THEN 5
        ELSE 6
      END,
      po.id
    LIMIT 1;

    
    IF FOUND THEN
        RETURN v_override;
    ELSE
        RETURN v_default;
    END IF;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
