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
 STABLE COST 5000
AS $function$
DECLARE
    v_scope bigint[];
BEGIN
    -- Attore nullo: nessun accesso, come la canonica
    -- fn_check_user_emittente_scope.
    -- ⚠️ Rev 2026-10-04 (Q-1, brief-db-esclusioni-implicite): era
    --    `RETURN true` («batch/sistema: nessun filtro»), cioe' una
    --    sessione con la veste OPERATORE e l'utente vuoto vedeva ogni
    --    billing account. Owner, superuser e BYPASSRLS non passano
    --    dalle policy: non hanno bisogno di questo ramo.
    IF p_auth_user_id IS NULL THEN
        RETURN false;
    END IF;

    -- Scope emittenti dell'operatore (SR id), canonico:
    --   NULL  = nessuna restrizione (solo super_admin)
    --   '{}'  = nessun accesso (no identita OPERATORE attiva,
    --           whitelist vuota dal P-2a, emittente attivo fuori scope)
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
IS 'Adapter via_efba dello scope EF_WHITELIST per billing_account: true se il BA e'' raggiungibile (mapping efba specifico-o-default) da almeno uno degli emittenti nello scope dell''operatore. Riusa fn_get_emittenti_scope_sr_ids ∩ fn_check_ba_visible_for_emittenti. Utente NULL -> false (rev 2026-10-04, Q-1: era true, come la canonica); super admin -> true; nessuna identita'' OPERATORE, whitelist vuota (P-2a) o emittente attivo fuori scope -> false. Nota perf: lo scope e'' query-constant (valutato una volta per auth_user_id); il costo per-riga e'' il lookup efba. Brief: brief-db-esclusioni-implicite Q-1.';
```

---
{% include-markdown "signature-core.md" %}
