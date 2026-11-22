{% include-markdown "it/dbzero/ui/manual/trgfn_ui_lista_preset_guard_pagina_dimensione.md" %}
# ⚙️ Funzione `trgfn_ui_lista_preset_guard_pagina_dimensione`

```sql
CREATE FUNCTION trgfn_ui_lista_preset_guard_pagina_dimensione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
IS 'Guard di ui.lista_preset: pagina_dimensione è NULL (lo standard) o una misura del catalogo ui.misure_pagina. Chiede a ui.fn_guard_misura_pagina, che rifiuta con E_UI_MISURA_PAGINA_NON_AMMESSA invece dell''errore della FK fk_lista_preset_misure_pagina, che resta come rete. Il trigger è trg_ui_lista_preset_a10_guard_pagina_ins_upd.';
```

</div>

---
{% include-markdown "signature-core.md" %}
