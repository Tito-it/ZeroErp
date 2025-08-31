# ⚙️ Funzione `trgfn_conti_ins_upd_normalize`

```sql
CREATE FUNCTION trgfn_conti_ins_upd_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_conti_ins_upd_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF NEW.iban IS NOT NULL THEN
    NEW.iban := upper(regexp_replace(NEW.iban, '\s+', '', 'g'));
    IF NEW.paese IS NULL AND length(NEW.iban) >= 2 THEN
      NEW.paese := substr(NEW.iban, 1, 2);
    END IF;
  END IF;

  IF NEW.bic_swift IS NOT NULL THEN
    NEW.bic_swift := upper(regexp_replace(NEW.bic_swift, '\s+', '', 'g'));
  END IF;

  -- Audit: aggiorna sempre data_update; gestisce user_insert/user_update
  NEW.data_update := now();
  IF TG_OP = 'INSERT' AND NEW.user_insert IS NULL THEN
    NEW.user_insert := current_user;
  ELSE
    NEW.user_update := current_user;
  END IF;

  RETURN NEW;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
