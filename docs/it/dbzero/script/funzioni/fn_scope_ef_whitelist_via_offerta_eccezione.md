# ⚙️ Funzione `fn_scope_ef_whitelist_via_offerta_eccezione`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_offerta_eccezione(p_auth_user_id integer, p_eccezione_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_offerta_eccezione(p_auth_user_id integer, p_eccezione_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: come sopra, ma partendo da una ECCEZIONE di offerta —
    --   e' la chiave che porta
    --   vendite.offerte_commerciali_eccezioni_componenti.
    -- ⭐ Delega alla sorella invece di ripetere la risalita: la
    --   regola «come un'offerta nomina il proprio emittente»
    --   resta scritta in un posto solo.
    SELECT script.fn_scope_ef_whitelist_via_offerta(
        p_auth_user_id,
        (SELECT e.offerta_id
           FROM vendite.offerte_commerciali_eccezioni e
          WHERE e.id = p_eccezione_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_offerta_eccezione(p_auth_user_id integer, p_eccezione_id bigint)
IS 'Come fn_scope_ef_whitelist_via_offerta ma a partire da una eccezione di offerta: e'' la chiave che porta vendite.offerte_commerciali_eccezioni_componenti. Delega alla sorella invece di ripetere la risalita alla testata.';
```

---
{% include-markdown "signature-core.md" %}
