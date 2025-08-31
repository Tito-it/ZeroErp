# ⚙️ Funzione `trgfn_attivita_norm_competenza_mese`

```sql
CREATE FUNCTION trgfn_attivita_norm_competenza_mese()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_norm_competenza_mese()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN


  IF NEW.competenza_mese IS NOT NULL THEN
    NEW.competenza_mese := date_trunc('month', NEW.competenza_mese)::date;
  END IF;
  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
