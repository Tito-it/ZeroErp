{% include-markdown "it/dbzero/script/manual/trgfn_audit_data_user_generic.md" %}
# ⚙️ Funzione `trgfn_audit_data_user_generic`

```sql
CREATE FUNCTION trgfn_audit_data_user_generic()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_audit_data_user_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.data_update := CURRENT_TIMESTAMP;
  NEW.user_update := CURRENT_USER;
  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
