{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_operatore_v2.md" %}
# ⚙️ Funzione `fn_crea_operatore_v2`

```sql
CREATE FUNCTION fn_crea_operatore_v2(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_attivo boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_operatore_v2(p_soggetto_id uuid DEFAULT NULL::uuid, p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_username text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_password_hash text DEFAULT NULL::text, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT 'M'::bpchar, p_is_super_admin boolean DEFAULT false, p_attivo boolean DEFAULT true, p_valido_dal date DEFAULT CURRENT_DATE, p_valido_al date DEFAULT NULL::date, p_comune_nascita_id integer DEFAULT NULL::integer, p_indirizzo_resid_dettaglio_id bigint DEFAULT NULL::bigint, p_indirizzo_domfisc_dettaglio_id bigint DEFAULT NULL::bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_auth_user_id     integer;
    v_soggetto_id      anagrafiche.soggetti.id%TYPE;
    v_ru_id            anagrafiche.risorse_umane.id%TYPE;
    v_tipo_soggetto_id config.tipi_soggetto_dettaglio.tipo_soggetto_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo (v2 multi-face native, Chunk A Fase 7 2026-04-29):
    --   Orchestratore creazione operatore.
    --   Due flussi (A: soggetto nuovo / B: soggetto esistente)
    --   identici a v1; cambia solo la firma capability +
    --   l'invocazione di fn_crea_risorsa_umana_v2.
    -- =========================================================

    -- ============ Guard comuni ============
    IF p_username IS NULL OR TRIM(p_username) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_username'),
            NULL::uuid, 'Username obbligatorio.'
        );
    END IF;

    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_email'),
            NULL::uuid, 'Email obbligatoria.'
        );
    END IF;

    IF p_password_hash IS NULL OR LENGTH(p_password_hash) = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_password_hash'),
            NULL::uuid, 'Password hash obbligatorio.'
        );
    END IF;

    IF p_qualifica_id IS NULL OR p_qualifica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_qualifica_id'),
            NULL::uuid, 'Qualifica obbligatoria.'
        );
    END IF;

    -- ============ Step 1: auth_user Django ============
    SELECT anagrafiche.fn_crea_auth_user(
        p_username      := p_username,
        p_email         := p_email,
        p_password_hash := p_password_hash,
        p_first_name    := COALESCE(p_nome, ''),
        p_last_name     := COALESCE(p_cognome, '')
    ) INTO v_auth_user_id;

    -- ============ Step 2: Soggetto (flusso A o B) ============
    IF p_soggetto_id IS NOT NULL THEN
        -- Flusso B: soggetto esistente
        SELECT tsd.tipo_soggetto_id
          INTO v_tipo_soggetto_id
          FROM anagrafiche.soggetti s
          JOIN config.tipi_soggetto_dettaglio tsd
            ON tsd.id = s.tipo_soggetto_dettaglio_id
         WHERE s.id = p_soggetto_id;

        IF v_tipo_soggetto_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('p_soggetto_id', p_soggetto_id),
                NULL::uuid,
                'Soggetto con id=' || p_soggetto_id || ' non trovato.'
            );
        END IF;

        IF v_tipo_soggetto_id <> 'PF' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('p_soggetto_id', p_soggetto_id,
                                  'tipo_soggetto_id', v_tipo_soggetto_id),
                NULL::uuid,
                'Soggetto deve essere Persona Fisica (PF). Trovato: ' || v_tipo_soggetto_id || '.'
            );
        END IF;

        v_soggetto_id := p_soggetto_id;

    ELSE
        -- Flusso A: crea soggetto PF nuovo
        IF p_cognome IS NULL OR TRIM(p_cognome) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_cognome'),
                NULL::uuid, 'Cognome obbligatorio per creazione soggetto nuovo.'
            );
        END IF;

        IF p_nome IS NULL OR TRIM(p_nome) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_nome'),
                NULL::uuid, 'Nome obbligatorio per creazione soggetto nuovo.'
            );
        END IF;

        IF p_codice_fiscale IS NULL OR TRIM(p_codice_fiscale) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
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

    -- ============ Step 3: risorsa_umana via v2 ============
    -- Differenza chiave vs fn_crea_operatore v1:
    -- chiama fn_crea_risorsa_umana_v2 con firma capability
    -- (p_is_super_admin/p_attivo) anziche' p_ruolo_sistema.
    SELECT anagrafiche.fn_crea_risorsa_umana_v2(
        p_soggetto_id            := v_soggetto_id,
        p_qualifica_id           := p_qualifica_id,
        p_unita_organizzativa_id := p_unita_organizzativa_id,
        p_valido_dal             := p_valido_dal,
        p_valido_al              := p_valido_al,
        p_auth_user_id           := v_auth_user_id,
        p_is_super_admin         := p_is_super_admin,
        p_attivo                 := p_attivo
    ) INTO v_ru_id;

    -- ============ Step 4: indirizzi soggetto (invariato) ============
    IF p_indirizzo_resid_dettaglio_id IS NOT NULL THEN
        PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
            p_soggetto_id            := v_soggetto_id,
            p_tipo_indirizzo_codice  := 'RES',
            p_indirizzo_dettaglio_id := p_indirizzo_resid_dettaglio_id
        );

        PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
            p_soggetto_id            := v_soggetto_id,
            p_tipo_indirizzo_codice  := 'DOMFISC',
            p_indirizzo_dettaglio_id := COALESCE(
                p_indirizzo_domfisc_dettaglio_id,
                p_indirizzo_resid_dettaglio_id
            )
        );
    END IF;

    RETURN v_auth_user_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_operatore_v2(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_attivo boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint)
IS 'Orchestratore creazione operatore - v2 multi-face native (Chunk A Fase 7 2026-04-29). Sostituisce v1 (p_ruolo_sistema config.ruolo_sistema) con p_is_super_admin/p_attivo. Body invariato; chiama fn_crea_risorsa_umana_v2 invece di fn_crea_risorsa_umana. v1 droppata in Chunk B post BE migrato.';
```

---
{% include-markdown "signature-core.md" %}
