# ⚙️ Funzione `fn_scope_ef_whitelist_via_pratica`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_pratica(p_auth_user_id integer, p_pratica_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_pratica(p_auth_user_id integer, p_pratica_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente della pratica indicata.
    -- ⚠️ Pratica inesistente -> emittente NULL -> la canonica
    --   risponde false quando la whitelist e' valorizzata:
    --   fail-closed, come per le sei famiglie di documento.
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT p.emittente_fiscale_id
           FROM pratiche.pratiche p
          WHERE p.id = p_pratica_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_pratica(p_auth_user_id integer, p_pratica_id bigint)
IS 'Adattatore di scope per i satelliti di pratiche.pratiche: risale da pratica_id a `emittente_fiscale_id` e delega a script.fn_scope_ef_whitelist. STABLE e NON security definer, come gli altri fn_scope_*: una funzione security definer dentro una policy guarderebbe con gli occhi dell''owner, che la RLS non vede. Pratica inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md §11.7';
```

---
{% include-markdown "signature-core.md" %}
