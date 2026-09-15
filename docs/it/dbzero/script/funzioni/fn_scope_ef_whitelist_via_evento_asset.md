{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_evento_asset.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_evento_asset`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_evento_asset(p_auth_user_id integer, p_evento_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_evento_asset(p_auth_user_id integer, p_evento_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: perimetro di un evento asset via l'ASSET (non un magazzino:
    --   l'evento puo' non averne). Chiave di note_evento_asset.
    SELECT script.fn_scope_ef_whitelist_via_asset(
        p_auth_user_id,
        (SELECT e.asset_id
           FROM magazzino.eventi_assets e
          WHERE e.id = p_evento_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_evento_asset(p_auth_user_id integer, p_evento_id bigint)
IS 'Adattatore di scope per un evento asset via l''ASSET (delega a via_asset): un evento puo'' non avere magazzino. Chiave di note_evento_asset.';
```

---
{% include-markdown "signature-core.md" %}
