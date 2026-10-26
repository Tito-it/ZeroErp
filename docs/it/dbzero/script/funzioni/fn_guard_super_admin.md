{% include-markdown "it/dbzero/script/manual/fn_guard_super_admin.md" %}
# ⚙️ Funzione `fn_guard_super_admin`

```sql
CREATE FUNCTION fn_guard_super_admin(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_super_admin(p_auth_user_id integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: chiedere SUPER_ADMIN nella prima riga di un verbo di scrittura.
--   La regola la decide script.fn_is_super_admin (la stessa del backend);
--   qui si solleva quando la risposta e' no.
-- Uso: PERFORM script.fn_guard_super_admin(
--          NULLIF(current_setting('app.current_user_id', true), '')::integer);
BEGIN
    -- NULL (utente NULL) vale no: fail-closed.
    IF p_auth_user_id IS NULL
       OR NOT COALESCE(script.fn_is_super_admin(p_auth_user_id), false) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_guard_super_admin', 'E_PERMESSO_NEGATO',
            jsonb_build_object('richiesto',    'SUPER_ADMIN',
                               'auth_user_id', p_auth_user_id,
                               'senza_utente', p_auth_user_id IS NULL),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_super_admin(p_auth_user_id integer)
IS 'Guard dei verbi di scrittura che chiedono SUPER_ADMIN (modello «una scrittura = un verbo»; D-B1 di brief-db-blocco-login-per-credenziale: la gestione accessi e'' amm_software, che non e'' un''area del catalogo ma una porta per soli SUPER_ADMIN). La regola NON e'' qui: la decide script.fn_is_super_admin, la stessa del backend, gate di contesto compreso (fuori dalla veste OPERATORE risponde false). Risposta no -> E_PERMESSO_NEGATO (NON_PERMESSO, lo stesso codice del backend), anche a utente NULL: fail-closed, con senza_utente nel contesto. Gemello di script.fn_guard_azione. L''utente arriva come parametro: il chiamante legge app.current_user_id (linee-guida-sql §10.4). INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
