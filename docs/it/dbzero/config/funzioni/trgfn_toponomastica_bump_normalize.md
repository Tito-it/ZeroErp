{% include-markdown "it/dbzero/config/manual/trgfn_toponomastica_bump_normalize.md" %}
# ⚙️ Funzione `trgfn_toponomastica_bump_normalize`

```sql
CREATE FUNCTION trgfn_toponomastica_bump_normalize()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_toponomastica_bump_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  
  UPDATE config.stradario_generale
     SET toponomastica_id = toponomastica_id  
   WHERE toponomastica_id = NEW.id;
  RETURN NEW;
END$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
