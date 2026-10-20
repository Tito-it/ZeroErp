{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_guard_prerequisiti.md" %}
# ⚙️ Funzione `trgfn_flussi_guard_prerequisiti`

```sql
CREATE FUNCTION trgfn_flussi_guard_prerequisiti()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_prerequisiti()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Wrapper trigger per guard prerequisiti.
  --   Solo per flussi template-based (template_flusso_id NOT NULL).
  --   I flussi manuali (NULL) bypassano il controllo.
  -- =========================================================

  IF NEW.template_flusso_id IS NOT NULL THEN
    PERFORM pratiche.fn_guard_prerequisiti_flusso(
      NEW.pratica_id,
      NEW.template_flusso_id
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_guard_prerequisiti()
IS 'BEFORE INSERT su flussi: verifica prerequisiti per flussi template-based.';
```

</div>

---
{% include-markdown "signature-core.md" %}
