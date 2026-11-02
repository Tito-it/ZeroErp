{% include-markdown "it/dbzero/script/manual/fn_available_actions_inventario.md" %}
# ⚙️ Funzione `fn_available_actions_inventario`

```sql
CREATE FUNCTION fn_available_actions_inventario(p_inventario_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_inventario(p_inventario_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la capability di un inventario per il detail API. Involucro:
--   la regola sta in script.fn_available_actions_documento_interno, una
--   sola per le due famiglie (D-L2-h). Esiste perche' il backend chiama
--   per ENTITA', come negli altri otto domini.
BEGIN
    RETURN script.fn_available_actions_documento_interno('INVENTARIO', p_inventario_id);
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_inventario(p_inventario_id bigint)
IS 'Capability di un inventario di magazzino per il detail API: involucro di script.fn_available_actions_documento_interno(''INVENTARIO'', id), dove sta la regola — una sola per le tre famiglie di documenti interni. Esiste perche'' il backend chiama la capability per entita''. NULL se l''inventario non si legge.';
```

</div>

---
{% include-markdown "signature-core.md" %}
