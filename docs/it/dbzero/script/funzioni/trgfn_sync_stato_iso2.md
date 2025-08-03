{% include-markdown "it/dbzero/script/manual/trgfn_sync_stato_iso2.md" %}
# ⚙️ Funzione `trgfn_sync_stato_iso2`

```sql
CREATE FUNCTION trgfn_sync_stato_iso2()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_sync_stato_iso2()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
-- Sincronizza stato_iso2 da config.stati basandosi su stato_id
  SELECT s.codice_iso2
    INTO NEW.stato_iso2
    FROM config.stati s
   WHERE s.id = NEW.stato_id;
  RETURN NEW;
END;
$function$
```
---
{% include-markdown "signature-core.md" %}
