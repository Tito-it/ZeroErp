{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_vettori_gen_codice.md" %}
# ⚙️ Funzione `trgfn_vettori_gen_codice`

```sql
CREATE FUNCTION trgfn_vettori_gen_codice()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_vettori_gen_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN   IF (NEW.codice IS NULL OR btrim(NEW.codice::text) = '') THEN     NEW.codice := script.fn_generate_codice('vettori');   END IF;   RETURN NEW; END; $function$
```

</div>

---
{% include-markdown "signature-core.md" %}
