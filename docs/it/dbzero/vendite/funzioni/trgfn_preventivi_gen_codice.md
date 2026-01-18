# ⚙️ Funzione `trgfn_preventivi_gen_codice`

```sql
CREATE FUNCTION trgfn_preventivi_gen_codice()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_gen_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN   IF (NEW.numero IS NULL OR btrim(NEW.numero::text) = '') THEN     NEW.numero := script.fn_generate_codice('preventivo');   END IF;   RETURN NEW; END; $function$
```

---
{% include-markdown "signature-core.md" %}
