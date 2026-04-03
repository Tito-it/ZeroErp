{% include-markdown "it/dbzero/script/manual/fn_get_parameter_full.md" %}
# ⚙️ Funzione `fn_get_parameter_full`

```sql
CREATE FUNCTION fn_get_parameter_full(p_code text, p_emittente_fiscale_id bigint, p_django_user_id integer, p_group_ids integer[], p_session_key text, p_function_name text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_parameter_full(p_code text, p_emittente_fiscale_id bigint DEFAULT NULL::bigint, p_django_user_id integer DEFAULT NULL::integer, p_group_ids integer[] DEFAULT NULL::integer[], p_session_key text DEFAULT NULL::text, p_function_name text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_param_id  config.parameters.id%TYPE;
    v_default   config.parameters.default_value%TYPE;
    v_result    config.parameter_overrides.overridden_value%TYPE;
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

    
    
    
    
    SELECT COALESCE(
        
        (SELECT po.overridden_value
         FROM config.parameter_overrides po
         WHERE po.parameter_id = v_param_id
           AND po.django_user_id = p_django_user_id
           AND po.attivo = true
         LIMIT 1),
        
        (SELECT po.overridden_value
         FROM config.parameter_overrides po
         WHERE po.parameter_id = v_param_id
           AND po.django_group_id = ANY(p_group_ids)
           AND po.attivo = true
         ORDER BY po.id
         LIMIT 1),
        
        (SELECT po.overridden_value
         FROM config.parameter_overrides po
         WHERE po.parameter_id = v_param_id
           AND po.emittente_fiscale_id = p_emittente_fiscale_id
           AND po.attivo = true
         LIMIT 1),
        
        (SELECT po.overridden_value
         FROM config.parameter_overrides po
         WHERE po.parameter_id = v_param_id
           AND po.session_key = p_session_key
           AND po.attivo = true
         LIMIT 1),
        
        (SELECT po.overridden_value
         FROM config.parameter_overrides po
         WHERE po.parameter_id = v_param_id
           AND po.function_name = p_function_name
           AND po.attivo = true
         LIMIT 1),
        
        v_default
    ) INTO v_result;

    RETURN v_result;
END;
$function$

COMMENT ON FUNCTION script.fn_get_parameter_full(p_code text, p_emittente_fiscale_id bigint, p_django_user_id integer, p_group_ids integer[], p_session_key text, p_function_name text)
IS 'Risoluzione parametro con precedenza: user -> group -> emittente -> session -> function -> default. Usa config.parameter_overrides con emittente_fiscale_id.';
```

---
{% include-markdown "signature-core.md" %}
