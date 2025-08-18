{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_istanze_utilities_ins_upd_clean_fields.md" %}
# ⚙️ Funzione `trgfn_istanze_utilities_ins_upd_clean_fields`

```sql
CREATE FUNCTION trgfn_istanze_utilities_ins_upd_clean_fields()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_ins_upd_clean_fields()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
   

   ----------------------------------------------------------------
   -- 1) Generazione codice automatico
   IF NEW.codice IS NULL THEN
     NEW.codice := script.fn_generate_codice('istanze_utilties');
   END IF;

   
   ------------------------------------------------------------------
   RETURN NEW;
 END;
 $function$
```
---
{% include-markdown "signature-core.md" %}
