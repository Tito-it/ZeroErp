# ⚙️ Funzione `fn_log`

```sql
CREATE FUNCTION fn_log(p_area text, p_function_name text, p_error_code text, p_context jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_log(p_area text, p_function_name text, p_error_code text, p_context jsonb)
 RETURNS void
 LANGUAGE sql
AS $function$
   -- 1) Forma base: 4 argomenti
  SELECT script.fn_log_error_only($1,$2,$3,$4,NULL::uuid,VARIADIC ARRAY[]::text[] )
$function$
```

---
{% include-markdown "signature-core.md" %}
