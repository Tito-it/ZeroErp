{% include-markdown "it/dbzero/script/manual/trgfn_sync_stato_iso2.md" %}
# ⚙️ Funzione `trgfn_sync_stato_iso2`

```sql
CREATE FUNCTION trgfn_sync_stato_iso2()
```

**Definizione completa:**

<div data-search-exclude markdown>

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

COMMENT ON FUNCTION script.trgfn_sync_stato_iso2()
IS '
  Sincronizza il campo stato_iso2 
  basandosi sul valore di stato_id: prima di ogni INSERT o UPDATE,
  recupera da config.stati il codice_iso2 corrispondente e lo assegna
  a NEW.stato_iso2, garantendo che i due campi rimangano sempre
  coerenti.
';
```

</div>

---
{% include-markdown "signature-core.md" %}
