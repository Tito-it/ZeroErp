{% include-markdown "it/dbzero/config/manual/trgfn_stradario_generale_protect_update.md" %}
# ⚙️ Funzione `trgfn_stradario_generale_protect_update`

```sql
CREATE FUNCTION trgfn_stradario_generale_protect_update()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_stradario_generale_protect_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Se il record non è usato in config.stradario, lascio passare
  IF NOT EXISTS (
    SELECT 1
      FROM config.stradario
     WHERE stradario_generale_id = OLD.id
  ) THEN
    RETURN NEW;
  END IF;

  -- Se siamo qui, il record è in uso: controllo ciascuna colonna
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

  IF OLD.descrizione_breve IS DISTINCT FROM NEW.descrizione_breve THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','descrizione_breve','id',OLD.id),
       NULL::uuid,
      'descrizione_breve'
    );
  END IF;

  IF OLD.toponomastica_id IS DISTINCT FROM NEW.toponomastica_id THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','toponomastica_id','id',OLD.id),
       NULL::uuid,
      'toponomastica_id'
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_stradario_generale_protect_update()
IS 'Blocca UPDATE di descrizione, descrizione_breve, toponomastica_id se esistono righe in config.stradario, indicando la colonna modificata';
```

</div>

---
{% include-markdown "signature-core.md" %}
