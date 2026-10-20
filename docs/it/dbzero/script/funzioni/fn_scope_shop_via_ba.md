# ⚙️ Funzione `fn_scope_shop_via_ba`

```sql
CREATE FUNCTION fn_scope_shop_via_ba(p_identita_id bigint, p_billing_account_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_shop_via_ba(p_identita_id bigint, p_billing_account_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- ⛔ DUE condizioni, non una: la testata pretende anche
    --   `canale_origine = 'SHOP'`. Un satellite che chiedesse la
    --   sola proprieta' sarebbe PIU' PERMISSIVO della propria
    --   testata, che e' l'invariante che questa slice difende.
    -- ⭐ Gemella di script.fn_scope_shop_via_ordine, che dal
    --   passo 2 fa la stessa cosa risalendo all'ordine.
    -- ⚠️ Billing account inesistente -> nessuna riga -> false:
    --   fail-closed, come tutta la famiglia.
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.billing_account ba
         WHERE ba.id             = p_billing_account_id
           AND ba.canale_origine = 'SHOP'::config.canale_origine
           AND script.fn_scope_ba_ownership(p_identita_id, ba.id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_shop_via_ba(p_identita_id bigint, p_billing_account_id bigint)
IS 'Adattatore della veste SHOP_CUSTOMER per i satelliti di anagrafiche.billing_account (a partire da anagrafiche.clienti): risale da billing_account_id (NOT NULL) e pretende ENTRAMBE le condizioni che la testata concede allo shop — canale_origine = SHOP e proprieta'' dell''identita'' — perche'' la prima si legge da una colonna che sta sul billing account e che i satelliti non hanno. ⛔ Una policy figlia che chiedesse la sola proprieta'' sarebbe piu'' permissiva della propria testata. ⭐ Gemella di script.fn_scope_shop_via_ordine. STABLE e NON security definer: leggendo sotto RLS vede il billing account gia'' filtrato dalla policy della testata, ed e'' voluto — il satellite non rispecchia il perimetro, ci passa attraverso. Brief: brief-db-perimetro-emittente-righe-documento.md §11.17';
```

</div>

---
{% include-markdown "signature-core.md" %}
