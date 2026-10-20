{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_vettori_normalize.md" %}
# ⚙️ Funzione `trgfn_vettori_normalize`

```sql
CREATE FUNCTION trgfn_vettori_normalize()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_vettori_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_vettori_normalize()
IS 'Normalize: no-op; generazione codice demandata al sistema_codici.';
```

</div>

---
{% include-markdown "signature-core.md" %}
