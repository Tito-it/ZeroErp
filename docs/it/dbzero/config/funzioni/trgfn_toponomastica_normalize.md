{% include-markdown "it/dbzero/config/manual/trgfn_toponomastica_normalize.md" %}
# ⚙️ Funzione `trgfn_toponomastica_normalize`

```sql
CREATE FUNCTION trgfn_toponomastica_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_toponomastica_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Default stato_id se mancante
  IF NEW.stato_id IS NULL THEN
    NEW.stato_id := script.fn_get_default_by_param(
      'config',
      'stati',
      'codice_iso3',
      'state_code_iso3',
      TG_NAME
    )::integer;
  END IF;

  -- Se ancora NULL, errore
  IF NEW.stato_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_STATO_SCONOSCIUTO',
      jsonb_build_object('table','config.toponomastica'),
      NULL::uuid,
      'stato_id'
    );
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
