{% include-markdown "it/dbzero/ui/manual/fn_guard_misura_pagina.md" %}
# ⚙️ Funzione `fn_guard_misura_pagina`

```sql
CREATE FUNCTION fn_guard_misura_pagina(p_valore jsonb)
```

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
    v_testo text := p_valore #>> '{}';
BEGIN
    IF p_valore IS NULL OR jsonb_typeof(p_valore) = 'null' THEN
        RETURN;
    END IF;

    -- ⚠️ CASE e non AND: il cast a integer di un valore non intero
    --    solleverebbe 22P02 invece del codice di catalogo. Fra parentesi:
    --    senza, PL/pgSQL chiude la condizione dell'IF al THEN del CASE.
    IF (CASE WHEN jsonb_typeof(p_valore) <> 'number'         THEN true
             WHEN v_testo !~ '^[0-9]{1,9}$'                  THEN true
             ELSE NOT ui.fn_misura_pagina_ammessa(v_testo::integer) END) THEN
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
IS 'Rifiuta un valore «righe per pagina» che non e'' un numero intero del catalogo ui.misure_pagina: E_UI_MISURA_PAGINA_NON_AMMESSA (DATO_ERRATO), con il valore e l''elenco delle misure ammesse nella frase, campo = pagina_dimensione. NULL e null jsonb passano (sono il default). Riceve il valore com''e'' scritto (jsonb): nella preferenza utente puo'' non essere un numero, e il rifiuto parte da un punto solo; il preset gli passa to_jsonb(pagina_dimensione). Lo chiamano i trigger di ui.lista_preset (dove la FK resta come rete) e di ui.lista_preferenza_utente. INVOKER. Brief: brief-db-misure-pagina-catalogo §2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
