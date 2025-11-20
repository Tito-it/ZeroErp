# ⚙️ Funzione `trgfn_contratti_normalize`

```sql
CREATE FUNCTION trgfn_contratti_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ----------------------------------------------------------------
  -- Generazione codice/anno/data SOLO in INSERT e SOLO se numero mancante
  IF TG_OP = 'INSERT' AND (NEW.numero IS NULL OR btrim(NEW.numero) = '') THEN
    NEW.numero := script.fn_generate_codice('contratto');
   
    -- imposta anno e data ai valori correnti di sistema
    if NEW.data IS NULL or NEW.data =0 THEN
      NEW.data := CURRENT_DATE;
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
