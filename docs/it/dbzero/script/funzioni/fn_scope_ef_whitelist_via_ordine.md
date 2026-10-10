# ⚙️ Funzione `fn_scope_ef_whitelist_via_ordine`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_ordine(p_auth_user_id integer, p_ordine_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_ordine(p_auth_user_id integer, p_ordine_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- ⚠️ Ordine inesistente -> emittente NULL -> la canonica
    --   risponde false a whitelist valorizzata: fail-closed.
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT o.emittente_fiscale_id
           FROM vendite.ordini o WHERE o.id = p_ordine_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_ordine(p_auth_user_id integer, p_ordine_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.ordini, veste OPERATORE: risale dalla chiave della testata a `emittente_fiscale_id` e delega a script.fn_scope_ef_whitelist. STABLE e NON security definer, come gli altri fn_scope_*. Ordine inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
