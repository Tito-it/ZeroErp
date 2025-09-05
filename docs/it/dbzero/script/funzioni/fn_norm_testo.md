# ⚙️ Funzione `fn_norm_testo`

```sql
CREATE FUNCTION fn_norm_testo(p_txt text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_norm_testo(p_txt text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$

  
  SELECT
    trim(
      regexp_replace(
        regexp_replace(
          lower(unaccent(coalesce(p_txt,''))),
          '[^\w\s]', ' ', 'g'           
        ),
        '\s+', ' ', 'g'               
      )
    )

$function$
```

---
{% include-markdown "signature-core.md" %}
