{% include-markdown "it/dbzero/script/manual/fn_scope_ba_ownership.md" %}
# ⚙️ Funzione `fn_scope_ba_ownership`

```sql
CREATE FUNCTION fn_scope_ba_ownership(p_identita_id bigint, p_billing_account_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ba_ownership(p_identita_id bigint, p_billing_account_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Il BA appartiene all'identita se condividono il
    -- soggetto_ruolo (cliente). EXISTS -> short-circuit.
    -- Defense-in-depth: id.attivo = true, coerente con le
    -- altre fn_scope_*; un'identita inattiva non deve mai
    -- passare il filtro scope (fail-closed).
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
          JOIN anagrafiche.billing_account  ba
            ON ba.soggetto_ruolo_id = id.soggetto_ruolo_id
         WHERE id.id     = p_identita_id
           AND id.attivo = true
           AND ba.id     = p_billing_account_id
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ba_ownership(p_identita_id bigint, p_billing_account_id bigint)
IS 'Scope policy BA_OWNERSHIP: ritorna true se il billing_account appartiene all''identita (via soggetto_ruolo comune). Usata sia da CLIENTE_PORTALE sia da SHOP_CUSTOMER (stesso ruolo anagrafico CL). STABLE, inlineable.';
```

---
{% include-markdown "signature-core.md" %}
