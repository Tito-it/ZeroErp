{% include-markdown "it/dbzero/config/manual/trgfn_toponomastica_protect_update.md" %}
# ⚙️ Funzione `trgfn_toponomastica_protect_update`

```sql
CREATE FUNCTION trgfn_toponomastica_protect_update()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_toponomastica_protect_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Consenti aggiornamenti in manutenzione esplicita
  IF current_setting('zeroerp.maintenance_toponomastica', true) = 'on' THEN
    RETURN NEW;
  END IF;

  -- Se il record non e' usato in config.stradario_generale, lascio passare
  IF NOT EXISTS (
    SELECT 1
      FROM config.stradario_generale
     WHERE toponomastica_id = OLD.id
  ) THEN
    RETURN NEW;
  END IF;

  -- Se siamo qui, il record e' in uso: controllo ciascuna colonna
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
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_toponomastica_protect_update()
IS 'Trigger function per proteggere aggiornamenti non autorizzati su config.toponomastica.
  Operazioni di manutenzione possono essere abilitate tramite la GUC ''zeroerp.maintenance_toponomastica''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
