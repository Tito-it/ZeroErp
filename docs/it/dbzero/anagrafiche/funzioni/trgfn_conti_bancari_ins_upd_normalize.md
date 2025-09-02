# ⚙️ Funzione `trgfn_conti_bancari_ins_upd_normalize`

```sql
CREATE FUNCTION trgfn_conti_bancari_ins_upd_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_conti_bancari_ins_upd_normalize()
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

  
  RETURN NEW;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
