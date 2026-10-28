{% include-markdown "it/dbzero/script/manual/fn_guard_utente_stesso.md" %}
# ⚙️ Funzione `fn_guard_utente_stesso`

```sql
CREATE FUNCTION fn_guard_utente_stesso(p_utente integer, p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_utente_stesso(p_utente integer, p_auth_user_id integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: chiedere che chi agisce sia la credenziale su cui agisce,
--   nella prima riga di un verbo che tocca «le proprie» cose.
-- Uso: PERFORM script.fn_guard_utente_stesso(
--          NULLIF(current_setting('app.current_user_id', true), '')::integer,
--          p_auth_user_id);
BEGIN
    -- NULL (nessun utente in sessione) vale no: fail-closed.
    IF p_utente IS NULL OR p_auth_user_id IS NULL
       OR p_utente <> p_auth_user_id THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_guard_utente_stesso', 'E_PERMESSO_NEGATO',
            jsonb_build_object('richiesto',    'UTENTE_STESSO',
                               'auth_user_id', p_auth_user_id,
                               'chi_agisce',   p_utente,
                               'senza_utente', p_utente IS NULL),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_utente_stesso(p_utente integer, p_auth_user_id integer)
IS 'Guard dei verbi che toccano le cose PROPRIE di una credenziale (il device del secondo fattore: registrare, confermare, rigenerare i codici, disabilitare): chi agisce (p_utente, che il chiamante legge da app.current_user_id, linee-guida-sql §10.4) dev''essere la credenziale su cui agisce (p_auth_user_id). No -> E_PERMESSO_NEGATO (NON_PERMESSO, lo stesso codice del backend e di fn_guard_super_admin, di cui e'' il gemello), anche a utente NULL: fail-closed, con senza_utente nel contesto. Protegge da un backend che sbaglia la GUC, non da uno manomesso. INVOKER. Brief: brief-db-secondo-fattore-totp §3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
