{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_operatore.md" %}
# ⚙️ Funzione `fn_crea_operatore`

```sql
CREATE FUNCTION fn_crea_operatore(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_ruolo_sistema config.ruolo_sistema, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_operatore(p_soggetto_id uuid DEFAULT NULL::uuid, p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_username text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_password_hash text DEFAULT NULL::text, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT 'M'::bpchar, p_ruolo_sistema config.ruolo_sistema DEFAULT 'OPERATIVO'::config.ruolo_sistema, p_valido_dal date DEFAULT CURRENT_DATE, p_valido_al date DEFAULT NULL::date, p_comune_nascita_id integer DEFAULT NULL::integer, p_indirizzo_resid_dettaglio_id bigint DEFAULT NULL::bigint, p_indirizzo_domfisc_dettaglio_id bigint DEFAULT NULL::bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_auth_user_id       integer;
    v_soggetto_id        anagrafiche.soggetti.id%TYPE;
    v_ru_id              anagrafiche.risorse_umane.id%TYPE;
    v_tipo_soggetto_id   config.tipi_soggetto_dettaglio.tipo_soggetto_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Orchestratore transazionale per creazione operatore.
    --   Due flussi:
    --     A) p_soggetto_id NULL: crea soggetto PF nuovo
    --     B) p_soggetto_id valorizzato: associa soggetto esistente
    --   In entrambi i flussi:
    --     1. fn_crea_auth_user   -> crea utente Django
    --     2. fn_crea_risorsa_umana -> crea RU + bridge auth_user
    --     3. fn_crea_indirizzo_soggetto -> RESID + DOMFISC
    --        (se p_indirizzo_resid_dettaglio_id fornito)
    --
    -- Parametri obbligatori (sempre):
    --   p_username, p_email, p_password_hash, p_qualifica_id
    --
    -- Parametri obbligatori (solo flusso A):
    --   p_cognome, p_nome, p_codice_fiscale
    --
    -- Restituisce:
    --   auth_user.id dell'utente creato
    -- =========================================================

    -- =============================================================
    -- Guard comuni (entrambi i flussi)
    -- =============================================================

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
    -- =============================================================

    SELECT anagrafiche.fn_crea_auth_user(
        p_username      := p_username,
        p_email         := p_email,
        p_password_hash := p_password_hash,
        p_first_name    := COALESCE(p_nome, ''),
        p_last_name     := COALESCE(p_cognome, '')
    ) INTO v_auth_user_id;

    -- =============================================================
    -- Step 2: Soggetto — biforcazione flusso A / flusso B
    -- =============================================================

    IF p_soggetto_id IS NOT NULL THEN
        -- ---------------------------------------------------------
        -- Flusso B: soggetto esistente
        -- ---------------------------------------------------------

        -- Guard: soggetto deve esistere
        SELECT tsd.tipo_soggetto_id
          INTO v_tipo_soggetto_id
          FROM anagrafiche.soggetti s
          JOIN config.tipi_soggetto_dettaglio tsd
            ON tsd.id = s.tipo_soggetto_dettaglio_id
         WHERE s.id = p_soggetto_id;

        IF v_tipo_soggetto_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('p_soggetto_id', p_soggetto_id),
                NULL::uuid,
                'Soggetto con id=' || p_soggetto_id || ' non trovato.'
            );
        END IF;

        -- Guard: natura deve essere PF (persona fisica)
        IF v_tipo_soggetto_id <> 'PF' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('p_soggetto_id', p_soggetto_id,
                                  'tipo_soggetto_id', v_tipo_soggetto_id),
                NULL::uuid,
                'Soggetto deve essere Persona Fisica (PF). Trovato: ' || v_tipo_soggetto_id || '.'
            );
        END IF;

        v_soggetto_id := p_soggetto_id;

    ELSE
        -- ---------------------------------------------------------
        -- Flusso A: crea soggetto PF nuovo
        -- ---------------------------------------------------------

        -- Guard flusso A: dati soggetto obbligatori
        IF p_cognome IS NULL OR TRIM(p_cognome) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_cognome'),
                NULL::uuid, 'Cognome obbligatorio per creazione soggetto nuovo.'
            );
        END IF;

        IF p_nome IS NULL OR TRIM(p_nome) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_nome'),
                NULL::uuid, 'Nome obbligatorio per creazione soggetto nuovo.'
            );
        END IF;

        IF p_codice_fiscale IS NULL OR TRIM(p_codice_fiscale) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_codice_fiscale'),
                NULL::uuid,
                'Codice fiscale obbligatorio per creazione soggetto nuovo.'
            );
        END IF;

        SELECT anagrafiche.fn_crea_soggetto_pf(
            p_cognome           := p_cognome,
            p_nome              := p_nome,
            p_codice_fiscale    := p_codice_fiscale,
            p_email             := p_email,
            p_data_nascita      := p_data_nascita,
            p_sesso             := p_sesso,
            p_comune_nascita_id := p_comune_nascita_id
        ) INTO v_soggetto_id;

    END IF;

    -- =============================================================
    -- Step 3: Creazione risorsa umana + bridge auth_user
    -- fn_get_or_create_soggetto_ruolo gestisce l'upsert del
    -- ruolo RIS_UMANA internamente.
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

    -- =============================================================
    -- Step 4: Creazione indirizzi soggetto
    -- Se p_indirizzo_resid_dettaglio_id fornito:
    --   a) Crea indirizzo RESID
    --   b) Crea indirizzo DOMFISC (se NULL, usa stesso di RESID)
    -- Se NULL: nessun indirizzo creato. Il trigger DEFERRED
    -- trgfn_soggetti_guard_indirizzi_required puo' bloccare
    -- al COMMIT se la matrice richiede RESID per PR.
    -- =============================================================

    IF p_indirizzo_resid_dettaglio_id IS NOT NULL THEN
        PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
            p_soggetto_id            := v_soggetto_id,
            p_tipo_indirizzo_codice  := 'RES',
            p_indirizzo_dettaglio_id := p_indirizzo_resid_dettaglio_id
        );

        PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
            p_soggetto_id            := v_soggetto_id,
            p_tipo_indirizzo_codice  := 'DOMFISC',
            p_indirizzo_dettaglio_id := COALESCE(p_indirizzo_domfisc_dettaglio_id, p_indirizzo_resid_dettaglio_id)
        );
    END IF;

    RETURN v_auth_user_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_operatore(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_ruolo_sistema config.ruolo_sistema, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint)
IS 'Orchestratore transazionale creazione operatore. Due flussi: A) p_soggetto_id NULL → crea soggetto PF nuovo via fn_crea_soggetto_pf; B) p_soggetto_id valorizzato → associa soggetto PF esistente (guard natura PF). In entrambi: fn_crea_auth_user, fn_crea_risorsa_umana (con bridge), fn_crea_indirizzo_soggetto (RESID + DOMFISC se forniti).';
```

---
{% include-markdown "signature-core.md" %}
