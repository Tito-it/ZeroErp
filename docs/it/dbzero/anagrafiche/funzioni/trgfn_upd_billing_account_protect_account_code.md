# ⚙️ Funzione `trgfn_upd_billing_account_protect_account_code`

```sql
CREATE FUNCTION trgfn_upd_billing_account_protect_account_code()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_upd_billing_account_protect_account_code()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP = 'UPDATE'
        AND OLD.account_code IS NOT NULL
        AND NEW.account_code IS DISTINCT FROM OLD.account_code
      THEN
        
        PERFORM script.fn_log_and_raise_error(
          'database',
          TG_NAME,
          'E_COLONNA_NON_MODIFICABILE',
          jsonb_build_object('column','account_code','id',OLD.id),
          NULL::uuid,
          'account_code'
        );
      END IF;
      RETURN NEW;
    END;
    $function$
```
---
{% include-markdown "signature-core.md" %}
