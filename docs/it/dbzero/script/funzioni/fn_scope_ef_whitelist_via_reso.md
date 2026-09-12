# ⚙️ Funzione `fn_scope_ef_whitelist_via_reso`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_reso(p_auth_user_id integer, p_reso_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_reso(p_auth_user_id integer, p_reso_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente del reso indicato.
    -- ⚠️ Reso inesistente -> emittente NULL -> la canonica
    --   risponde false a whitelist valorizzata: fail-closed.
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT r.emittente_fiscale_id
           FROM vendite.resi r
          WHERE r.id = p_reso_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_reso(p_auth_user_id integer, p_reso_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.resi: risale dalla chiave della testata a `emittente_fiscale_id` e delega a script.fn_scope_ef_whitelist. STABLE e NON security definer, come gli altri fn_scope_*. Reso inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
