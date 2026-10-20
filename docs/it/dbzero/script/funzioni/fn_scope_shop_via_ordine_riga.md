# ⚙️ Funzione `fn_scope_shop_via_ordine_riga`

```sql
CREATE FUNCTION fn_scope_shop_via_ordine_riga(p_identita_id bigint, p_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_shop_via_ordine_riga(p_identita_id bigint, p_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    SELECT script.fn_scope_shop_via_ordine(
        p_identita_id,
        (SELECT r.ordine_id
           FROM vendite.ordini_righe r WHERE r.id = p_riga_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_shop_via_ordine_riga(p_identita_id bigint, p_riga_id bigint)
IS 'Come fn_scope_shop_via_ordine ma a partire da una riga d''ordine.';
```

</div>

---
{% include-markdown "signature-core.md" %}
