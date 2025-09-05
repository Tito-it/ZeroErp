# ⚙️ Funzione `fn_norm_via`

```sql
CREATE FUNCTION fn_norm_via(p_topo text, p_via text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_norm_via(p_topo text, p_via text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$

 
  SELECT script.fn_norm_testo(coalesce(p_topo,'') || ' ' || coalesce(p_via,''));

$function$
```

---
{% include-markdown "signature-core.md" %}
