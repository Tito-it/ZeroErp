{% include-markdown "it/dbzero/script/manual/trgfn_generate_account_code_generic.md" %}
# ⚙️ Funzione `trgfn_generate_account_code_generic`

```sql
CREATE FUNCTION trgfn_generate_account_code_generic()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_generate_account_code_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_code_type TEXT := COALESCE(NULLIF(TG_ARGV[0], ''), TG_TABLE_NAME);
  BEGIN
    IF NEW.account_code IS NULL OR trim(NEW.account_code) = '' THEN
      NEW.account_code := script.fn_generate_codice(v_code_type);
    END IF;
    RETURN NEW;
  END;
  $function$
```