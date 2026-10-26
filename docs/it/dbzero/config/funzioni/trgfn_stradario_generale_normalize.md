{% include-markdown "it/dbzero/config/manual/trgfn_stradario_generale_normalize.md" %}
# ⚙️ Funzione `trgfn_stradario_generale_normalize`

```sql
CREATE FUNCTION trgfn_stradario_generale_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_stradario_generale_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE v_topo text;
BEGIN
  
  SELECT descrizione INTO v_topo
    FROM config.toponomastica
   WHERE id = NEW.toponomastica_id;

  NEW.indirizzo_normalizzato := script.fn_norm_via(v_topo, NEW.descrizione);
  RETURN NEW;
END$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
