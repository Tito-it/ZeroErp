{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_dettaglio_protect_update.md" %}
# ⚙️ Funzione `trgfn_indirizzi_dettaglio_protect_update`

```sql
CREATE FUNCTION trgfn_indirizzi_dettaglio_protect_update()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_protect_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Consenti aggiornamenti in manutenzione esplicita
  IF current_setting('zeroerp.maintenance_indirizzi_dettaglio', true) = 'on' THEN
    RETURN NEW;
  END IF;

  -- Blocca cambio stradario_id se non in manutenzione
  IF NEW.stradario_id IS DISTINCT FROM OLD.stradario_id THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','stradario_id','id',OLD.id),
      NULL::uuid,
      'stradario_id'
    );
  END IF;

  RETURN NEW;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
