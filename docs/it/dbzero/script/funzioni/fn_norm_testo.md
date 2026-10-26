{% include-markdown "it/dbzero/script/manual/fn_norm_testo.md" %}
# ⚙️ Funzione `fn_norm_testo`

```sql
CREATE FUNCTION fn_norm_testo(p_txt text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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

</div>

---
{% include-markdown "signature-core.md" %}
