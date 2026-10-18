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
    -- Scopo: l'utente vede l'emittente della chiave (asset)? La
    --   domanda su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('asset', ...), DEFINER, invece di
    --   leggerlo sotto la RLS del padre: una strada sola, e nessuna policy del
    --   padre rieseguita a ogni chiamata. Stesse risposte. Le policy non passano
    --   piu' di qui (20261018-50).
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('asset', p_asset_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_asset(p_auth_user_id integer, p_asset_id bigint)
IS '⭐ rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l''emittente dal risolutore DEFINER (via_efba: dalla composizione delle policy, in convenzione soggetto_ruolo); una strada sola, nessuna policy del padre per chiamata. Stesse risposte. Adattatore di scope per gli asset, che portano l''emittente in proprio (un asset presso un cliente non e'' in nessun magazzino). Fail-closed su asset inesistente. Lo usano le policy di assets, eventi_assets (per delega) e note_asset.';
```

---
{% include-markdown "signature-core.md" %}
