{% include-markdown "it/dbzero/script/manual/fn_available_actions_rettifica.md" %}
# ⚙️ Funzione `fn_available_actions_rettifica`

```sql
CREATE FUNCTION fn_available_actions_rettifica(p_rettifica_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_rettifica(p_rettifica_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la capability di una rettifica per il detail API. Involucro:
--   vedi fn_available_actions_inventario.
BEGIN
    RETURN script.fn_available_actions_documento_interno('RETTIFICA', p_rettifica_id);
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_rettifica(p_rettifica_id bigint)
IS 'Capability di una rettifica di magazzino per il detail API: involucro di script.fn_available_actions_documento_interno(''RETTIFICA'', id), dove sta la regola — una sola per le due famiglie di documenti interni (D-L2-h). NULL se la rettifica non si legge. Brief: brief-db-magazzino-lotto-2-bis-be-fe R-1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
