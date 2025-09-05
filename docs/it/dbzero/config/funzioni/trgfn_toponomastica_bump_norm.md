# ⚙️ Funzione `trgfn_toponomastica_bump_norm`

```sql
CREATE FUNCTION trgfn_toponomastica_bump_norm()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_toponomastica_bump_norm()
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

---
{% include-markdown "signature-core.md" %}
