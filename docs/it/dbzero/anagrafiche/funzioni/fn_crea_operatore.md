{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_operatore.md" %}
# ⚙️ Funzione `fn_crea_operatore`

```sql
CREATE FUNCTION fn_crea_operatore(p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_ruolo_sistema config.ruolo_sistema, p_valido_dal date, p_valido_al date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_operatore(p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_username text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_password_hash text DEFAULT NULL::text, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT 'M'::bpchar, p_ruolo_sistema config.ruolo_sistema DEFAULT 'OPERATIVO'::config.ruolo_sistema, p_valido_dal date DEFAULT CURRENT_DATE, p_valido_al date DEFAULT NULL::date)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_auth_user_id   integer;
    v_soggetto_id    anagrafiche.soggetti.id%TYPE;
    v_ru_id          anagrafiche.risorse_umane.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Orchestratore transazionale per creazione operatore.
    --   Delega ai building block atomici:
    --     1. fn_crea_auth_user   → crea utente Django
    --     2. fn_crea_soggetto_pf → crea soggetto PF + contatto
    --     3. fn_crea_risorsa_umana → crea RU + bridge auth_user
    --   Singola transazione, rollback automatico.
    --
    -- Parametri obbligatori:
    --   p_cognome, p_nome, p_codice_fiscale:
    --     dati soggetto PF
    --   p_username, p_email, p_password_hash:
    --     credenziali auth_user
    --   p_qualifica_id:
    --     qualifica risorsa umana
    --
    -- Parametri opzionali:
    --   p_unita_organizzativa_id: UO (default NULL)
    --   p_data_nascita:  data nascita (default NULL)
    --   p_sesso:         sesso (default 'M')
    --   p_ruolo_sistema: ruolo sistema (default OPERATIVO)
    --   p_valido_dal:    inizio validita' (default oggi)
    --   p_valido_al:     fine validita' (default NULL)
    --
    -- Restituisce:
    --   auth_user.id dell'utente creato
    --
    -- Nota indirizzo:
    --   Questo orchestratore NON crea indirizzo. Se la
    --   matrice config.tipi_soggetto_dettaglio_tipi_indirizzo
    --   richiede RES per PR, il chiamante deve creare
    --   l'indirizzo prima del COMMIT (trigger DEFERRED).
    --
    -- Building block chiamati:
    --   anagrafiche.fn_crea_auth_user
    --   anagrafiche.fn_crea_soggetto_pf
    --   anagrafiche.fn_crea_risorsa_umana
    --     (che chiama script.fn_get_or_create_soggetto_ruolo)
    -- =========================================================

    -- =============================================================
    -- Validazione coerenza parametri orchestratore
    -- I guard di dettaglio sono nei building block.
    -- Qui validiamo solo che i parametri obbligatori
    -- dell'orchestratore siano presenti.
    -- =============================================================

    IF p_cognome IS NULL OR TRIM(p_cognome) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_cognome'),
            NULL::uuid, 'Cognome obbligatorio.'
        );
    END IF;

    IF p_nome IS NULL OR TRIM(p_nome) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_nome'),
            NULL::uuid, 'Nome obbligatorio.'
        );
    END IF;

    IF p_codice_fiscale IS NULL OR TRIM(p_codice_fiscale) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_codice_fiscale'),
            NULL::uuid,
            'Codice fiscale obbligatorio (richiesto da guard persona fisica).'
        );
    END IF;

    IF p_username IS NULL OR TRIM(p_username) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_username'),
            NULL::uuid, 'Username obbligatorio.'
        );
    END IF;

    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_email'),
            NULL::uuid, 'Email obbligatoria.'
        );
    END IF;

    IF p_password_hash IS NULL OR LENGTH(p_password_hash) = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_password_hash'),
            NULL::uuid, 'Password hash obbligatorio.'
        );
    END IF;

    IF p_qualifica_id IS NULL OR p_qualifica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_qualifica_id'),
            NULL::uuid, 'Qualifica obbligatoria.'
        );
    END IF;

    -- =============================================================
    -- Step 1: Creazione auth_user (Django)
    -- Guard unicita' username/email nel building block.
    -- =============================================================

    SELECT anagrafiche.fn_crea_auth_user(
        p_username      := p_username,
        p_email         := p_email,
        p_password_hash := p_password_hash,
        p_first_name    := p_nome,
        p_last_name     := p_cognome
    ) INTO v_auth_user_id;

    -- =============================================================
    -- Step 2: Creazione soggetto PF + contatto default
    -- Guard CF univoco e lookup config nel building block.
    -- =============================================================

    SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome        := p_cognome,
        p_nome           := p_nome,
        p_codice_fiscale := p_codice_fiscale,
        p_email          := p_email,
        p_data_nascita   := p_data_nascita,
        p_sesso          := p_sesso
    ) INTO v_soggetto_id;

    -- =============================================================
    -- Step 3: Creazione risorsa umana + bridge auth_user
    -- fn_crea_risorsa_umana chiama internamente
    -- fn_get_or_create_soggetto_ruolo('RIS_UMANA').
    -- Se p_auth_user_id fornito, crea bridge con trigger
    -- guard PF e sync is_active.
    -- =============================================================

    SELECT anagrafiche.fn_crea_risorsa_umana(
        p_soggetto_id            := v_soggetto_id,
        p_qualifica_id           := p_qualifica_id,
        p_unita_organizzativa_id := p_unita_organizzativa_id,
        p_valido_dal             := p_valido_dal,
        p_valido_al              := p_valido_al,
        p_auth_user_id           := v_auth_user_id,
        p_ruolo_sistema          := p_ruolo_sistema
    ) INTO v_ru_id;

    RETURN v_auth_user_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_operatore(p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_ruolo_sistema config.ruolo_sistema, p_valido_dal date, p_valido_al date)
IS 'Orchestratore transazionale creazione operatore. Chiama: fn_crea_auth_user, fn_crea_soggetto_pf, fn_crea_risorsa_umana (con bridge). Obbligatori: p_cognome, p_nome, p_codice_fiscale, p_username, p_email, p_password_hash, p_qualifica_id (DEFAULT NULL, guard nel body). NON crea indirizzo (DEFERRED). Rollback automatico.';
```

---
{% include-markdown "signature-core.md" %}
