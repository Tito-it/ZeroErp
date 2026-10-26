{% include-markdown "it/dbzero/pratiche/manual/trgfn_template_flussi_default_definizione.md" %}
# ⚙️ Funzione `trgfn_template_flussi_default_definizione`

```sql
CREATE FUNCTION trgfn_template_flussi_default_definizione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_template_flussi_default_definizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: default del re-parent — un template inserito senza
--        edizione appartiene al PRESET del suo tipo (realta'
--        pre-fork). Le edizioni specifiche si passano esplicite.
BEGIN
  IF NEW.definizione_id IS NULL THEN
    NEW.definizione_id := pratiche.fn_risolvi_definizione(NEW.tipo_prestazione_id, NULL);
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_template_flussi_default_definizione()
IS 'BEFORE INSERT su pratiche.template_flussi: se definizione_id e'' NULL lo risolve al preset PUBBLICATA del tipo (fn_risolvi_definizione). Mantiene invariati seed e fixture dopo il SET NOT NULL di Fase 0.';
```

</div>

---
{% include-markdown "signature-core.md" %}
