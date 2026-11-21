{% include-markdown "it/dbzero/ui/manual/trgfn_misure_pagina_ritira_dalle_preferenze.md" %}
# ⚙️ Funzione `trgfn_misure_pagina_ritira_dalle_preferenze`

```sql
CREATE FUNCTION trgfn_misure_pagina_ritira_dalle_preferenze()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_misure_pagina_ritira_dalle_preferenze()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una misura tolta dal catalogo esce dalle preferenze di
--   lista che la citano (la chiave pagina_dimensione); il resto
--   della configurazione resta.
-- Montaggio: AFTER DELETE FOR EACH ROW su ui.misure_pagina.
DECLARE
    v_misura ui.misure_pagina.misura%TYPE;
BEGIN
    IF TG_RELID <> 'ui.misure_pagina'::regclass OR TG_WHEN <> 'AFTER'
       OR TG_LEVEL <> 'ROW' OR TG_OP <> 'DELETE' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'dettaglio', 'atteso AFTER DELETE FOR EACH ROW su ui.misure_pagina'),
            NULL::uuid,
            format('%s: atteso AFTER DELETE FOR EACH ROW su ui.misure_pagina', TG_NAME));
    END IF;

    v_misura := OLD.misura;

    UPDATE ui.lista_preferenza_utente pu
       SET configurazione = pu.configurazione - 'pagina_dimensione'
     WHERE ui.fn_intero_da_jsonb(pu.configurazione -> 'pagina_dimensione') = v_misura;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_misure_pagina_ritira_dalle_preferenze()
IS 'Sul catalogo ui.misure_pagina, AFTER DELETE FOR EACH ROW: la misura ritirata esce dalle preferenze di lista che la citano (la chiave pagina_dimensione di ui.lista_preferenza_utente.configurazione, letta con ui.fn_intero_da_jsonb); il resto della configurazione resta, e l''utente torna allo standard. La riscrittura passa dai trigger della preferenza: il guard di forma giudica ciò che resta. Montata altrove: E_TRIGGER_ARGOMENTI_INVALIDI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
