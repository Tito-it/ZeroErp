{% include-markdown "it/dbzero/ui/manual/fn_misura_pagina_risolta.md" %}
# ⚙️ Funzione `fn_misura_pagina_risolta`

```sql
CREATE FUNCTION fn_misura_pagina_risolta(p_preferenza integer, p_preset integer, p_uso ui.uso_misura_pagina)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_misura_pagina_risolta(p_preferenza integer, p_preset integer, p_uso ui.uso_misura_pagina)
 RETURNS TABLE(misura integer, standard integer, origine text)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN s.preferenza_ok THEN fn_misura_pagina_risolta.p_preferenza
             ELSE s.standard
         END AS standard,
     s.standard,
         CASE
             WHEN s.preferenza_ok THEN 'preferenza'::text
             WHEN s.preset_ok THEN 'preset'::text
             ELSE 'catalogo'::text
         END AS "case"
    FROM ( SELECT a.preferenza_ok,
             a.preset_ok,
                 CASE
                     WHEN a.preset_ok THEN fn_misura_pagina_risolta.p_preset
                     ELSE ui.fn_misura_pagina_default(((fn_misura_pagina_risolta.p_uso)::text)::character varying)
                 END AS standard
            FROM ( SELECT ui.fn_misura_pagina_ammessa(fn_misura_pagina_risolta.p_preferenza) AS preferenza_ok,
                     ui.fn_misura_pagina_ammessa(fn_misura_pagina_risolta.p_preset) AS preset_ok) a) s;
END

COMMENT ON FUNCTION ui.fn_misura_pagina_risolta(p_preferenza integer, p_preset integer, p_uso ui.uso_misura_pagina)
IS 'La misura «righe per pagina» di una lista, data la misura della preferenza (p_preferenza), quella del preset di base (p_preset) e l''uso della lista (p_uso, ui.lista_definizione.uso_misura). Una riga: misura, la misura che risponde; standard, quella che risponderebbe senza la preferenza; origine, da dove viene (''preferenza'', ''preset'' o ''catalogo''). Lo standard è la misura del preset se è nel catalogo ui.misure_pagina, altrimenti il default dell''uso (ui.fn_misura_pagina_default). Risponde la misura della preferenza se è nel catalogo, altrimenti lo standard: una misura uscita dal catalogo non è più una scelta. NULL vale «nessuna misura». Mai una misura NULL: senza il default dell''uso solleva E_UI_MISURA_PAGINA_DEFAULT_MANCANTE. La leggono ui.fn_resolve_lista_config e ui.fn_misura_lista. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
