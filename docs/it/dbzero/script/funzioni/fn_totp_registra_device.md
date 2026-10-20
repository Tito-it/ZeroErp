{% include-markdown "it/dbzero/script/manual/fn_totp_registra_device.md" %}
# ⚙️ Funzione `fn_totp_registra_device`

```sql
CREATE FUNCTION fn_totp_registra_device(p_auth_user_id integer, p_secret_encrypted character varying, p_recovery_codes_hash jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_totp_registra_device(p_auth_user_id integer, p_secret_encrypted character varying, p_recovery_codes_hash jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: registrare il device del secondo fattore, non confermato;
--   sostituisce un setup a meta', non un device in uso.
DECLARE
    v_device_id config.auth_totp_device.id%TYPE;
BEGIN
    -- Prima riga: chi agisce e' la credenziale stessa.
    PERFORM script.fn_guard_utente_stesso(
        NULLIF(current_setting('app.current_user_id', true), '')::integer,
        p_auth_user_id);

    IF p_auth_user_id <= 0
       OR p_secret_encrypted IS NULL OR btrim(p_secret_encrypted) = ''
       OR NOT script.fn_check_totp_recovery_hash(p_recovery_codes_hash) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_registra_device', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id,
                               'segreto_vuoto', p_secret_encrypted IS NULL
                                                OR btrim(p_secret_encrypted) = '',
                               'recovery_tipo', jsonb_typeof(p_recovery_codes_hash)),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_totp_registra_device',
                           'segreto e codici di recupero (array non vuoto di hash distinti) obbligatori']);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM django.auth_user au WHERE au.id = p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_registra_device', 'E_CREDENZIALE_NON_TROVATA',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- Una istruzione: nasce, o sostituisce un setup a meta'. Un
    -- device confermato non si tocca (WHERE) e RETURNING resta vuoto.
    INSERT INTO config.auth_totp_device AS d
           (auth_user_id, secret_encrypted, recovery_codes_hash, confermato)
    VALUES (p_auth_user_id, p_secret_encrypted, p_recovery_codes_hash, false)
    ON CONFLICT (auth_user_id) DO UPDATE
       SET secret_encrypted    = EXCLUDED.secret_encrypted,
           recovery_codes_hash = EXCLUDED.recovery_codes_hash,
           ultimo_passo_usato  = NULL,
           ultimo_uso_at       = NULL
     WHERE NOT d.confermato
    RETURNING d.id INTO v_device_id;

    IF v_device_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_registra_device', 'E_TOTP_DEVICE_GIA_ATTIVO',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_totp_registra_device(p_auth_user_id integer, p_secret_encrypted character varying, p_recovery_codes_hash jsonb)
IS 'Registra il device del secondo fattore (TOTP) di una credenziale, NON confermato: segreto cifrato dal backend e hash dei codici di recupero (script.fn_check_totp_recovery_hash: array non vuoto di stringhe distinte). Sostituisce un device non confermato (il setup ricomincia); su un device confermato -> E_TOTP_DEVICE_GIA_ATTIVO (va prima disabilitato). Una istruzione (upsert con WHERE NOT confermato): nessuna finestra fra domanda e scrittura. Chi agisce: la credenziale stessa (script.fn_guard_utente_stesso). Forma sbagliata -> E_AUTH_CHIAMATA_NON_VALIDA; credenziale inesistente -> E_CREDENZIALE_NON_TROVATA. SECURITY DEFINER del PROPRIETARIO, search_path bloccato: all''app solo SELECT. Brief: brief-db-secondo-fattore-totp §3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
