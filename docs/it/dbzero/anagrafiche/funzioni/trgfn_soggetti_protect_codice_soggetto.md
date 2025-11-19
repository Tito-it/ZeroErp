{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_protect_codice_soggetto.md" %}
# ⚙️ Funzione `trgfn_soggetti_protect_codice_soggetto`

```sql
CREATE FUNCTION trgfn_soggetti_protect_codice_soggetto()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_protect_codice_soggetto()
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
          jsonb_build_object('column','codice','id',OLD.id),
          NULL::uuid,
          'codice soggetto'
        );
      END IF;
      RETURN NEW;
    END;
    $function$
```

---
{% include-markdown "signature-core.md" %}
