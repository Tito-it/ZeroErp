{% include-markdown "it/dbzero/script/manual/fn_scope_cliente_ownership.md" %}
# ⚙️ Funzione `fn_scope_cliente_ownership`

```sql
CREATE FUNCTION fn_scope_cliente_ownership(p_identita_id bigint, p_cliente_sr_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_cliente_ownership(p_identita_id bigint, p_cliente_sr_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Match diretto: il target soggetto_ruolo e' quello
    -- dell'identita, e l'identita e' in veste CLIENTE_PORTALE
    -- oppure SHOP_CUSTOMER (i due ruoli applicativi che
    -- condividono il ruolo anagrafico CL). Evita false positive
    -- su altre identita collegate allo stesso SR con veste
    -- diversa (es. FORNITORE_PORTALE su SR misto CL/FO).
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
         WHERE id.id                = p_identita_id
           AND id.soggetto_ruolo_id = p_cliente_sr_id
           AND id.ruolo_applicativo IN ('CLIENTE_PORTALE', 'SHOP_CUSTOMER')
           AND id.attivo            = true
    );
$function$

COMMENT ON FUNCTION script.fn_scope_cliente_ownership(p_identita_id bigint, p_cliente_sr_id bigint)
IS 'Scope policy CLIENTE_OWNERSHIP: ritorna true se il soggetto_ruolo cliente target coincide con il soggetto_ruolo dell''identita e l''identita e'' in veste CLIENTE_PORTALE o SHOP_CUSTOMER attiva. STABLE, inlineable.';
```

---
{% include-markdown "signature-core.md" %}
