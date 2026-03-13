{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_normalize.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_normalize`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_normalize()
IS 'Normalize: no-op; generazione codice demandata al sistema_codici.';
```

---
{% include-markdown "signature-core.md" %}
