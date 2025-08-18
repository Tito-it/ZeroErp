{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_upd_protect_account_code.md" %}
# ⚙️ Funzione `trgfn_billing_account_upd_protect_account_code`

```sql
CREATE FUNCTION trgfn_billing_account_upd_protect_account_code()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_upd_protect_account_code()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP = 'UPDATE'
        AND OLD.codice IS NOT NULL
        AND NEW.codice IS DISTINCT FROM OLD.codice
      THEN
        
        PERFORM script.fn_log_and_raise_error(
          'database',
          TG_NAME,
          'E_COLONNA_NON_MODIFICABILE',
          jsonb_build_object('column','codice (account)','id',OLD.id),
          NULL::uuid,
          'codice (account)'
        );
      END IF;
      RETURN NEW;
    END;
    $function$
```
---
{% include-markdown "signature-core.md" %}
