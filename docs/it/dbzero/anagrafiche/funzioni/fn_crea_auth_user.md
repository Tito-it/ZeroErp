{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_auth_user.md" %}
# ⚙️ Funzione `fn_crea_auth_user`

```sql
CREATE FUNCTION fn_crea_auth_user(p_username text, p_email text, p_password_hash text, p_first_name text, p_last_name text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_auth_user(p_username text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_password_hash text DEFAULT NULL::text, p_first_name text DEFAULT NULL::text, p_last_name text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_auth_user_id  integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Crea un record auth_user (Django) con validazione
    --   parametri e guard unicita'. Non crea soggetto ne'
    --   bridge: e' un building block atomico.
    --
    -- Parametri obbligatori:
    --   p_username:      username univoco
    --   p_email:         email univoca, SENZA distinguere
    --                    maiuscole e minuscole (D-9, rev 20260925-41)
    --   p_password_hash: hash password Django
    --
    -- Parametri opzionali:
    --   p_first_name:    nome (default NULL)
    --   p_last_name:     cognome (default NULL)
    --
    -- Restituisce:
    --   auth_user.id dell'utente creato
    --
    -- Riusabile da:
    --   fn_crea_operatore_v2 (solo quando la credenziale
    --   dell'email non esiste: altrimenti la riusa, D-6),
    --   qualsiasi flusso che necessiti di un utente Django.
    -- =========================================================

    -- =============================================================
    -- Validazione parametri obbligatori
    -- =============================================================

    IF p_username IS NULL OR TRIM(p_username) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_auth_user',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_username'),
            NULL::uuid, 'Username obbligatorio.'
        );
    END IF;

    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_auth_user',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_email'),
            NULL::uuid, 'Email obbligatoria.'
        );
    END IF;

    IF p_password_hash IS NULL OR LENGTH(p_password_hash) = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_auth_user',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_password_hash'),
            NULL::uuid, 'Password hash obbligatorio.'
        );
    END IF;

    -- =============================================================
    -- Guard unicita'
    -- =============================================================

    IF EXISTS (SELECT 1 FROM django.auth_user WHERE username = TRIM(p_username)) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_auth_user',
            'E_ADMIN_USERNAME_DUPLICATO',
            jsonb_build_object('username', p_username),
            NULL::uuid, 'Username gia'' esistente.'
        );
    END IF;

    -- ⭐ Rev 20260925-41: la regola «questa email ha gia' una
    --   credenziale» sta in UN posto, senza distinguere maiuscole e
    --   minuscole (D-9). Era `email = TRIM(p_email)`: Mario@x.it e
    --   mario@x.it passavano come due persone.
    IF script.fn_get_auth_user_id_for_email(p_email) IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_auth_user',
            'E_ADMIN_EMAIL_DUPLICATA',
            jsonb_build_object('email', p_email),
            NULL::uuid, 'Email gia'' esistente.'
        );
    END IF;

    -- =============================================================
    -- INSERT auth_user
    -- =============================================================

    INSERT INTO django.auth_user (
        username, email, first_name, last_name,
        password, is_active, is_staff, is_superuser, date_joined
    )
    VALUES (
        TRIM(p_username),
        TRIM(p_email),
        COALESCE(TRIM(p_first_name), ''),
        COALESCE(TRIM(p_last_name), ''),
        p_password_hash,
        true, false, false, NOW()
    )
    RETURNING id INTO v_auth_user_id;

    RETURN v_auth_user_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_auth_user(p_username text, p_email text, p_password_hash text, p_first_name text, p_last_name text)
IS 'Building block: crea auth_user (Django) con guard unicita'' username/email. Obbligatori: p_username, p_email, p_password_hash (DEFAULT NULL, guard nel body). Ritorna auth_user.id. ⭐ Rev 20260925-41: l''email duplicata si riconosce SENZA distinguere maiuscole e minuscole (D-9 di brief-db-blocco-login-per-credenziale), chiedendo a script.fn_get_auth_user_id_for_email, la sede unica della regola; il codice resta E_ADMIN_EMAIL_DUPLICATA (senza il guard la collisione arriverebbe dall''indice unico come 23505 anonimo). Chiamata dalla madre fn_crea_operatore_v2 solo quando l''email non ha ancora una credenziale (altrimenti la riusa, D-6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
