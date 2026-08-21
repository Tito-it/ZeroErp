{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_gen_codice.md" %}
# ⚙️ Funzione `trgfn_soggetti_gen_codice`

```sql
CREATE FUNCTION trgfn_soggetti_gen_codice()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_gen_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN   IF (NEW.codice IS NULL OR btrim(NEW.codice::text) = '') THEN     NEW.codice := script.fn_generate_codice('soggetto');   END IF;   RETURN NEW; END; $function$
```

---
{% include-markdown "signature-core.md" %}
