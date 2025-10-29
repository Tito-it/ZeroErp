# ⚙️ Funzione `trgfn_ordini_norm`

```sql
CREATE FUNCTION trgfn_ordini_norm()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_norm()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ----------------------------------------------------------------
  -- Generazione codice/anno/data SOLO in INSERT e SOLO se numero mancante
  IF TG_OP = 'INSERT' AND (NEW.numero IS NULL OR btrim(NEW.numero) = '') THEN
    NEW.numero := script.fn_generate_codice('ordine');
   
    -- imposta anno e data ai valori correnti di sistema
    NEW.anno := EXTRACT(YEAR FROM CURRENT_DATE)::smallint;
    NEW.data := CURRENT_DATE;
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
