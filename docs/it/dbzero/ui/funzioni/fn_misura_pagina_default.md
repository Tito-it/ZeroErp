{% include-markdown "it/dbzero/ui/manual/fn_misura_pagina_default.md" %}
# ⚙️ Funzione `fn_misura_pagina_default`

```sql
CREATE FUNCTION fn_misura_pagina_default(p_uso character varying)
```

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
    SELECT m.misura
      INTO v_misura
      FROM ui.misure_pagina m
     WHERE m.uso_default = p_uso;

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
IS 'La misura «righe per pagina» di default per un uso (COMPATTA: drawer e dialog; PAGINA: pagine e ripiego del resolver delle liste), dal catalogo ui.misure_pagina. Mai NULL: se il catalogo non ha quel default (o l''uso e'' fuori vocabolario) solleva E_UI_MISURA_PAGINA_DEFAULT_MANCANTE (TECNICO). La chiedono ui.fn_resolve_lista_config e ui.fn_get_misure_pagina. STABLE, INVOKER. Brief: brief-db-misure-pagina-catalogo §2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
