{% include-markdown "it/dbzero/script/manual/fn_is_super_admin.md" %}
# ⚙️ Funzione `fn_is_super_admin`

```sql
CREATE FUNCTION fn_is_super_admin(p_auth_user_id integer)
```

**Definizione completa:**

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
    --      EXISTS identita OPERATORE attiva con binding
    --      SUPER_ADMIN attivo (logica pre-GUC invariata).
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
        ELSE EXISTS (
            SELECT 1
              FROM anagrafiche.identita_digitali id
              JOIN config.profili_accesso_bindings pab
                ON pab.identita_digitale_id = id.id
              JOIN config.profili_accesso pa
                ON pa.id = pab.profilo_accesso_id
             WHERE id.auth_user_id      = p_auth_user_id
               AND id.attivo            = true
               AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
               AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
               AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
               AND pab.attivo = true
               AND pa.attivo  = true
               AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
        )
    END;
$function$

COMMENT ON FUNCTION script.fn_is_super_admin(p_auth_user_id integer)
IS 'SUPER_ADMIN check context-aware (post PR-B 21-04-2026). Se GUC app.ruolo_applicativo e'' popolata e diversa da OPERATORE ritorna false (fail-closed su contesti portale/shop). Altrimenti applica la logica legacy: EXISTS identita OPERATORE attiva con binding SUPER_ADMIN attivo. STABLE, inlineable, fail-soft su GUC mancante (chiamate test/psql OK).';
```

---
{% include-markdown "signature-core.md" %}
