{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_soggetto_pf.md" %}
# ⚙️ Funzione `fn_crea_soggetto_pf`

```sql
CREATE FUNCTION fn_crea_soggetto_pf(p_cognome text, p_nome text, p_codice_fiscale text, p_email character varying, p_data_nascita date, p_sesso character, p_stato_iso2 character, p_comune_nascita_id integer, p_tipo_contatto_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_soggetto_pf(p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_email character varying DEFAULT NULL::character varying, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT NULL::bpchar, p_stato_iso2 character DEFAULT NULL::bpchar, p_comune_nascita_id integer DEFAULT NULL::integer, p_tipo_contatto_id integer DEFAULT NULL::integer)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_soggetto_dettaglio_id  config.tipi_soggetto_dettaglio.id%TYPE;
    v_stato_id                    config.stati.id%TYPE;
    v_stato_iso2_resolved         config.stati.codice_iso2%TYPE;
    v_tipo_contatto_id            config.tipi_contatti.id%TYPE;
    v_soggetto_id                 anagrafiche.soggetti.id%TYPE;
BEGIN
    -- Validazione parametri obbligatori
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
            NULL::uuid, 'Codice fiscale obbligatorio.'
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

    -- Tipo contatto: fallback al primo dalla tabella se non fornito
    v_tipo_contatto_id := COALESCE(
        p_tipo_contatto_id,
        (SELECT id FROM config.tipi_contatti ORDER BY id LIMIT 1)
    );

    IF v_tipo_contatto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_tipo_contatto_id'),
            NULL::uuid,
            'Tipo contatto obbligatorio e nessun tipo contatto trovato in config.tipi_contatti.'
        );
    END IF;

    -- Lookup tipo soggetto dettaglio (Persona Fisica — natura PR)
    SELECT tsd.id INTO v_tipo_soggetto_dettaglio_id
    FROM config.tipi_soggetto_dettaglio tsd
    WHERE tsd.codice_interno = 'PR';

    IF v_tipo_soggetto_dettaglio_id IS NULL THEN
        -- Fix: E_GENERICO → E_CODICE
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_CODICE',
            jsonb_build_object('codice_interno', 'PR'),
            NULL::uuid,
            'PR', 'config.tipi_soggetto_dettaglio'
        );
    END IF;

    -- Stato (nazionalita) — default da config.parameters
    v_stato_iso2_resolved := COALESCE(
        p_stato_iso2,
        (SELECT default_value FROM config.parameters
          WHERE code = 'soggetto_default_stato_iso2'),
        'IT'
    );

    SELECT id INTO v_stato_id
    FROM config.stati
    WHERE codice_iso2 = v_stato_iso2_resolved;

    IF v_stato_id IS NULL THEN
        -- Fix: E_GENERICO → E_CODICE
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_CODICE',
            jsonb_build_object('codice_iso2', v_stato_iso2_resolved),
            NULL::uuid,
            v_stato_iso2_resolved, 'config.stati'
        );
    END IF;

    -- Guard unicita CF per stato
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

    -- Step 1: Creazione soggetto (Persona Fisica)
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

    -- Step 2: Creazione contatto default con tipo_contatto_id
    INSERT INTO anagrafiche.contatti (
        soggetto_id, tipo_contatto_id, nominativo, email, is_default
    )
    VALUES (
        v_soggetto_id,
        v_tipo_contatto_id,
        TRIM(p_cognome) || ' ' || TRIM(p_nome),
        TRIM(p_email),
        true
    );

    RETURN v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_soggetto_pf(p_cognome text, p_nome text, p_codice_fiscale text, p_email character varying, p_data_nascita date, p_sesso character, p_stato_iso2 character, p_comune_nascita_id integer, p_tipo_contatto_id integer)
IS 'Crea soggetto PF (natura PR) + contatto default con tipo_contatto_id. Fallback tipo contatto: primo da config.tipi_contatti. Default stato_iso2 da config.parameters. Guard CF univoco. NON crea indirizzo.';
```

---
{% include-markdown "signature-core.md" %}
