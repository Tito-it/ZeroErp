{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_guard_ripetibilita.md" %}
# ⚙️ Funzione `trgfn_flussi_guard_ripetibilita`

```sql
CREATE FUNCTION trgfn_flussi_guard_ripetibilita()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_ripetibilita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Wrapper trigger per guard ripetibilita' (D3).
  --   Solo per flussi template-based (template_flusso_id
  --   NOT NULL): i flussi manuali bypassano, come per i
  --   prerequisiti.
  -- =========================================================

  IF NEW.template_flusso_id IS NOT NULL THEN
    PERFORM pratiche.fn_guard_ripetibilita_flusso(
      NEW.pratica_id,
      NEW.template_flusso_id
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_guard_ripetibilita()
IS 'BEFORE INSERT su flussi: verifica la regola di ripetibilita'' del template per flussi template-based.';
```

</div>

---
{% include-markdown "signature-core.md" %}
