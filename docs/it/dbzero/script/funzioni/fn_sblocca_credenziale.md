{% include-markdown "it/dbzero/script/manual/fn_sblocca_credenziale.md" %}
# ⚙️ Funzione `fn_sblocca_credenziale`

```sql
CREATE FUNCTION fn_sblocca_credenziale(p_auth_user_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sblocca_credenziale(p_auth_user_id integer)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: togliere il blocco dell'admin da una credenziale, per decisione
--   di un SUPER_ADMIN. Non tocca i tentativi.
DECLARE
    v_utente integer;
BEGIN
    -- Prima riga: chi agisce dev'essere SUPER_ADMIN (D-B1).
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_super_admin(v_utente);

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_sblocca_credenziale', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_sblocca_credenziale',
                           'credenziale assente o non valida']);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM django.auth_user au WHERE au.id = p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_sblocca_credenziale', 'E_CREDENZIALE_NON_TROVATA',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    UPDATE config.credenziali c
       SET bloccata_at   = NULL,
           bloccata_da   = NULL,
           motivo_blocco = NULL
     WHERE c.auth_user_id = p_auth_user_id
       AND c.bloccata_at IS NOT NULL;
END;
$function$

COMMENT ON FUNCTION script.fn_sblocca_credenziale(p_auth_user_id integer)
IS 'Toglie il blocco dell''amministratore da una credenziale: e'' l''unica strada, perche'' il blocco non scade e il reset password non lo toglie (D-B3). Prima riga script.fn_guard_super_admin(app.current_user_id) (D-B1). Non tocca i tentativi (fallimenti consecutivi e righe di provenienza: li azzerano un accesso riuscito o un reset). Idempotente: senza blocco, o senza riga, non fa niente. Credenziale inesistente -> E_CREDENZIALE_NON_TROVATA. SECURITY DEFINER del PROPRIETARIO, non di un superuser, search_path bloccato. Brief: brief-db-blocco-login-per-credenziale §3.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
