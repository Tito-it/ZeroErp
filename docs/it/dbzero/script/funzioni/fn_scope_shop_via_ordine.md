# ⚙️ Funzione `fn_scope_shop_via_ordine`

```sql
CREATE FUNCTION fn_scope_shop_via_ordine(p_identita_id bigint, p_ordine_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_shop_via_ordine(p_identita_id bigint, p_ordine_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- ⛔ DUE condizioni, non una: la testata pretende anche
    --   `canale_origine = 'SHOP'`. Un satellite che chiedesse la
    --   sola proprieta' sarebbe PIU' PERMISSIVO della propria
    --   testata, che e' l'invariante che questa slice difende.
    SELECT EXISTS (
        SELECT 1
          FROM vendite.ordini o
         WHERE o.id = p_ordine_id
           AND o.canale_origine = 'SHOP'::config.canale_origine
           AND script.fn_scope_cliente_ownership(
                   p_identita_id, o.soggetto_ruolo_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_shop_via_ordine(p_identita_id bigint, p_ordine_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.ordini, veste SHOP_CUSTOMER: proprieta'' del cliente PIU'' `canale_origine = SHOP`. ⛔ Le condizioni sono due perche'' due ne pretende la testata: un satellite che chiedesse la sola proprieta'' sarebbe piu'' permissivo del documento a cui appartiene.';
```

</div>

---
{% include-markdown "signature-core.md" %}
