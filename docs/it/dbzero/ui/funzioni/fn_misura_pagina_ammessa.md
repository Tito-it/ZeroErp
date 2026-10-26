{% include-markdown "it/dbzero/ui/manual/fn_misura_pagina_ammessa.md" %}
# ⚙️ Funzione `fn_misura_pagina_ammessa`

```sql
CREATE FUNCTION fn_misura_pagina_ammessa(p_misura integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_misura_pagina_ammessa(p_misura integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se una misura «righe per pagina» e' nel catalogo.
    SELECT EXISTS (SELECT 1 FROM ui.misure_pagina m WHERE m.misura = p_misura);
$function$

COMMENT ON FUNCTION ui.fn_misura_pagina_ammessa(p_misura integer)
IS 'La misura «righe per pagina» e'' nel catalogo ui.misure_pagina? NULL -> false. La chiedono ui.fn_guard_misura_pagina (per rifiutare una scrittura) e ui.fn_resolve_lista_config (per non rispondere una misura che il paginatore non offre). STABLE, INVOKER, inlineabile. Brief: brief-db-misure-pagina-catalogo §2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
