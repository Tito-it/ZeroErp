# ⚙️ Funzione `trgfn_resellers_protect_codice`

```sql
CREATE FUNCTION trgfn_resellers_protect_codice()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_resellers_protect_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- ===========================================================
    -- A10 Protect: codice non modificabile dopo creazione
    -- ===========================================================
  IF TG_OP = 'UPDATE'
    AND OLD.codice IS NOT NULL
    AND NEW.codice IS DISTINCT FROM OLD.codice THEN
    PERFORM script.fn_log_and_raise_error(
      'database', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('table','anagrafiche.resellers','column','codice','id',OLD.id),
      NULL::uuid, 'codice (reseller)'
    );
  END IF;
  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
