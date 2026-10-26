{% include-markdown "it/dbzero/script/manual/fn_totp_conferma_device.md" %}
# ⚙️ Funzione `fn_totp_conferma_device`

```sql
CREATE FUNCTION fn_totp_conferma_device(p_auth_user_id integer, p_passo bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_totp_conferma_device(p_auth_user_id integer, p_passo bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: confermare il device dopo il primo codice verificato dal
--   backend, registrandone il passo.
DECLARE
    v_device_id config.auth_totp_device.id%TYPE;
BEGIN
    -- Prima riga: chi agisce e' la credenziale stessa.
    PERFORM script.fn_guard_utente_stesso(
        NULLIF(current_setting('app.current_user_id', true), '')::integer,
        p_auth_user_id);

    IF p_auth_user_id <= 0 OR p_passo IS NULL OR p_passo < 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_conferma_device', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id, 'p_passo', p_passo),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_totp_conferma_device',
                           'credenziale e passo (>= 0) obbligatori']);
    END IF;

    UPDATE config.auth_totp_device d
       SET confermato         = true,
           ultimo_passo_usato = p_passo,
           ultimo_uso_at      = now()
     WHERE d.auth_user_id = p_auth_user_id
       AND NOT d.confermato
    RETURNING d.id INTO v_device_id;

    IF v_device_id IS NULL THEN
        IF EXISTS (SELECT 1 FROM config.auth_totp_device d
                    WHERE d.auth_user_id = p_auth_user_id) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_totp_conferma_device', 'E_TOTP_DEVICE_GIA_ATTIVO',
                jsonb_build_object('auth_user_id', p_auth_user_id),
                NULL::uuid,
                VARIADIC ARRAY[]::text[]);
        END IF;
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_conferma_device', 'E_TOTP_DEVICE_ASSENTE',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_totp_conferma_device(p_auth_user_id integer, p_passo bigint)
IS 'Conferma il device del secondo fattore (TOTP) dopo che il backend ha verificato il primo codice: confermato = true e il PASSO di quel codice diventa il primo registrato (da li'' l''anti-replay di script.fn_totp_registra_uso). Una istruzione (UPDATE … WHERE NOT confermato). Gia'' confermato -> E_TOTP_DEVICE_GIA_ATTIVO; nessun device -> E_TOTP_DEVICE_ASSENTE; passo NULL o < 0 -> E_AUTH_CHIAMATA_NON_VALIDA. Nessun controllo di passo gia'' usato: un device non confermato non ne ha. Chi agisce: la credenziale stessa (script.fn_guard_utente_stesso). SECURITY DEFINER del PROPRIETARIO, search_path bloccato. Brief: brief-db-secondo-fattore-totp §3-4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
