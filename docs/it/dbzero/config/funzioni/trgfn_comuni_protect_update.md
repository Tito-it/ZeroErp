{% include-markdown "it/dbzero/config/manual/trgfn_comuni_protect_update.md" %}
# ⚙️ Funzione `trgfn_comuni_protect_update`

```sql
CREATE FUNCTION trgfn_comuni_protect_update()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_comuni_protect_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Se il record non e' usato in config.stradario, lascio passare
  IF NOT EXISTS (
    SELECT 1
    FROM config.stradario
    WHERE comune_id = OLD.id
  ) THEN
    RETURN NEW;
  END IF;

  -- Se siamo qui, il record e' in uso: blocco modifiche ai campi chiave
  IF OLD.descrizione IS DISTINCT FROM NEW.descrizione THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','descrizione','id',OLD.id),
      NULL::uuid,
      'descrizione'
    );
  END IF;

  IF OLD.provincia_id IS DISTINCT FROM NEW.provincia_id THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','provincia_id','id',OLD.id),
      NULL::uuid,
      'provincia_id'
    );
  END IF;

  IF OLD.extra_country IS DISTINCT FROM NEW.extra_country THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','extra_country','id',OLD.id),
      NULL::uuid,
      'extra_country'
    );
  END IF;

  RETURN NEW;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
