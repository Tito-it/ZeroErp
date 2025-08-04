# ⚙️ Funzione `trgfn_upd_soggetti_protect_codice_soggetto`

```sql
CREATE FUNCTION trgfn_upd_soggetti_protect_codice_soggetto()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_upd_soggetti_protect_codice_soggetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP = 'UPDATE'
        AND OLD.codice_soggetto IS NOT NULL
        AND NEW.codice_soggetto IS DISTINCT FROM OLD.codice_soggetto
      THEN
        
        PERFORM script.fn_log_and_raise_error(
          'database',
          TG_NAME,
          'E_COLONNA_NON_MODIFICABILE',
          jsonb_build_object('column','codice_soggetto','id',OLD.id),
          NULL::uuid,
          'codice_soggetto'
        );
      END IF;
      RETURN NEW;
    END;
    $function$
```
---
{% include-markdown "signature-core.md" %}
