# ⚙️ Funzione `trgfn_pdp_protect_cols`

```sql
CREATE FUNCTION trgfn_pdp_protect_cols()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_pdp_protect_cols()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    IF OLD.pdp IS NOT NULL
       AND NEW.pdp IS DISTINCT FROM OLD.pdp THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
        jsonb_build_object('column','pdp','id',OLD.id),
        NULL::uuid, 'pdp'
      );
    END IF;

    IF OLD.indirizzo_dettaglio_id IS NOT NULL
       AND NEW.indirizzo_dettaglio_id IS DISTINCT FROM OLD.indirizzo_dettaglio_id THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
        jsonb_build_object('column','indirizzo_dettaglio_id','id',OLD.id),
        NULL::uuid, 'indirizzo_dettaglio_id'
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
```
---
{% include-markdown "signature-core.md" %}
