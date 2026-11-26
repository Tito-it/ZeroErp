# ⚙️ Funzione `fn_guard_gestione_veste`

```sql
CREATE FUNCTION fn_guard_gestione_veste(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_gestione_veste(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: chi agisce (p_auth_user_id, letto dalla sessione
    --   dal chiamante) puo' gestire una veste di tipo
    --   p_ruolo_applicativo? No -> E_PERMESSO_NEGATO.
    -- =========================================================
    IF p_ruolo_applicativo IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_guard_gestione_veste', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            'anagrafiche.fn_guard_gestione_veste',
            'tipo di veste mancante');
    END IF;

    CASE p_ruolo_applicativo
        WHEN 'CLIENTE_PORTALE', 'SHOP_CUSTOMER' THEN
            PERFORM script.fn_guard_livello(p_auth_user_id, 'anagrafiche', 'cliente', 'TUTTO');
        WHEN 'FORNITORE_PORTALE' THEN
            PERFORM script.fn_guard_livello(p_auth_user_id, 'anagrafiche', 'fornitore', 'TUTTO');
        ELSE
            -- OPERATORE, e ogni veste senza una porta di gestione
            PERFORM script.fn_guard_super_admin(p_auth_user_id);
    END CASE;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_gestione_veste(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
IS 'Guard: l''utente p_auth_user_id puo'' revocare una veste di tipo p_ruolo_applicativo, o toglierne la revoca? CLIENTE_PORTALE e SHOP_CUSTOMER: livello TUTTO su anagrafiche.cliente (script.fn_guard_livello); FORNITORE_PORTALE: livello TUTTO su anagrafiche.fornitore; OPERATORE e ogni altro tipo: SUPER_ADMIN (script.fn_guard_super_admin). Sono i permessi delle porte di invito e disattivazione del backend. No, o utente NULL: E_PERMESSO_NEGATO. Tipo NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. La usano anagrafiche.fn_revoca_veste e anagrafiche.fn_togli_revoca_veste. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
