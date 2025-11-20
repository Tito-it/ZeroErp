# ⚙️ Funzione `trgfn_attivita_fatturabili_normalize`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  
  IF NEW.competenza_mese IS NOT NULL THEN
    NEW.competenza_mese := date_trunc('month', NEW.competenza_mese)::date;
  END IF;

   
  IF NEW.sorgente_tipo IS NOT NULL THEN
    NEW.sorgente_tipo := upper(btrim(NEW.sorgente_tipo));
    IF NEW.sorgente_riga IS NULL THEN
      NEW.sorgente_riga := 0;  
    END IF;
  END IF;

  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
