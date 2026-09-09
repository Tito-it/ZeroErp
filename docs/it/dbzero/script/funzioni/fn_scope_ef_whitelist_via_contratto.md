# ⚙️ Funzione `fn_scope_ef_whitelist_via_contratto`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_contratto(p_auth_user_id integer, p_contratto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_contratto(p_auth_user_id integer, p_contratto_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente del contratto indicato.
    -- ⚠️ Contratto inesistente -> emittente NULL -> la canonica
    --   risponde false a whitelist valorizzata: fail-closed.
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT k.emittente_fiscale_id
           FROM vendite.contratti k
          WHERE k.id = p_contratto_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_contratto(p_auth_user_id integer, p_contratto_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.contratti: risale dalla chiave della testata a `emittente_fiscale_id` e delega a script.fn_scope_ef_whitelist. STABLE e NON security definer, come gli altri fn_scope_*. Contratto inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). ⚠️ Non copre vendite.fatture_atti (si aggancia a fatture) ne'' vendite.attivita_fatturabili (rotta portante commessa_id, non contratto_id che e'' nullable). Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
