{% include-markdown "it/dbzero/script/manual/fn_totp_rigenera_recovery.md" %}
# ⚙️ Funzione `fn_totp_rigenera_recovery`

```sql
CREATE FUNCTION fn_totp_rigenera_recovery(p_auth_user_id integer, p_recovery_codes_hash jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_totp_rigenera_recovery(p_auth_user_id integer, p_recovery_codes_hash jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: sostituire il mazzo dei codici di recupero di un device in uso.
DECLARE
    v_device_id config.auth_totp_device.id%TYPE;
BEGIN
    -- Prima riga: chi agisce e' la credenziale stessa.
    PERFORM script.fn_guard_utente_stesso(
        NULLIF(current_setting('app.current_user_id', true), '')::integer,
        p_auth_user_id);

    IF p_auth_user_id <= 0
       OR NOT script.fn_check_totp_recovery_hash(p_recovery_codes_hash) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_rigenera_recovery', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id,
                               'recovery_tipo', jsonb_typeof(p_recovery_codes_hash)),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_totp_rigenera_recovery',
                           'codici di recupero (array non vuoto di hash distinti) obbligatori']);
    END IF;

    UPDATE config.auth_totp_device d
       SET recovery_codes_hash = p_recovery_codes_hash
     WHERE d.auth_user_id = p_auth_user_id
       AND d.confermato
    RETURNING d.id INTO v_device_id;

    IF v_device_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_rigenera_recovery', 'E_TOTP_DEVICE_ASSENTE',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_totp_rigenera_recovery(p_auth_user_id integer, p_recovery_codes_hash jsonb)
IS 'Sostituisce il mazzo dei codici di recupero del secondo fattore di un device CONFERMATO: i vecchi, usati o no, non valgono piu''. Il backend ha verificato prima un codice corrente e mostra i nuovi una volta sola. Forma del mazzo: script.fn_check_totp_recovery_hash (se no E_AUTH_CHIAMATA_NON_VALIDA). Device assente o non confermato -> E_TOTP_DEVICE_ASSENTE (durante il setup i codici li da'' la registrazione). Chi agisce: la credenziale stessa (script.fn_guard_utente_stesso). SECURITY DEFINER del PROPRIETARIO, search_path bloccato. Brief: brief-db-secondo-fattore-totp §3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
