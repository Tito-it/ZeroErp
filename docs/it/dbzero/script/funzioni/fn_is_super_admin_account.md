{% include-markdown "it/dbzero/script/manual/fn_is_super_admin_account.md" %}
# ⚙️ Funzione `fn_is_super_admin_account`

```sql
CREATE FUNCTION fn_is_super_admin_account(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_is_super_admin_account(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: la CREDENZIALE ha un binding SUPER_ADMIN attivo? Senza
    --   il cancello della veste di script.fn_is_super_admin, che
    --   chiede questa funzione nel suo ramo ELSE.
    -- Il SUPER_ADMIN si lega solo a un'identita' OPERATORE (binding
    -- per identita', privilegio personale).
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
          JOIN config.profili_accesso_bindings pab
            ON pab.identita_digitale_id = id.id
          JOIN config.profili_accesso pa
            ON pa.id = pab.profilo_accesso_id
         WHERE id.auth_user_id      = p_auth_user_id
           AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
           -- Rev 2026-10-07: «valida oggi» la decide il building block.
           AND script.fn_veste_utilizzabile(id.id)
           AND pab.attivo = true
           AND pa.attivo  = true
           AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
    );
$function$

COMMENT ON FUNCTION script.fn_is_super_admin_account(p_auth_user_id integer)
IS 'La CREDENZIALE (django.auth_user.id) ha un binding SUPER_ADMIN attivo: identita'' OPERATORE attiva e valida oggi, binding e profilo attivi. Senza il cancello della veste: e'' la seconda delle due domande di script.fn_is_super_admin, che la chiede nel suo ramo ELSE (estratta il 2026-09-29, regola del 2). La usa da sola script.fn_totp_obbligatorio: l''obbligo del secondo fattore vale su tutte le porte, anche dove il bypass dei permessi non si accende. Non e'' la domanda dell''anti-lockout (fn_check_almeno_un_super_admin_attivo), che conta tutti gli amministratori raggiungibili. LANGUAGE sql, STABLE, INVOKER, inlineabile. Brief: brief-db-secondo-fattore-totp §2. Rev 2026-10-07 (brief-db-veste-utilizzabile): «identita'' OPERATORE attiva e valida oggi» si legge da script.fn_veste_utilizzabile, non da una copia di attivo + finestra.';
```

</div>

---
{% include-markdown "signature-core.md" %}
