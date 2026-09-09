# ⚙️ Funzione `fn_scope_ef_whitelist_via_offerta`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_offerta(p_auth_user_id integer, p_offerta_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_offerta(p_auth_user_id integer, p_offerta_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente dell'offerta indicata.
    -- ⚠️ Offerta inesistente -> emittente NULL -> la canonica
    --   risponde false a whitelist valorizzata: fail-closed.
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT o.emittente_fiscale_id
           FROM vendite.offerte_commerciali o
          WHERE o.id = p_offerta_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_offerta(p_auth_user_id integer, p_offerta_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.offerte_commerciali: risale dalla chiave della testata a `emittente_fiscale_id` e delega a script.fn_scope_ef_whitelist. STABLE e NON security definer, come gli altri fn_scope_*. Offerta inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). ⭐ Serve anche alla policy del padre partizionato vendite.note, che smista su target_tipo. Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
