{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_asset.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_asset`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_asset(p_auth_user_id integer, p_asset_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_asset(p_auth_user_id integer, p_asset_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: perimetro emittente di un asset, che porta l'emittente in
    --   proprio (un asset presso un cliente non e' in nessun magazzino).
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT a.emittente_fiscale_id
           FROM magazzino.assets a
          WHERE a.id = p_asset_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_asset(p_auth_user_id integer, p_asset_id bigint)
IS 'Adattatore di scope per gli asset, che portano l''emittente in proprio (un asset presso un cliente non e'' in nessun magazzino). Fail-closed su asset inesistente. Lo usano le policy di assets, eventi_assets (per delega) e note_asset.';
```

---
{% include-markdown "signature-core.md" %}
