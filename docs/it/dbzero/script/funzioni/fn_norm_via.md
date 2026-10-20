{% include-markdown "it/dbzero/script/manual/fn_norm_via.md" %}
# ⚙️ Funzione `fn_norm_via`

```sql
CREATE FUNCTION fn_norm_via(p_topo text, p_via text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_norm_via(p_topo text, p_via text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$

 
  SELECT script.fn_norm_testo(coalesce(p_topo,'') || ' ' || coalesce(p_via,''));

$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
