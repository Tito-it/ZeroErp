{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_istanze_utilities_normalize.md" %}
# ⚙️ Funzione `trgfn_istanze_utilities_normalize`

```sql
CREATE FUNCTION trgfn_istanze_utilities_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_istanze_utilities_normalize()
IS 'Normalize: no-op; generazione codice demandata al sistema_codici.';
```

</div>

---
{% include-markdown "signature-core.md" %}
