{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist`

```sql
CREATE FUNCTION fn_scope_ef_whitelist(p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist(p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        p_emittente_fiscale_id
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist(p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Adapter PK dello scope EF_WHITELIST (entry-point policy per tabelle con emittente_fiscale_id). Delega a script.fn_check_user_emittente_scope (canonica auth_user_id, bypass SUPER_ADMIN/fix C7, read+write unificati). STABLE, inlineable. Adapter SR/via_fattura in changeSet -06/-07.';
```

</div>

---
{% include-markdown "signature-core.md" %}
