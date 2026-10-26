{% include-markdown "it/dbzero/script/manual/fn_imposta_deve_cambiare_password.md" %}
# ⚙️ Funzione `fn_imposta_deve_cambiare_password`

```sql
CREATE FUNCTION fn_imposta_deve_cambiare_password(p_auth_user_id integer, p_valore boolean)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_imposta_deve_cambiare_password(p_auth_user_id integer, p_valore boolean)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: impostare il cambio password obbligatorio della credenziale.
--   Upsert: la riga nasce qui se non c'e'.
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 OR p_valore IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_imposta_deve_cambiare_password', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id, 'p_valore', p_valore),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_imposta_deve_cambiare_password',
                           'credenziale e valore obbligatori']);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM django.auth_user au WHERE au.id = p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_imposta_deve_cambiare_password', 'E_CREDENZIALE_NON_TROVATA',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    INSERT INTO config.credenziali AS c (auth_user_id, deve_cambiare_password)
    VALUES (p_auth_user_id, p_valore)
    ON CONFLICT (auth_user_id) DO UPDATE
       SET deve_cambiare_password = EXCLUDED.deve_cambiare_password
     WHERE c.deve_cambiare_password IS DISTINCT FROM EXCLUDED.deve_cambiare_password;
END;
$function$

COMMENT ON FUNCTION script.fn_imposta_deve_cambiare_password(p_auth_user_id integer, p_valore boolean)
IS 'Scrive il cambio password obbligatorio della CREDENZIALE (D-7): upsert su config.credenziali, dove la riga nasce alla prima scrittura. La chiamano invito operatore, cambio password, reset e attivazione (backend). SECURITY DEFINER del PROPRIETARIO, non di un superuser, search_path bloccato: l''app su config.credenziali ha solo SELECT. Nessun guard di permesso, dichiarato: i chiamanti girano come admin, come l''utente stesso o prima del login. Credenziale inesistente -> E_CREDENZIALE_NON_TROVATA (la FK verso django.auth_user in CI non esiste). Brief: brief-db-blocco-login-per-credenziale §3.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
