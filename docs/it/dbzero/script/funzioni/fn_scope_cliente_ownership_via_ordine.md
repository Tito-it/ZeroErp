# ⚙️ Funzione `fn_scope_cliente_ownership_via_ordine`

```sql
CREATE FUNCTION fn_scope_cliente_ownership_via_ordine(p_identita_id bigint, p_ordine_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_cliente_ownership_via_ordine(p_identita_id bigint, p_ordine_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    SELECT script.fn_scope_cliente_ownership(
        p_identita_id,
        (SELECT o.soggetto_ruolo_id
           FROM vendite.ordini o WHERE o.id = p_ordine_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_cliente_ownership_via_ordine(p_identita_id bigint, p_ordine_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.ordini, veste CLIENTE_PORTALE: risale dalla testata a `soggetto_ruolo_id` e delega a script.fn_scope_cliente_ownership. ⚠️ Esiste perche'' i satelliti devono rispecchiare TUTTE le vesti della testata: con la sola veste operatore un cliente del portale smetterebbe di vedere le righe degli ordini che possiede.';
```

</div>

---
{% include-markdown "signature-core.md" %}
