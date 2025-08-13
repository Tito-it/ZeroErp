{% include-markdown "it/dbzero/script/manual/fn_ensure_logconn.md" %}
# ⚙️ Funzione `fn_ensure_logconn`

```sql
CREATE FUNCTION fn_ensure_logconn()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_ensure_logconn()
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE v_conn text := current_setting('myapp.dblink_log_connection', true);
BEGIN
  IF v_conn IS NULL OR length(trim(v_conn))=0 THEN RETURN; END IF;
  PERFORM public.dblink_connect('logconn', v_conn);  -- o dblink_connect_u se usi superuser
EXCEPTION WHEN duplicate_object THEN NULL;
END; 
$function$
```
---
{% include-markdown "signature-core.md" %}
