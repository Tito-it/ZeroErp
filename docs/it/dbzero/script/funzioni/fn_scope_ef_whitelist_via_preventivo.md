# ⚙️ Funzione `fn_scope_ef_whitelist_via_preventivo`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_preventivo(p_auth_user_id integer, p_preventivo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_preventivo(p_auth_user_id integer, p_preventivo_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente del preventivo indicato.
    -- ⚠️ Preventivo inesistente -> emittente NULL -> la canonica
    --   risponde false quando la whitelist e' valorizzata:
    --   fail-closed, come per le fatture.
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT p.emittente_fiscale_id
           FROM vendite.preventivi p
          WHERE p.id = p_preventivo_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_preventivo(p_auth_user_id integer, p_preventivo_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.preventivi: risale dalla chiave della testata a `emittente_fiscale_id` e delega a script.fn_scope_ef_whitelist. STABLE e NON security definer, come gli altri fn_scope_*: una funzione security definer dentro una policy guarderebbe con gli occhi dell''owner, che la RLS non vede. Preventivo inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
