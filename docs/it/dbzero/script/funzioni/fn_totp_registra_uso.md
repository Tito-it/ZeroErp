{% include-markdown "it/dbzero/script/manual/fn_totp_registra_uso.md" %}
# ⚙️ Funzione `fn_totp_registra_uso`

```sql
CREATE FUNCTION fn_totp_registra_uso(p_auth_user_id integer, p_passo bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_totp_registra_uso(p_auth_user_id integer, p_passo bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: accettare il passo di un codice gia' verificato dal backend
--   solo se successivo all'ultimo usato, e registrarlo.
DECLARE
    v_device_id config.auth_totp_device.id%TYPE;
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0
       OR p_passo IS NULL OR p_passo < 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_registra_uso', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id, 'p_passo', p_passo),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_totp_registra_uso',
                           'credenziale e passo (>= 0) obbligatori']);
    END IF;

    -- Confronto e scrittura insieme: la riga resta bloccata fino alla
    -- fine della transazione, e chi arriva dopo rivaluta il WHERE.
    UPDATE config.auth_totp_device d
       SET ultimo_passo_usato = p_passo,
           ultimo_uso_at      = now()
     WHERE d.auth_user_id = p_auth_user_id
       AND d.confermato
       AND d.ultimo_passo_usato < p_passo
    RETURNING d.id INTO v_device_id;

    IF v_device_id IS NULL THEN
        IF EXISTS (SELECT 1 FROM config.auth_totp_device d
                    WHERE d.auth_user_id = p_auth_user_id AND d.confermato) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_totp_registra_uso', 'E_TOTP_PASSO_GIA_USATO',
                jsonb_build_object('auth_user_id', p_auth_user_id, 'passo', p_passo),
                NULL::uuid,
                VARIADIC ARRAY[]::text[]);
        END IF;
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_registra_uso', 'E_TOTP_DEVICE_ASSENTE',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_totp_registra_uso(p_auth_user_id integer, p_passo bigint)
IS 'Anti-replay del secondo fattore (RFC 6238 §5.2): il backend ha verificato il codice e ne passa il PASSO; si accetta solo un passo successivo all''ultimo usato e lo si registra con ultimo_uso_at, in UNA istruzione a riga bloccata (due richieste simultanee con lo stesso codice: una sola passa). Rende monouso anche il token di sfida del login a due passi. Passo non successivo -> E_TOTP_PASSO_GIA_USATO; device assente o non confermato -> E_TOTP_DEVICE_ASSENTE; id o passo rotti -> E_AUTH_CHIAMATA_NON_VALIDA. Nessuno agisce: si chiama prima del login, come fn_registra_tentativo_login, e il backend la chiama solo dopo la password. Un codice sbagliato non arriva qui (E_TOTP_CODICE_NON_VALIDO e il tentativo fallito sono del backend, D-T2). SECURITY DEFINER del PROPRIETARIO, search_path bloccato. Brief: brief-db-secondo-fattore-totp §4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
