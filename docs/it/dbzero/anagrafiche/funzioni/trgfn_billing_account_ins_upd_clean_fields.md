# ⚙️ Funzione `trgfn_billing_account_ins_upd_clean_fields`

```sql
CREATE FUNCTION trgfn_billing_account_ins_upd_clean_fields()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_ins_upd_clean_fields()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
   

   ----------------------------------------------------------------
   -- 1) Generazione codice automatico
   IF NEW.account_code IS NULL THEN
     NEW.account_code := script.fn_generate_codice('billing_account');
   END IF;

   
   ------------------------------------------------------------------
   RETURN NEW;
 END;
 $function$
```
---
{% include-markdown "signature-core.md" %}
