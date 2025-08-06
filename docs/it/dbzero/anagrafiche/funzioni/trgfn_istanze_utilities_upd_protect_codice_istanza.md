{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_istanze_utilities_upd_protect_codice_istanza.md" %}
# ⚙️ Funzione `trgfn_istanze_utilities_upd_protect_codice_istanza`

```sql
CREATE FUNCTION trgfn_istanze_utilities_upd_protect_codice_istanza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_upd_protect_codice_istanza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP = 'UPDATE'
        AND OLD.codice_istanza IS NOT NULL
        AND NEW.codice_istanza IS DISTINCT FROM OLD.codice_istanza
      THEN
        
        PERFORM script.fn_log_and_raise_error(
          'database',
          TG_NAME,
          'E_COLONNA_NON_MODIFICABILE',
          jsonb_build_object('column','codice_istanza','id',OLD.id),
          NULL::uuid,
          'codice_istanza'
        );
      END IF;
      RETURN NEW;
    END;
    $function$
```
---
{% include-markdown "signature-core.md" %}
