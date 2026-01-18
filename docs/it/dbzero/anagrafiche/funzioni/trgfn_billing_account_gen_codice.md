# ⚙️ Funzione `trgfn_billing_account_gen_codice`

```sql
CREATE FUNCTION trgfn_billing_account_gen_codice()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_gen_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN   IF (NEW.codice IS NULL OR btrim(NEW.codice::text) = '') THEN     NEW.codice := script.fn_generate_codice('billing_account');   END IF;   RETURN NEW; END; $function$
```

---
{% include-markdown "signature-core.md" %}
