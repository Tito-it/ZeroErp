{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_resellers_normalize.md" %}
# ⚙️ Funzione `trgfn_resellers_normalize`

```sql
CREATE FUNCTION trgfn_resellers_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_resellers_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_resellers_normalize()
IS 'Normalize: no-op; generazione codice demandata al sistema_codici.';
```

---
{% include-markdown "signature-core.md" %}
