{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_efba.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_efba`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_efba(p_auth_user_id integer, p_billing_account_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_efba(p_auth_user_id integer, p_billing_account_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_scope bigint[];
BEGIN
    -- Attore nullo (batch/sistema): nessun filtro (coerente con
    -- la canonica fn_check_user_emittente_scope).
    IF p_auth_user_id IS NULL THEN
        RETURN true;
    END IF;

    -- Scope emittenti dell'operatore (SR id), canonico:
    --   NULL  = nessuna restrizione (super_admin / whitelist vuota)
    --   '{}'  = nessun accesso (no identita OPERATORE attiva)
    --   array = whitelist SR
    v_scope := script.fn_get_emittenti_scope_sr_ids(p_auth_user_id);

    IF v_scope IS NULL THEN
        RETURN true;                      -- accesso globale
    END IF;

    IF cardinality(v_scope) = 0 THEN
        RETURN false;                     -- fail-closed
    END IF;

    -- Whitelist: il BA deve essere visibile (efba specifico o
    -- default) per almeno uno degli emittenti in scope.
    RETURN script.fn_check_ba_visible_for_emittenti(
        p_billing_account_id, v_scope);
END
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_efba(p_auth_user_id integer, p_billing_account_id bigint)
IS 'Adapter via_efba dello scope EF_WHITELIST per billing_account: true se il BA e'' raggiungibile (mapping efba specifico-o-default) da almeno uno degli emittenti nello scope dell''operatore. Riusa fn_get_emittenti_scope_sr_ids ∩ fn_check_ba_visible_for_emittenti. NULL user/super_admin/whitelist vuota -> true; no identita -> false. Nota perf: lo scope e'' query-constant (valutato una volta per auth_user_id); il costo per-riga e'' il lookup efba.';
```

---
{% include-markdown "signature-core.md" %}
