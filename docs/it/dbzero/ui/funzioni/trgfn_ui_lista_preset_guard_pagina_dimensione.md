# ⚙️ Funzione `trgfn_ui_lista_preset_guard_pagina_dimensione`

```sql
CREATE FUNCTION trgfn_ui_lista_preset_guard_pagina_dimensione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_preset_guard_pagina_dimensione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la misura «righe per pagina» di un preset e' del catalogo.
BEGIN
    PERFORM ui.fn_guard_misura_pagina(to_jsonb(NEW.pagina_dimensione));
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_lista_preset_guard_pagina_dimensione()
IS 'Guard di ui.lista_preset: pagina_dimensione deve stare nel catalogo ui.misure_pagina (NULL = il default). Chiede a ui.fn_guard_misura_pagina, che rifiuta con E_UI_MISURA_PAGINA_NON_AMMESSA invece del 23503 della FK (che resta come rete). Il trigger nasce in 90_end/20260930-12, dopo il seed dei preset. Brief: brief-db-misure-pagina-catalogo §2-3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
