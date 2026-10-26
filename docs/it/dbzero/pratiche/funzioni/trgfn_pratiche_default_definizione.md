{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_default_definizione.md" %}
# ⚙️ Funzione `trgfn_pratiche_default_definizione`

```sql
CREATE FUNCTION trgfn_pratiche_default_definizione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_default_definizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: PIN dell'edizione di workflow alla nascita della
--        pratica. Risolve per (tipo, emittente): l'edizione
--        dell'emittente vince sul preset. Il pin e' per sempre
--        (immutabilita' enforce-ata dal guard di Fase 1).
BEGIN
  IF NEW.definizione_id IS NULL THEN
    NEW.definizione_id := pratiche.fn_risolvi_definizione(
      NEW.tipo_prestazione_id,
      NEW.emittente_fiscale_id
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_default_definizione()
IS 'BEFORE INSERT su pratiche.pratiche: auto-pin di definizione_id via fn_risolvi_definizione(tipo, emittente) quando NULL — edizione PUBBLICATA dell''emittente > preset. Il BE create_pratica non deve passare la colonna.';
```

</div>

---
{% include-markdown "signature-core.md" %}
