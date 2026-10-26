{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_conti_bancari_normalize.md" %}
# ⚙️ Funzione `trgfn_conti_bancari_normalize`

```sql
CREATE FUNCTION trgfn_conti_bancari_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_conti_bancari_normalize()
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

COMMENT ON FUNCTION anagrafiche.trgfn_conti_bancari_normalize()
IS 'Trigger function BEFORE INSERT/UPDATE su anagrafiche.conti_bancari:
 - Normalizza IBAN/BIC (uppercase, no spazi)
 - Deriva paese da IBAN se mancante
 - Aggiorna audit (data_update, user_insert/user_update).';
```

</div>

---
{% include-markdown "signature-core.md" %}
