{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_iu_clone_catasto_from_parent.md" %}
# ⚙️ Funzione `trgfn_iu_clone_catasto_from_parent`

```sql
CREATE FUNCTION trgfn_iu_clone_catasto_from_parent()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_iu_clone_catasto_from_parent()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Idempotenza e logica principale sono dentro la funzione clone
  PERFORM script.fn_clone_catasto_from_parent_by_istanza(NEW.id);
  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
