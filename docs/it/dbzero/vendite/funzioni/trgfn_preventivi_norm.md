# ⚙️ Funzione `trgfn_preventivi_norm`

```sql
CREATE FUNCTION trgfn_preventivi_norm()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_norm()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Normalizzazione automatica al 1° del mese ---
  IF NEW.competenza_mese IS NOT NULL THEN
    NEW.competenza_mese := date_trunc('month', NEW.competenza_mese)::date;
  END IF;
  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
