# ⚙️ Funzione `trgfn_clienti_set_periodo`

```sql
CREATE FUNCTION trgfn_clienti_set_periodo()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_set_periodo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  fine_esclusiva DATE;
BEGIN
  -- Trigger function: normalizza "periodo" = [data_attivazione, data_chiusura+1)  
  -- Inclusività della data_chiusura: se valorizzata, usiamo (data_chiusura + 1 giorno) come estremo esclusivo
  fine_esclusiva := CASE
    WHEN NEW.data_chiusura IS NULL THEN 'infinity'::date
    ELSE NEW.data_chiusura + 1
  END;
  IF NEW.data_attivazione IS NOT NULL THEN
    NEW.periodo := daterange(NEW.data_attivazione, fine_esclusiva, '[)');
  ELSE
    NEW.periodo := NULL;
  END IF;
  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
