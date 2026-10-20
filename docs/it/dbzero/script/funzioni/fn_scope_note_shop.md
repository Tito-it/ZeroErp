# ⚙️ Funzione `fn_scope_note_shop`

```sql
CREATE FUNCTION fn_scope_note_shop(p_identita_id bigint, p_target_tipo character varying, p_target_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_note_shop(p_identita_id bigint, p_target_tipo character varying, p_target_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- ⛔ `fn_scope_shop_via_ordine` porta DUE condizioni —
    --   proprieta' e `canale_origine = 'SHOP'` — perche' due ne
    --   pretende la testata. Il padre non puo' farsi bastare la
    --   proprieta': sarebbe piu' permissivo della partizione.
    SELECT CASE p_target_tipo
        WHEN 'ORDINE' THEN script.fn_scope_shop_via_ordine(p_identita_id, p_target_id)
        ELSE false
    END;
$function$

COMMENT ON FUNCTION script.fn_scope_note_shop(p_identita_id bigint, p_target_tipo character varying, p_target_id bigint)
IS 'Smistatore per il padre vendite.note, veste SHOP_CUSTOMER. Solo ORDINE, e delegando a fn_scope_shop_via_ordine, che pretende proprieta'' E canale_origine = SHOP: due condizioni, come la testata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
