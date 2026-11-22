{% include-markdown "it/dbzero/ui/manual/fn_misura_pagina_default.md" %}
# ⚙️ Funzione `fn_misura_pagina_default`

```sql
CREATE FUNCTION fn_misura_pagina_default(p_uso character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_misura_pagina_default(p_uso character varying)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la misura «righe per pagina» di default per un uso.
--   Mai NULL: un default che manca e' un catalogo rotto.
DECLARE
    v_misura ui.misure_pagina.misura%TYPE;
BEGIN
    -- Sul testo dell'enum: un uso fuori vocabolario non trova la riga.
    SELECT m.misura
      INTO v_misura
      FROM ui.misure_pagina m
     WHERE m.uso_default::text = p_uso;

    IF v_misura IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'ui.fn_misura_pagina_default', 'E_UI_MISURA_PAGINA_DEFAULT_MANCANTE',
            jsonb_build_object('uso_default', p_uso),
            NULL::uuid,
            VARIADIC ARRAY[COALESCE(p_uso, 'NULL')]);
    END IF;

    RETURN v_misura;
END;
$function$

COMMENT ON FUNCTION ui.fn_misura_pagina_default(p_uso character varying)
IS 'La misura «righe per pagina» di default per un uso (ui.uso_misura_pagina: COMPATTA, drawer e dialog; PAGINA, pagine), dal catalogo ui.misure_pagina. Mai NULL: se il catalogo non ha quel default, o l''uso è fuori vocabolario, solleva E_UI_MISURA_PAGINA_DEFAULT_MANCANTE (TECNICO). La chiedono ui.fn_get_misure_pagina (il default di ogni uso), ui.fn_misura_pagina_risolta (lo standard di una lista senza un preset nel catalogo) e il trigger differito del catalogo, che a fine transazione pretende un default per ogni uso. STABLE, INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
