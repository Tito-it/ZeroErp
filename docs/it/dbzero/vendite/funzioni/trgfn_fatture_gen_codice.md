# ⚙️ Funzione `trgfn_fatture_gen_codice`

```sql
CREATE FUNCTION trgfn_fatture_gen_codice()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_gen_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN   IF (NEW.numero IS NULL OR NEW.numero = 0) THEN     NEW.numero := script.fn_generate_codice('fatture');   END IF;   RETURN NEW; END; $function$
```

---
{% include-markdown "signature-core.md" %}
