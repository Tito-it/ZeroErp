{% include-markdown "it/dbzero/script/manual/fn_get_default_by_param.md" %}
# ⚙️ Funzione `fn_get_default_by_param`

```sql
CREATE FUNCTION fn_get_default_by_param(p_table_schema text, p_table_name text, p_filter_column text, p_param_code text, p_function_name text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_default_by_param(p_table_schema text, p_table_name text, p_filter_column text, p_param_code text, p_function_name text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_param_val  text;
  v_lookup_id  text;
  v_pk_col     text;
BEGIN

    
    
    
    
    
    
    
    
    

  
  v_param_val := script.fn_get_parameter_full(
    p_param_code,
    NULL,                                     
    NULL,                                     
    current_setting('app.session_key', true), 
    p_function_name
  );

  
  SELECT a.attname
    INTO v_pk_col
  FROM pg_index i
  JOIN pg_class c      ON c.oid = i.indrelid
  JOIN pg_namespace n  ON n.oid = c.relnamespace
  JOIN pg_attribute a  ON a.attrelid = c.oid AND a.attnum = ANY(i.indkey)
  WHERE n.nspname = p_table_schema
    AND c.relname  = p_table_name
    AND i.indisprimary
  LIMIT 1;

  IF v_pk_col IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      p_function_name,
      'E_DEFAULT_ERRATO',
      jsonb_build_object(
        'tabella',   p_table_schema||'.'||p_table_name,
        'parametro', p_param_code,
        'valore',    v_param_val
      ),
      NULL::uuid,
      p_table_schema, p_table_name
    );
    
     
  END IF;

  
  EXECUTE format(
    'SELECT %I::text FROM %I.%I WHERE %I::text = $1 LIMIT 1',
    v_pk_col, p_table_schema, p_table_name, p_filter_column
  )
  INTO v_lookup_id
  USING v_param_val;

  
  IF v_lookup_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      p_function_name,
      'E_DEFAULT_ERRATO',
      jsonb_build_object(
        'tabella',   p_table_schema||'.'||p_table_name,
        'parametro', p_param_code,
        'valore',    v_param_val
      ),
      NULL::uuid,
        p_table_schema||'.'||p_table_name,
        p_param_code,
        v_param_val
      
    );
    
     
     
  END IF;

  RETURN v_lookup_id;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
