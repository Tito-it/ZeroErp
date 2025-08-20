{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_istanze_utilities_upd_protect_codice.md" %}
# ⚙️ Funzione `trgfn_istanze_utilities_upd_protect_codice`

```sql
CREATE FUNCTION trgfn_istanze_utilities_upd_protect_codice()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_upd_protect_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP = 'UPDATE'
        AND OLD.codice IS NOT NULL
        AND NEW.codice IS DISTINCT FROM OLD.codice
      THEN
        
        PERFORM script.fn_log_and_raise_error(
          'database',
          TG_NAME,
          'E_COLONNA_NON_MODIFICABILE',
          jsonb_build_object('column','codice (istanza)','id',OLD.id),
          NULL::uuid,
          'codice (istanza)'
        );
      END IF;
      RETURN NEW;
    END;
    $function$
```

---
{% include-markdown "signature-core.md" %}
