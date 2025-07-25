# ⚙️ Funzione `trgfn_parameters_audit`

```sql
CREATE FUNCTION trgfn_parameters_audit()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameters_audit()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_old   TEXT := OLD.default_value;
  v_new   TEXT;
BEGIN
  -- calcolo solo la parte che differisce
  IF TG_OP = 'UPDATE' THEN
    v_new := NEW.default_value;
  ELSE  -- DELETE
    v_new := NULL;
  END IF;

  -- unico INSERT con action = TG_OP (UPDATE o DELETE)
  INSERT INTO config.parameters_audit(
    parameter_code,
    action,
    old_value,
    new_value,
    reason,
    user_insert,
    data_insert
  ) VALUES (
    OLD.code,
    TG_OP,
    v_old,
    v_new,
    NULL,
    current_user,
    now()
  );

  RETURN NULL;
END;
$function$
```
---
{% include-markdown "signature-core.md" %}
