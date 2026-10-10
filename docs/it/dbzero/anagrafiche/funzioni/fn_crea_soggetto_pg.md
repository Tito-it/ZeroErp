{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_soggetto_pg.md" %}
# ⚙️ Funzione `fn_crea_soggetto_pg`

```sql
CREATE FUNCTION fn_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id bigint, p_email character varying, p_codice_fiscale text, p_partita_iva text, p_stato_iso2 character, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_tipo_contatto_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id bigint, p_email character varying, p_codice_fiscale text DEFAULT NULL::text, p_partita_iva text DEFAULT NULL::text, p_stato_iso2 character DEFAULT NULL::bpchar, p_forma_giuridica_id bigint DEFAULT NULL::bigint, p_id_prov_iscri_rea integer DEFAULT NULL::integer, p_iscrizione_rea character varying DEFAULT NULL::character varying, p_capitale_sociale numeric DEFAULT NULL::numeric, p_socio_unico anagrafiche.socio_unico_enum DEFAULT NULL::anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum DEFAULT NULL::anagrafiche.liquidazione_enum, p_destinatario_fe character varying DEFAULT NULL::character varying, p_pec_fatturazione character varying DEFAULT NULL::character varying, p_codice_sdi character varying DEFAULT NULL::character varying, p_tipo_contatto_id integer DEFAULT NULL::integer)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- ⭐ Rev 20261009-28 (brief-db-sesso-senza-default): una natura base PF
--   (privato, ditta individuale) qui si rifiuta. La persona fisica ha la sua
--   porta, fn_crea_soggetto_pf, che ne riceve nome, cognome e sesso: da qui
--   una ditta individuale nasceva con la sola ragione sociale.
DECLARE
    v_tipo_soggetto_id            config.tipi_soggetto_dettaglio.tipo_soggetto_id%TYPE;
    v_descrizione_dettaglio       config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_stato_id                    config.stati.id%TYPE;
    v_stato_iso2_resolved         config.stati.codice_iso2%TYPE;
    v_dati_societari_policy       config.tipi_soggetto_dettaglio.dati_societari_policy%TYPE;
    v_socio_unico_resolved        anagrafiche.dati_societari.socio_unico%TYPE;
    v_liquidazione_resolved       anagrafiche.dati_societari.liquidazione%TYPE;
    v_tipo_contatto_id            config.tipi_contatti.id%TYPE;
    v_soggetto_id                 anagrafiche.soggetti.id%TYPE;
BEGIN
    -- Validazione parametri obbligatori
    IF p_ragione_sociale IS NULL OR TRIM(p_ragione_sociale) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pg',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_ragione_sociale'),
            NULL::uuid, 'Ragione sociale obbligatoria.'
        );
    END IF;

    IF p_tipo_soggetto_dettaglio_id IS NULL OR p_tipo_soggetto_dettaglio_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pg',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_tipo_soggetto_dettaglio_id'),
            NULL::uuid, 'Tipo soggetto dettaglio obbligatorio e > 0.'
        );
    END IF;

    -- Verifica che il tipo soggetto esista e recupera policy dati societari
    SELECT tsd.dati_societari_policy, tsd.tipo_soggetto_id, tsd.descrizione
      INTO v_dati_societari_policy, v_tipo_soggetto_id, v_descrizione_dettaglio
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = p_tipo_soggetto_dettaglio_id;

    IF v_dati_societari_policy IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pg',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_tipo_soggetto_dettaglio_id', p_tipo_soggetto_dettaglio_id),
            NULL::uuid,
            concat('Tipo soggetto dettaglio id=', p_tipo_soggetto_dettaglio_id, ' non trovato.')
        );
    END IF;

    -- ⛔ Rev 20261009-28: una persona fisica qui e' un chiamante che ha
    --   sbagliato porta (TECNICO, non un dato del form).
    IF v_tipo_soggetto_id = 'PF' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pg',
            'E_SOGGETTO_CREAZIONE_NATURA_ERRATA',
            jsonb_build_object('tipo_soggetto_dettaglio_id', p_tipo_soggetto_dettaglio_id,
                               'tipo_soggetto_id',           v_tipo_soggetto_id),
            NULL::uuid,
            COALESCE(v_descrizione_dettaglio, p_tipo_soggetto_dettaglio_id::text),
            v_tipo_soggetto_id
        );
    END IF;

    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pg',
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
            'database', 'anagrafiche.fn_crea_soggetto_pg',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_tipo_contatto_id'),
            NULL::uuid,
            'Tipo contatto obbligatorio e nessun tipo contatto trovato in config.tipi_contatti.'
        );
    END IF;

    -- Risoluzione default da config.parameters
    -- Stato (nazionalita)
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
            'database', 'anagrafiche.fn_crea_soggetto_pg',
            'E_CODICE',
            jsonb_build_object('codice_iso2', v_stato_iso2_resolved),
            NULL::uuid,
            v_stato_iso2_resolved, 'config.stati'
        );
    END IF;

    -- Socio unico e liquidazione (default da config.parameters)
    v_socio_unico_resolved := COALESCE(
        p_socio_unico,
        (SELECT default_value FROM config.parameters
          WHERE code = 'dati_societari_default_socio_unico')::anagrafiche.socio_unico_enum,
        'SU'::anagrafiche.socio_unico_enum
    );

    v_liquidazione_resolved := COALESCE(
        p_liquidazione,
        (SELECT default_value FROM config.parameters
          WHERE code = 'dati_societari_default_liquidazione')::anagrafiche.liquidazione_enum,
        'LN'::anagrafiche.liquidazione_enum
    );

    -- Guard unicita CF/PIVA per stato (se forniti)
    IF p_codice_fiscale IS NOT NULL AND TRIM(p_codice_fiscale) <> '' THEN
        IF EXISTS (
            SELECT 1 FROM anagrafiche.soggetti
             WHERE stato_id = v_stato_id
               AND id_fiscale_univoco_cf_piva = UPPER(TRIM(p_codice_fiscale))
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_soggetto_pg',
                'E_ADMIN_CF_DUPLICATO',
                jsonb_build_object('codice_fiscale', p_codice_fiscale),
                NULL::uuid, 'Codice fiscale gia'' presente in anagrafica.'
            );
        END IF;
    END IF;

    IF p_partita_iva IS NOT NULL AND TRIM(p_partita_iva) <> '' THEN
        IF EXISTS (
            SELECT 1 FROM anagrafiche.soggetti
             WHERE stato_id = v_stato_id
               AND id_fiscale_univoco_cf_piva = UPPER(TRIM(p_partita_iva))
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_soggetto_pg',
                'E_ADMIN_PIVA_DUPLICATA',
                jsonb_build_object('partita_iva', p_partita_iva),
                NULL::uuid, 'Partita IVA gia'' presente in anagrafica.'
            );
        END IF;
    END IF;

    -- Step 1: Creazione soggetto (Persona Giuridica)
    INSERT INTO anagrafiche.soggetti (
        ragione_sociale, codice_fiscale, partita_iva,
        stato_id, tipo_soggetto_dettaglio_id, attivo
    )
    VALUES (
        TRIM(p_ragione_sociale),
        CASE WHEN p_codice_fiscale IS NOT NULL AND TRIM(p_codice_fiscale) <> ''
             THEN UPPER(TRIM(p_codice_fiscale))
             ELSE NULL
        END,
        CASE WHEN p_partita_iva IS NOT NULL AND TRIM(p_partita_iva) <> ''
             THEN UPPER(TRIM(p_partita_iva))
             ELSE NULL
        END,
        v_stato_id, p_tipo_soggetto_dettaglio_id, true
    )
    RETURNING id INTO v_soggetto_id;

    -- Step 2: Creazione contatto default con tipo_contatto_id
    INSERT INTO anagrafiche.contatti (
        soggetto_id, tipo_contatto_id, nominativo, email, is_default
    )
    VALUES (
        v_soggetto_id,
        v_tipo_contatto_id,
        TRIM(p_ragione_sociale),
        TRIM(p_email),
        true
    );

    -- Step 3: Creazione dati societari (se policy lo richiede
    --         o se almeno un campo DS e fornito con policy OPTIONAL)
    IF v_dati_societari_policy = 'REQUIRED'
       OR (v_dati_societari_policy = 'OPTIONAL' AND (
            p_id_prov_iscri_rea IS NOT NULL
            OR p_iscrizione_rea IS NOT NULL
            OR p_capitale_sociale IS NOT NULL
            OR p_forma_giuridica_id IS NOT NULL
            OR p_destinatario_fe IS NOT NULL
            OR p_pec_fatturazione IS NOT NULL
            OR p_codice_sdi IS NOT NULL
          ))
    THEN
        -- Guard campi NOT NULL di dati_societari
        IF p_id_prov_iscri_rea IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_soggetto_pg',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_id_prov_iscri_rea'),
                NULL::uuid,
                'Provincia iscrizione REA obbligatoria per dati societari.'
            );
        END IF;

        IF p_iscrizione_rea IS NULL OR TRIM(p_iscrizione_rea) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_soggetto_pg',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_iscrizione_rea'),
                NULL::uuid,
                'Iscrizione REA obbligatoria per dati societari.'
            );
        END IF;

        IF p_capitale_sociale IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_soggetto_pg',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_capitale_sociale'),
                NULL::uuid,
                'Capitale sociale obbligatorio per dati societari.'
            );
        END IF;

        IF p_destinatario_fe IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_soggetto_pg',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_destinatario_fe'),
                NULL::uuid,
                'Destinatario FE obbligatorio per dati societari (P=PEC, C=Codice SDI).'
            );
        END IF;

        INSERT INTO anagrafiche.dati_societari (
            soggetto_id, capitale_sociale,
            id_prov_iscri_rea, iscrizione_rea,
            socio_unico, liquidazione,
            destinatario_fe, pec_fatturazione, codice_sdi,
            forma_giuridica_id
        )
        VALUES (
            v_soggetto_id, p_capitale_sociale,
            p_id_prov_iscri_rea, TRIM(p_iscrizione_rea),
            v_socio_unico_resolved, v_liquidazione_resolved,
            p_destinatario_fe, TRIM(p_pec_fatturazione), TRIM(p_codice_sdi),
            p_forma_giuridica_id
        );
    END IF;

    RETURN v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id bigint, p_email character varying, p_codice_fiscale text, p_partita_iva text, p_stato_iso2 character, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_tipo_contatto_id integer)
IS 'Crea soggetto PG o ENC + contatto default con tipo_contatto_id + dati societari (se policy). Una natura base PF (privato, ditta individuale) si rifiuta con E_SOGGETTO_CREAZIONE_NATURA_ERRATA: la porta e'' fn_crea_soggetto_pf (rev 20261009-28, brief-db-sesso-senza-default). Il sesso non si scrive: per PG ed ENC e'' NULL (sesso_policy NONE). Fallback tipo contatto: primo da config.tipi_contatti. Default stato_iso2, socio_unico, liquidazione da config.parameters. NON crea indirizzi ne assegna ruoli.';
```

---
{% include-markdown "signature-core.md" %}
