{% include-markdown "it/dbzero/script/manual/fn_imposta_totp_obbligatorio.md" %}
# ⚙️ Funzione `fn_imposta_totp_obbligatorio`

```sql
CREATE FUNCTION fn_imposta_totp_obbligatorio(p_auth_user_id integer, p_valore boolean)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_imposta_totp_obbligatorio(p_auth_user_id integer, p_valore boolean)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: imporre (o togliere) il secondo fattore a una credenziale,
--   per decisione di un SUPER_ADMIN. Upsert: la riga nasce qui.
BEGIN
    -- Prima riga: chi agisce dev'essere SUPER_ADMIN.
    PERFORM script.fn_guard_super_admin(
        NULLIF(current_setting('app.current_user_id', true), '')::integer);

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 OR p_valore IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_imposta_totp_obbligatorio', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id, 'p_valore', p_valore),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_imposta_totp_obbligatorio',
                           'credenziale e valore obbligatori']);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM django.auth_user au WHERE au.id = p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_imposta_totp_obbligatorio', 'E_CREDENZIALE_NON_TROVATA',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- R-DB-A6: su una macchina l'obbligo la ferma. Si rifiuta solo
    -- l'ACCENSIONE: spegnere e' l'uscita (D-2).
    IF p_valore
       AND script.fn_categoria_accesso(p_auth_user_id) = 'SISTEMA' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_imposta_totp_obbligatorio', 'E_CREDENZIALE_DI_SISTEMA',
            jsonb_build_object('auth_user_id', p_auth_user_id, 'valore', p_valore),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    INSERT INTO config.credenziali AS c (auth_user_id, totp_obbligatorio)
    VALUES (p_auth_user_id, p_valore)
    ON CONFLICT (auth_user_id) DO UPDATE
       SET totp_obbligatorio = EXCLUDED.totp_obbligatorio
     WHERE c.totp_obbligatorio IS DISTINCT FROM EXCLUDED.totp_obbligatorio;
END;
$function$

COMMENT ON FUNCTION script.fn_imposta_totp_obbligatorio(p_auth_user_id integer, p_valore boolean)
IS 'Accende o spegne l''obbligo del secondo fattore (TOTP) sulla CREDENZIALE (brief-db-secondo-fattore-totp §2.1): upsert su config.credenziali.totp_obbligatorio, dove la riga nasce alla prima scrittura. Prima riga script.fn_guard_super_admin(app.current_user_id): e'' gestione accessi, come il blocco. Credenziale inesistente -> E_CREDENZIALE_NON_TROVATA (la FK verso django.auth_user in CI non esiste). ACCENDERE l''obbligo su una credenziale di categoria SISTEMA (script.fn_categoria_accesso: processo o API_CLIENT) -> E_CREDENZIALE_DI_SISTEMA, da ogni strada: una macchina non ha un telefono e l''obbligo la ferma. SPEGNERLO passa: e'' l''uscita (D-2, brief-db-credenziale-verbi-amministratore R-DB-A6). Spegnere l''obbligo non toglie il device, e non toglie l''obbligo che viene da un profilo: la risposta unica e'' script.fn_totp_obbligatorio. SECURITY DEFINER del PROPRIETARIO, search_path bloccato: l''app su config.credenziali ha solo SELECT.';
```

</div>

---
{% include-markdown "signature-core.md" %}
