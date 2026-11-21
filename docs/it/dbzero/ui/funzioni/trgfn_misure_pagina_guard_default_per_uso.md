{% include-markdown "it/dbzero/ui/manual/trgfn_misure_pagina_guard_default_per_uso.md" %}
# ⚙️ Funzione `trgfn_misure_pagina_guard_default_per_uso`

```sql
CREATE FUNCTION trgfn_misure_pagina_guard_default_per_uso()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_misure_pagina_guard_default_per_uso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: a fine transazione il catalogo delle misure ha un default
--   per ogni uso. Lo chiede a ui.fn_misura_pagina_default, che
--   solleva E_UI_MISURA_PAGINA_DEFAULT_MANCANTE se manca.
-- Montaggio: CONSTRAINT TRIGGER AFTER INSERT OR UPDATE OF uso_default
--   OR DELETE, DEFERRABLE INITIALLY DEFERRED, FOR EACH ROW.
DECLARE
    v_uso ui.misure_pagina.uso_default%TYPE;
BEGIN
    IF TG_RELID <> 'ui.misure_pagina'::regclass OR TG_WHEN <> 'AFTER'
       OR TG_LEVEL <> 'ROW' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'dettaglio', 'atteso AFTER … FOR EACH ROW su ui.misure_pagina'),
            NULL::uuid,
            format('%s: atteso AFTER … FOR EACH ROW su ui.misure_pagina', TG_NAME));
    END IF;

    FOREACH v_uso IN ARRAY enum_range(NULL::ui.uso_misura_pagina) LOOP
        PERFORM ui.fn_misura_pagina_default(v_uso::text);
    END LOOP;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_misure_pagina_guard_default_per_uso()
IS 'Sul catalogo ui.misure_pagina: a fine transazione ogni valore di ui.uso_misura_pagina ha la sua misura di default. Lo chiede a ui.fn_misura_pagina_default, che solleva E_UI_MISURA_PAGINA_DEFAULT_MANCANTE (TECNICO) se manca: togliere un default senza spostarlo è rifiutato al commit, spostarlo nella stessa transazione passa. CONSTRAINT TRIGGER AFTER INSERT OR UPDATE OF uso_default OR DELETE, DEFERRABLE INITIALLY DEFERRED, FOR EACH ROW: con SET CONSTRAINTS IMMEDIATE scatta a fine istruzione. Montata altrove: E_TRIGGER_ARGOMENTI_INVALIDI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
