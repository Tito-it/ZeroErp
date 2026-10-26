{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_istanze_dati_precontrattuali_protect_update.md" %}
# ⚙️ Funzione `trgfn_istanze_dati_precontrattuali_protect_update`

```sql
CREATE FUNCTION trgfn_istanze_dati_precontrattuali_protect_update()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF EXISTS (
    SELECT 1
      FROM vendite.contratti_utilities cu
     WHERE cu.istanza_dati_precontrattuali_id = OLD.id
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('table','anagrafiche.istanze_dati_precontrattuali','id',OLD.id),
      NULL::uuid,
      'record'
    );
  END IF;

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update()
IS 'Blocca UPDATE/DELETE su istanze_dati_precontrattuali se esistono snapshot in vendite.contratti_utilities.';
```

</div>

---
{% include-markdown "signature-core.md" %}
