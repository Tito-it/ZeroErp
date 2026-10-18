{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_soggetto_pf.md" %}
# ⚙️ Funzione `fn_crea_soggetto_pf`

```sql
CREATE FUNCTION fn_crea_soggetto_pf(p_cognome text, p_nome text, p_codice_fiscale text, p_email character varying, p_data_nascita date, p_sesso character, p_stato_iso2 character, p_comune_nascita_id integer, p_tipo_contatto_id integer, p_tipo_soggetto_dettaglio_id bigint, p_partita_iva text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_soggetto_pf(p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_email character varying DEFAULT NULL::character varying, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT NULL::bpchar, p_stato_iso2 character DEFAULT NULL::bpchar, p_comune_nascita_id integer DEFAULT NULL::integer, p_tipo_contatto_id integer DEFAULT NULL::integer, p_tipo_soggetto_dettaglio_id bigint DEFAULT NULL::bigint, p_partita_iva text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: crea un soggetto PERSONA FISICA (natura base PF: privato PR o
--   ditta individuale DI) + il contatto di default. NON crea indirizzi.
-- ⭐ Rev 20261009-26 (brief-db-sesso-senza-default):
--   - la natura di dettaglio la sceglie il chiamante
--     (p_tipo_soggetto_dettaglio_id, obbligatorio): prima era PR cablato, e
--     una ditta individuale scelta nel form nasceva privato, senza P.IVA;
--   - p_partita_iva: per la DI la pretende gia'
--     trgfn_soggetti_guard_cf_piva_obbligatori;
--   - il sesso passa cosi' com'e': via il COALESCE(p_sesso, 'M'). Se serve
--     lo decide la natura (sesso_policy), nel guard
--     trgfn_soggetti_guard_sesso_policy: una sede sola per la regola.
-- =========================================================
DECLARE
    v_tipo_soggetto_id            config.tipi_soggetto_dettaglio.tipo_soggetto_id%TYPE;
    v_descrizione_dettaglio       config.tipi_soggetto_dettaglio.descrizione%TYPE;
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

    -- Natura di dettaglio: obbligatoria, e di natura base PF
    IF p_tipo_soggetto_dettaglio_id IS NULL OR p_tipo_soggetto_dettaglio_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_tipo_soggetto_dettaglio_id'),
            NULL::uuid, 'Tipo soggetto obbligatorio.'
        );
    END IF;

    SELECT tsd.tipo_soggetto_id, tsd.descrizione
      INTO v_tipo_soggetto_id, v_descrizione_dettaglio
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = p_tipo_soggetto_dettaglio_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_tipo_soggetto_dettaglio_id',
                               'p_tipo_soggetto_dettaglio_id', p_tipo_soggetto_dettaglio_id),
            NULL::uuid,
            concat('Tipo soggetto dettaglio id=', p_tipo_soggetto_dettaglio_id, ' non trovato.')
        );
    END IF;

    -- ⛔ Una societa' o un ente qui e' un chiamante che ha sbagliato porta
    --   (la porta giusta e' fn_crea_soggetto_pg): TECNICO, non un dato del form.
    IF v_tipo_soggetto_id <> 'PF' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_soggetto_pf',
            'E_SOGGETTO_CREAZIONE_NATURA_ERRATA',
            jsonb_build_object('tipo_soggetto_dettaglio_id', p_tipo_soggetto_dettaglio_id,
                               'tipo_soggetto_id',           v_tipo_soggetto_id),
            NULL::uuid,
            COALESCE(v_descrizione_dettaglio, p_tipo_soggetto_dettaglio_id::text),
            v_tipo_soggetto_id
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
    -- Il sesso passa com'e': se la natura lo pretende e manca, lo rifiuta
    --   trgfn_soggetti_guard_sesso_policy (E_SESSO_OBBLIGATORIO, campo sesso).
    INSERT INTO anagrafiche.soggetti (
        cognome, nome, codice_fiscale, partita_iva, data_nascita, sesso,
        stato_id, tipo_soggetto_dettaglio_id, comune_id, attivo
    )
    VALUES (
        TRIM(p_cognome), TRIM(p_nome),
        UPPER(TRIM(p_codice_fiscale)),
        NULLIF(UPPER(TRIM(p_partita_iva)), ''),
        p_data_nascita, p_sesso,
        v_stato_id, p_tipo_soggetto_dettaglio_id,
        p_comune_nascita_id, true
    )
    RETURNING id INTO v_soggetto_id;

    -- Step 2: Creazione contatto default con tipo_contatto_id
    --         (BB anagrafiche.fn_crea_contatto, rev 2026-10-17)
    PERFORM anagrafiche.fn_crea_contatto(
        v_soggetto_id, NULL,
        jsonb_build_object('tipo_contatto_id', v_tipo_contatto_id,
                           'nominativo',       TRIM(p_cognome) || ' ' || TRIM(p_nome),
                           'email',            TRIM(p_email),
                           'is_default',       true));

    RETURN v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_soggetto_pf(p_cognome text, p_nome text, p_codice_fiscale text, p_email character varying, p_data_nascita date, p_sesso character, p_stato_iso2 character, p_comune_nascita_id integer, p_tipo_contatto_id integer, p_tipo_soggetto_dettaglio_id bigint, p_partita_iva text)
IS 'Crea un soggetto PERSONA FISICA (natura base PF: privato PR o ditta individuale DI, scelta dal chiamante con p_tipo_soggetto_dettaglio_id, obbligatorio) + contatto default con tipo_contatto_id. Una natura che non e'' PF si rifiuta con E_SOGGETTO_CREAZIONE_NATURA_ERRATA (porta giusta: fn_crea_soggetto_pg). p_partita_iva per la DI (la pretende il guard su CF e P.IVA). Il sesso passa com''e'', senza default: quando serve lo decide config.tipi_soggetto_dettaglio.sesso_policy nel guard trgfn_soggetti_guard_sesso_policy (PR obbligatorio, DI facoltativo). Fallback tipo contatto: primo da config.tipi_contatti. Default stato_iso2 da config.parameters. Guard CF univoco. NON crea indirizzo. Rev 20261009-26, brief-db-sesso-senza-default. Rev 2026-10-17: il contatto lo scrive il BB anagrafiche.fn_crea_contatto (regola del 2, brief-db-processi-accensione-per-ambiente 2b-1 lotto 3); comportamento invariato.';
```

---
{% include-markdown "signature-core.md" %}
