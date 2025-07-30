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
AS $function$
   DECLARE
     v_param_val   TEXT;
     v_lookup_id   TEXT;
     v_pk_col    TEXT;
   BEGIN
     
     -- -----------------------------------------------------
     -- Input
     -- p_table_schema: schema della tabella da cui recuperare il valore
     -- p_table_name: nome della tabella da cui recuperare il valore
     -- p_filter_column: colonna della tabella da usare come filtro (presumibilmente una PK o indice univoco esempio: codice_iso3)
     -- p_param_code: codice del parametro da cui recuperare il valore di filtro (esempio: 'state_code_iso3')
     -- Output
     -- v_lookup_id: valore trovato nella tabella, sempre come TEXT (caller deve castare in seguito) rappresenta id del record trovato.
     -- -----------------------------------------------------

     -- 1) Recupera il valore del parametro (testuale)
     v_param_val := script.fn_get_parameter_full(
       p_param_code,
       NULL,       -- tenant_id
       NULL,       -- user_id
       session_user,
       p_function_name 
     );

     -- 1.1) calcola la PK della tabella dinamica
       SELECT a.attname
         INTO v_pk_col
       FROM pg_attribute a
       JOIN pg_class   c ON a.attrelid   = c.oid
       JOIN pg_namespace n ON n.oid      = c.relnamespace
       WHERE n.nspname   = p_table_schema
         AND c.relname    = p_table_name
         AND a.attnum>0
       ORDER BY a.attnum
       LIMIT 1;

     -- 2) Esegue il lookup dinamico
     EXECUTE format(
       'SELECT %I::text
         FROM %I.%I
         WHERE %I = $1
         LIMIT 1',
       -- 
        v_pk_col,          -- 1° %I
         p_table_schema,    -- 2° %I
         p_table_name,      -- 3° %I
         p_filter_column    -- 4° %I
     )
     INTO v_lookup_id
     USING v_param_val;

     -- 3) Se non ho trovato nulla, loggo e sollevo tramite fn_log_and_raise_error
       IF v_lookup_id IS NULL THEN
         PERFORM script.fn_log_and_raise_error(
           'database',
           p_function_name ,
           'E_DEFAULT_ERRATO',
           jsonb_build_object(
             'tabella',   p_table_schema||'.'||p_table_name,
             'parametro', p_param_code,
             'valore',    v_param_val
           ),
           NULL::uuid,
           format(
             'La tabella %s parametro %s non ha valori per %s',
             p_table_schema||'.'||p_table_name,
             p_param_code,
             v_param_val
           )
         );
       END IF;

     RETURN v_lookup_id;
   END;
 $function$
```
---
{% include-markdown "signature-core.md" %}
