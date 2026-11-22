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
    -- Scopo: le misure «righe per pagina» ammesse, in ordine, e il
    --   default di ogni uso: la lettura unica per l'applicazione.
    -- Gli usi dall'enum, non scritti qui: un uso nuovo ha il suo default
    --   senza toccare la funzione.
    SELECT jsonb_build_object(
               'misure',           (SELECT COALESCE(jsonb_agg(m.misura ORDER BY m.misura), jsonb_build_array())
                                      FROM ui.misure_pagina m),
               'default_per_uso',  (SELECT jsonb_object_agg(u.uso::text, ui.fn_misura_pagina_default(u.uso::text))
                                      FROM unnest(enum_range(NULL::ui.uso_misura_pagina)) AS u(uso)),
               -- Le due chiavi di prima, finche' il backend non legge default_per_uso.
               'default_compatta', ui.fn_misura_pagina_default('COMPATTA'),
               'default_pagina',   ui.fn_misura_pagina_default('PAGINA'));
$function$

COMMENT ON FUNCTION ui.fn_get_misure_pagina()
IS 'Le misure «righe per pagina» per tutta l''applicazione, in una lettura: {"misure": [...] in ordine crescente, "default_per_uso": {uso: misura} per ogni valore di ui.uso_misura_pagina (COMPATTA: drawer e dialog; PAGINA: pagine)}. Gli usi vengono dall''enum: un uso nuovo compare senza toccare la funzione. Dal catalogo ui.misure_pagina; i default da ui.fn_misura_pagina_default, che solleva E_UI_MISURA_PAGINA_DEFAULT_MANCANTE se ne manca uno: mai NULL. Le chiavi default_compatta e default_pagina ripetono i due default di default_per_uso e restano finché il backend non legge quella. La serve il backend a ogni paginatore. STABLE, INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
