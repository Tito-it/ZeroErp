{% include-markdown "it/dbzero/script/manual/fn_get_parameter_full.md" %}
# ⚙️ Funzione `fn_get_parameter_full`

```sql
CREATE FUNCTION fn_get_parameter_full(p_code text, p_tenant_id integer, p_user_id integer, p_session_key text, p_function_name text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_parameter_full(p_code text, p_tenant_id integer DEFAULT NULL::integer, p_user_id integer DEFAULT NULL::integer, p_session_key text DEFAULT NULL::text, p_function_name text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_param_id    BIGINT;
    v_default     TEXT;
    v_override    TEXT;
   
BEGIN
    

    -- 1. Recupera id e default_value del parametro
    SELECT id, default_value
      INTO v_param_id, v_default
      FROM config.parameters
    WHERE code = p_code;

    IF NOT FOUND THEN
        -- Se il parametro non esiste, logga l'errore e solleva un'eccezione  
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_get_parameter_full',
            'ERRORE_PARAMETRI_TABELLA',
            jsonb_build_object(
              'codice_parametro', p_code,
              'nome_tabella',      'config.parameters'
            ),
            NULL::uuid,                                        
            'config.parameters', p_code::text 
          );

    END IF;

    -- 2. Cerca l'override più specifico
    SELECT overridden_value
      INTO v_override
      FROM config.parameter_overrides
    WHERE parameter_id = v_param_id
      AND (
          (function_name   IS NOT NULL AND function_name   = p_function_name)
        OR (session_key     IS NOT NULL AND session_key     = p_session_key)
        OR (user_id         IS NOT NULL AND user_id         = p_user_id)
        OR (tenant_id       IS NOT NULL AND tenant_id       = p_tenant_id)
      )
    ORDER BY
      CASE
        WHEN function_name   = p_function_name THEN 1
        WHEN session_key     = p_session_key   THEN 2
        WHEN user_id         = p_user_id       THEN 3
        WHEN tenant_id       = p_tenant_id     THEN 4
        ELSE 5
      END
    LIMIT 1;

    -- 3. Se trovato un override, restituiscilo; altrimenti il default
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
