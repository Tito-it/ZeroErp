{% include-markdown "it/dbzero/vendite/manual/trgfn_fatturazione_lotti_gen_codice.md" %}
# ⚙️ Funzione `trgfn_fatturazione_lotti_gen_codice`

```sql
CREATE FUNCTION trgfn_fatturazione_lotti_gen_codice()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatturazione_lotti_gen_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN   IF (NEW.codice IS NULL OR btrim(NEW.codice::text) = '') THEN     NEW.codice := script.fn_generate_codice('lotti_fatturazione');   END IF;   RETURN NEW; END; $function$
```

</div>

---
{% include-markdown "signature-core.md" %}
