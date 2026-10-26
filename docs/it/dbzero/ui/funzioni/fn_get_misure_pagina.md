{% include-markdown "it/dbzero/ui/manual/fn_get_misure_pagina.md" %}
# ⚙️ Funzione `fn_get_misure_pagina`

```sql
CREATE FUNCTION fn_get_misure_pagina()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_get_misure_pagina()
 RETURNS jsonb
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: le misure «righe per pagina» ammesse, in ordine, e i due
    --   default: la lettura unica per l'applicazione.
    SELECT jsonb_build_object(
               'misure',           (SELECT COALESCE(jsonb_agg(m.misura ORDER BY m.misura), jsonb_build_array())
                                      FROM ui.misure_pagina m),
               'default_compatta', ui.fn_misura_pagina_default('COMPATTA'),
               'default_pagina',   ui.fn_misura_pagina_default('PAGINA'));
$function$

COMMENT ON FUNCTION ui.fn_get_misure_pagina()
IS 'Le misure «righe per pagina» per TUTTA l''applicazione, in una lettura: {"misure": [...] in ordine crescente, "default_compatta": drawer e dialog, "default_pagina": pagine}. Dal catalogo ui.misure_pagina; i default da ui.fn_misura_pagina_default (se ne manca uno solleva, mai NULL). La serve il backend a ogni paginatore: sostituisce le costanti PAGINATION del frontend (decisioni di Tid del 2026-09-29). STABLE, INVOKER. Brief: brief-db-misure-pagina-catalogo §2, §6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
