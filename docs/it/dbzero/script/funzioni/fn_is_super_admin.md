{% include-markdown "it/dbzero/script/manual/fn_is_super_admin.md" %}
# ⚙️ Funzione `fn_is_super_admin`

```sql
CREATE FUNCTION fn_is_super_admin(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_is_super_admin(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- =========================================================
    -- Scopo:
    --   Verifica SUPER_ADMIN context-aware.
    --
    -- Logica (post PR-B 21-04-2026, SSO multi-veste):
    --   1. Se GUC app.ruolo_applicativo e' popolata ed e'
    --      diversa da OPERATORE -> false (bypass non si
    --      attiva in contesto portale/shop/api_client).
    --   2. Altrimenti (GUC non popolata o ='OPERATORE'):
    --      la credenziale ha un binding SUPER_ADMIN attivo,
    --      domanda di script.fn_is_super_admin_account
    --      (rev 2026-09-29, regola del 2: la chiede anche
    --      l'obbligo del secondo fattore).
    --
    -- Fail-soft GUC: current_setting(..., true) ritorna
    -- NULL se non settata; NULLIF normalizza '' -> NULL.
    -- Chiamate legacy (test/psql senza GUC) funzionano come
    -- prima: l'invariante "un user con OPERATORE+SUPER_ADMIN
    -- e' super admin a livello account" resta per l'uso
    -- fuori request HTTP.
    -- =========================================================
    SELECT CASE
        WHEN NULLIF(current_setting('app.ruolo_applicativo', true), '') IS NOT NULL
             AND NULLIF(current_setting('app.ruolo_applicativo', true), '') <> 'OPERATORE'
            THEN false
        ELSE script.fn_is_super_admin_account(p_auth_user_id)
    END;
$function$

COMMENT ON FUNCTION script.fn_is_super_admin(p_auth_user_id integer)
IS 'SUPER_ADMIN check context-aware (post PR-B 21-04-2026). Se GUC app.ruolo_applicativo e'' popolata e diversa da OPERATORE ritorna false (fail-closed su contesti portale/shop). Altrimenti risponde script.fn_is_super_admin_account: EXISTS identita OPERATORE attiva con binding SUPER_ADMIN attivo (rev 2026-09-29, regola del 2: quella domanda la fa anche l''obbligo del secondo fattore, senza il cancello della veste). STABLE, inlineable, fail-soft su GUC mancante (chiamate test/psql OK).';
```

</div>

---
{% include-markdown "signature-core.md" %}
