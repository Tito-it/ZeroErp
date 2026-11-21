{% include-markdown "it/dbzero/ui/manual/fn_guard_misura_pagina.md" %}
# ⚙️ Funzione `fn_guard_misura_pagina`

```sql
CREATE FUNCTION fn_guard_misura_pagina(p_valore jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_guard_misura_pagina(p_valore jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare un valore «righe per pagina» che non e' una misura
--   del catalogo. NULL e null jsonb passano: sono il default.
DECLARE
    -- Esplicito: il testo del valore com'e' scritto, per la frase.
    v_testo  text := p_valore #>> '{}';
    -- La misura, se il valore e' un intero (dal BB); altrimenti NULL.
    v_misura ui.misure_pagina.misura%TYPE := ui.fn_intero_da_jsonb(p_valore);
BEGIN
    IF p_valore IS NULL OR jsonb_typeof(p_valore) = 'null' THEN
        RETURN;
    END IF;

    IF v_misura IS NULL OR NOT ui.fn_misura_pagina_ammessa(v_misura) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'ui.fn_guard_misura_pagina', 'E_UI_MISURA_PAGINA_NON_AMMESSA',
            jsonb_build_object('campo', 'pagina_dimensione', 'valore', p_valore),
            NULL::uuid,
            VARIADIC ARRAY[v_testo,
                           (SELECT string_agg(m.misura::text, ', ' ORDER BY m.misura)
                              FROM ui.misure_pagina m)]);
    END IF;
END;
$function$

COMMENT ON FUNCTION ui.fn_guard_misura_pagina(p_valore jsonb)
IS 'Rifiuta un valore «righe per pagina» che non è un numero intero del catalogo ui.misure_pagina: E_UI_MISURA_PAGINA_NON_AMMESSA (DATO_ERRATO), con il valore e l''elenco delle misure ammesse nella frase, campo = pagina_dimensione. NULL e null jsonb passano (sono il default). Riceve il valore com''è scritto (jsonb): nella preferenza utente può non essere un numero, e il rifiuto parte da un punto solo; il preset gli passa to_jsonb(pagina_dimensione). Che il valore sia un intero lo dice ui.fn_intero_da_jsonb, la stessa domanda dei resolver: la stringa "25" è rifiutata. Lo chiamano il trigger della misura di ui.lista_preset (dove la FK resta come rete) e il trigger di forma delle preferenze (ui.trgfn_preferenza_guard_forma). INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
