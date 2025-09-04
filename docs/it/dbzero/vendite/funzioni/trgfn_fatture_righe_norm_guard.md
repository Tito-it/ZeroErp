# ⚙️ Funzione `trgfn_fatture_righe_norm_guard`

```sql
CREATE FUNCTION trgfn_fatture_righe_norm_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_righe_norm_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_parent INTEGER;
BEGIN
  -- Normalizza source_tipo (UPPER+TRIM) e default BA = parent se NULL
  IF NEW.source_tipo IS NOT NULL THEN
    NEW.source_tipo := upper(btrim(NEW.source_tipo));
  END IF;

  IF NEW.dest_billing_account_id IS NULL THEN
    SELECT billing_account_id
      INTO v_parent
    FROM vendite.fatture
    WHERE id = NEW.fattura_id;
    NEW.dest_billing_account_id := v_parent;
  END IF;

  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
