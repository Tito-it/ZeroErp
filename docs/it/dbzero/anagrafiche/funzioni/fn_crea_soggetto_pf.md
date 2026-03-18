{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_soggetto_pf.md" %}
# ⚙️ Funzione `fn_crea_soggetto_pf`

```sql
CREATE FUNCTION fn_crea_soggetto_pf(p_cognome text, p_nome text, p_codice_fiscale text, p_email text, p_data_nascita date, p_sesso character, p_stato_iso2 character, p_comune_nascita_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_soggetto_pf(p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT NULL::bpchar, p_stato_iso2 character DEFAULT NULL::bpchar, p_comune_nascita_id integer DEFAULT NULL::integer)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Lookup config
    v_tipo_soggetto_dettaglio_id  config.tipi_soggetto_dettaglio.id%TYPE;
    v_stato_id                    config.stati.id%TYPE;
    v_stato_iso2_resolved         config.stati.codice_iso2%TYPE;
    -- Risultato
    v_soggetto_id                 anagrafiche.soggetti.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Crea un soggetto Persona Fisica (natura PR = Privato)
    --   con contatto default. Non crea indirizzo: il
    --   chiamante e' responsabile se la matrice config
    --   richiede RES per la natura PR.
    --
    -- Parametri obbligatori:
    --   p_cognome:        cognome
    --   p_nome:           nome
    --   p_codice_fiscale: CF (guard PF lo richiede)
    --   p_email:          email (usata per contatto default)
    --
    -- Parametri opzionali:
    --   p_data_nascita:      data nascita (default NULL)
    --   p_sesso:             sesso (default da parametro o 'M')
    --   p_stato_iso2:        ISO2 nazionalita' (default da
    --                        config.parameters soggetto_default_stato_iso2)
    --   p_comune_nascita_id: comune di nascita (default NULL)
    --
    -- Defaults risolti internamente:
    --   p_stato_iso2 -> config.parameters.soggetto_default_stato_iso2
    --   p_sesso      -> 'M' (hardcode accettabile, non e' config)
    -- =========================================================

    -- =============================================================
    -- Validazione parametri obbligatori
    -- =============================================================

    IF p_cognome IS NULL OR TRIM(p_cognome) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_cognome'),
            NULL::uuid, 'Cognome obbligatorio.'
        );
    END IF;

    IF p_nome IS NULL OR TRIM(p_nome) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_nome'),
            NULL::uuid, 'Nome obbligatorio.'
        );
    END IF;

    IF p_codice_fiscale IS NULL OR TRIM(p_codice_fiscale) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_codice_fiscale'),
            NULL::uuid,
            'Codice fiscale obbligatorio (richiesto da guard persona fisica).'
        );
    END IF;

    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_email'),
            NULL::uuid, 'Email obbligatoria (usata per contatto default).'
        );
    END IF;

    -- =============================================================
    -- Lookup config (no ID hardcoded)
    -- =============================================================

    -- Natura: PR = Privato (Persona Fisica senza P.IVA)
    SELECT id INTO v_tipo_soggetto_dettaglio_id
    FROM config.tipi_soggetto_dettaglio
    WHERE codice_interno = 'PR';

    IF v_tipo_soggetto_dettaglio_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_GENERICO',
            jsonb_build_object('codice_interno', 'PR'),
            NULL::uuid,
            'Tipo soggetto dettaglio PR non trovato in config.tipi_soggetto_dettaglio.'
        );
    END IF;

    -- Stato (nazionalita') — default da config.parameters
    v_stato_iso2_resolved := COALESCE(
        p_stato_iso2,
        (SELECT default_value FROM config.parameters
          WHERE code = 'soggetto_default_stato_iso2'),
        'IT'  -- fallback ultimo livello se parametro mancante
    );

    SELECT id INTO v_stato_id
    FROM config.stati
    WHERE codice_iso2 = v_stato_iso2_resolved;

    IF v_stato_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_GENERICO',
            jsonb_build_object('codice_iso2', v_stato_iso2_resolved),
            NULL::uuid,
            concat('Stato ', v_stato_iso2_resolved, ' non trovato in config.stati.')
        );
    END IF;

    -- =============================================================
    -- Guard unicita' CF
    -- =============================================================

    IF EXISTS (
        SELECT 1 FROM anagrafiche.soggetti
         WHERE stato_id = v_stato_id
           AND id_fiscale_univoco_cf_piva = UPPER(TRIM(p_codice_fiscale))
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_ADMIN_CF_DUPLICATO',
            jsonb_build_object('codice_fiscale', p_codice_fiscale),
            NULL::uuid, 'Codice fiscale gia'' presente in anagrafica.'
        );
    END IF;

    -- =============================================================
    -- Step 1: Creazione soggetto (Persona Fisica)
    -- =============================================================

    INSERT INTO anagrafiche.soggetti (
        cognome, nome, codice_fiscale, data_nascita, sesso,
        stato_id, tipo_soggetto_dettaglio_id, comune_id, attivo
    )
    VALUES (
        TRIM(p_cognome), TRIM(p_nome),
        UPPER(TRIM(p_codice_fiscale)),
        p_data_nascita, COALESCE(p_sesso, 'M'),
        v_stato_id, v_tipo_soggetto_dettaglio_id,
        p_comune_nascita_id, true
    )
    RETURNING id INTO v_soggetto_id;

    -- =============================================================
    -- Step 2: Creazione contatto default
    -- =============================================================

    INSERT INTO anagrafiche.contatti (
        soggetto_id, nominativo, email, is_default
    )
    VALUES (
        v_soggetto_id,
        TRIM(p_cognome) || ' ' || TRIM(p_nome),
        TRIM(p_email),
        true
    );

    RETURN v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_soggetto_pf(p_cognome text, p_nome text, p_codice_fiscale text, p_email text, p_data_nascita date, p_sesso character, p_stato_iso2 character, p_comune_nascita_id integer)
IS 'Building block: crea soggetto Persona Fisica (natura PR) + contatto default. Default stato_iso2 da config.parameters (soggetto_default_stato_iso2). Guard CF univoco. NON crea indirizzo (responsabilita'' del chiamante). Riusabile da orchestratori.';
```

---
{% include-markdown "signature-core.md" %}
