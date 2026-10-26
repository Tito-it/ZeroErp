{% include-markdown "it/dbzero/script/manual/fn_totp_consuma_recovery.md" %}
# ⚙️ Funzione `fn_totp_consuma_recovery`

```sql
CREATE FUNCTION fn_totp_consuma_recovery(p_auth_user_id integer, p_codice_hash text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_totp_consuma_recovery(p_auth_user_id integer, p_codice_hash text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: consumare un codice di recupero (monouso) e dire quanti ne
--   restano.
DECLARE
    -- Esplicito: un conteggio calcolato, non una colonna.
    v_rimasti integer;
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0
       OR p_codice_hash IS NULL OR btrim(p_codice_hash) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_consuma_recovery', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id,
                               'hash_vuoto', p_codice_hash IS NULL OR btrim(p_codice_hash) = ''),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_totp_consuma_recovery',
                           'credenziale e hash del codice obbligatori']);
    END IF;

    UPDATE config.auth_totp_device d
       SET recovery_codes_hash = d.recovery_codes_hash - p_codice_hash,
           ultimo_uso_at       = now()
     WHERE d.auth_user_id = p_auth_user_id
       AND d.confermato
       AND jsonb_exists(d.recovery_codes_hash, p_codice_hash)
    RETURNING jsonb_array_length(d.recovery_codes_hash) INTO v_rimasti;

    IF v_rimasti IS NULL THEN
        IF EXISTS (SELECT 1 FROM config.auth_totp_device d
                    WHERE d.auth_user_id = p_auth_user_id AND d.confermato) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_totp_consuma_recovery', 'E_TOTP_RECOVERY_NON_VALIDO',
                jsonb_build_object('auth_user_id', p_auth_user_id),
                NULL::uuid,
                VARIADIC ARRAY[]::text[]);
        END IF;
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_consuma_recovery', 'E_TOTP_DEVICE_ASSENTE',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN v_rimasti;
END;
$function$

COMMENT ON FUNCTION script.fn_totp_consuma_recovery(p_auth_user_id integer, p_codice_hash text)
IS 'Consuma un codice di recupero del secondo fattore (monouso): toglie l''HASH (lo calcola il backend dal codice digitato) dal mazzo e restituisce quanti codici restano, in UNA istruzione a riga bloccata — due login con lo stesso codice, uno solo passa. Hash assente -> E_TOTP_RECOVERY_NON_VALIDO; device assente o non confermato -> E_TOTP_DEVICE_ASSENTE; id o hash vuoti -> E_AUTH_CHIAMATA_NON_VALIDA. Nessuno agisce: si chiama prima del login e il backend la chiama solo dopo la password. SECURITY DEFINER del PROPRIETARIO, search_path bloccato. Brief: brief-db-secondo-fattore-totp §3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
