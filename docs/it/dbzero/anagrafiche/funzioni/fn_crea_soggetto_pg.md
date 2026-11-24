{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_soggetto_pg.md" %}
# ⚙️ Funzione `fn_crea_soggetto_pg`

```sql
CREATE FUNCTION fn_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id bigint, p_email character varying, p_codice_fiscale text, p_partita_iva text, p_stato_iso2 character, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_tipo_contatto_id integer, p_data_costituzione date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id bigint, p_email character varying, p_codice_fiscale text DEFAULT NULL::text, p_partita_iva text DEFAULT NULL::text, p_stato_iso2 character DEFAULT NULL::bpchar, p_forma_giuridica_id bigint DEFAULT NULL::bigint, p_id_prov_iscri_rea integer DEFAULT NULL::integer, p_iscrizione_rea character varying DEFAULT NULL::character varying, p_capitale_sociale numeric DEFAULT NULL::numeric, p_socio_unico anagrafiche.socio_unico_enum DEFAULT NULL::anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum DEFAULT NULL::anagrafiche.liquidazione_enum, p_destinatario_fe character varying DEFAULT NULL::character varying, p_pec_fatturazione character varying DEFAULT NULL::character varying, p_codice_sdi character varying DEFAULT NULL::character varying, p_tipo_contatto_id integer DEFAULT NULL::integer, p_data_costituzione date DEFAULT NULL::date)
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
    v_tipo_contatto_id            config.tipi_contatti.id%TYPE;
    v_soggetto_id                 anagrafiche.soggetti.id%TYPE;
    v_vincolo                     pg_catalog.pg_constraint.conname%TYPE;
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

    -- Stato (nazionalita). Rev 2026-10-18 (D-1 di Tid): quello detto dal
    -- chiamante, cercato dal BB che rifiuta un codice con piu' stati
    -- (E_STATO_ISO2_AMBIGUO; prima un SELECT INTO ne prendeva uno a caso);
    -- altrimenti quello proposto, che valida e non ripiega. ⛔ Il ripiego
    -- silenzioso a 'IT' e il parametro soggetto_default_stato_iso2 sono
    -- ritirati.
    IF NULLIF(btrim(p_stato_iso2), '') IS NOT NULL THEN
        v_stato_iso2_resolved := upper(btrim(p_stato_iso2));
        v_stato_id := script.fn_stato_id_da_iso2(v_stato_iso2_resolved, 'anagrafiche.fn_crea_soggetto_pg');
    ELSE
        v_stato_id := script.fn_stato_proposto_id('anagrafiche.fn_crea_soggetto_pg');
    END IF;

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

    -- Step 1: Creazione soggetto (Persona Giuridica)
    -- ⭐ Rev 20261123-56 (S4, brief-db-revisione-anagrafiche §20):
    --   - CF e P.IVA passano come arrivano: li normalizza
    --     trgfn_soggetti_normalize (a01), una regola sola (D-T5-2 a);
    --   - il doppione lo dice l'indice uq_soggetto_idstato_id_fiscale_univoco,
    --     sulla coppia (stato, CF + P.IVA). Il pre-controllo di prima
    --     guardava un campo per volta: diceva altro dall'indice, e il
    --     doppione che gli sfuggiva arrivava come 23505 senza codice. Qui
    --     la violazione di QUELL'indice (per nome) diventa
    --     E_ADMIN_CF_DUPLICATO, anche nella corsa fra due creazioni; ogni
    --     altra violazione risale com'e'.
    BEGIN
        INSERT INTO anagrafiche.soggetti (
            ragione_sociale, codice_fiscale, partita_iva,
            stato_id, tipo_soggetto_dettaglio_id, attivo
        )
        VALUES (
            TRIM(p_ragione_sociale),
            p_codice_fiscale,
            p_partita_iva,
            v_stato_id, p_tipo_soggetto_dettaglio_id, true
        )
        RETURNING id INTO v_soggetto_id;
    EXCEPTION
        WHEN unique_violation THEN
            GET STACKED DIAGNOSTICS v_vincolo = CONSTRAINT_NAME;
            IF v_vincolo IS DISTINCT FROM 'uq_soggetto_idstato_id_fiscale_univoco' THEN
                RAISE;
            END IF;
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_soggetto_pg',
                'E_ADMIN_CF_DUPLICATO',
                jsonb_build_object('campo',          CASE WHEN NULLIF(btrim(p_partita_iva), '') IS NOT NULL THEN 'partita_iva' ELSE 'codice_fiscale' END,
                                   'vincolo',        v_vincolo,
                                   'stato_id',       v_stato_id,
                                   'codice_fiscale', p_codice_fiscale,
                                   'partita_iva',    p_partita_iva),
                NULL::uuid,
                format('Esiste gia'' un soggetto con lo stesso identificativo fiscale nello stesso stato (codice fiscale %s, partita IVA %s)',
                       COALESCE(NULLIF(btrim(p_codice_fiscale), ''), '-'),
                       COALESCE(NULLIF(btrim(p_partita_iva), ''), '-')));
    END;

    -- Step 2: Creazione contatto default con tipo_contatto_id
    --         (BB anagrafiche.fn_crea_contatto, rev 2026-10-17)
    PERFORM anagrafiche.fn_crea_contatto(
        v_soggetto_id, NULL,
        jsonb_build_object('tipo_contatto_id', v_tipo_contatto_id,
                           'nominativo',       TRIM(p_ragione_sociale),
                           'email',            TRIM(p_email),
                           'is_default',       true));

    -- Step 3: i dati societari. ⭐ Rev 20261020-02 (brief-db-dati-societari-in-creazione):
    --   QUANDO scriverli lo decide il BB della nascita, lo stesso di
    --   fn_crea_soggetto_pf (regola del 2): policy REQUIRED, o almeno un campo
    --   con un valore, data di costituzione compresa (prima si perdeva: il verbo
    --   la riceveva NULL). Una sezione passata a una natura NONE non si scarta
    --   piu' in silenzio: la rifiuta il guard della natura. Scrive il verbo
    --   (rev 20261011-01, B-4), e le regole restano nei trigger della tabella.
    PERFORM anagrafiche.fn_scrivi_dati_societari_alla_nascita(
        p_soggetto_id        := v_soggetto_id,
        p_forma_giuridica_id := p_forma_giuridica_id,
        p_id_prov_iscri_rea  := p_id_prov_iscri_rea,
        p_iscrizione_rea     := p_iscrizione_rea,
        p_capitale_sociale   := p_capitale_sociale,
        p_socio_unico        := p_socio_unico,
        p_liquidazione       := p_liquidazione,
        p_destinatario_fe    := p_destinatario_fe,
        p_pec_fatturazione   := p_pec_fatturazione,
        p_codice_sdi         := p_codice_sdi,
        p_data_costituzione  := p_data_costituzione
    );

    RETURN v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_soggetto_pg(p_ragione_sociale text, p_tipo_soggetto_dettaglio_id bigint, p_email character varying, p_codice_fiscale text, p_partita_iva text, p_stato_iso2 character, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_tipo_contatto_id integer, p_data_costituzione date)
IS 'Crea un soggetto PG o ENC, il suo contatto di default (anagrafiche.fn_crea_contatto; il tipo di contatto, se non passato, e'' il primo di config.tipi_contatti) e i dati societari quando la natura li pretende o se ne riceve almeno un campo (anagrafiche.fn_scrivi_dati_societari_alla_nascita, lo stesso BB di fn_crea_soggetto_pf): una sezione passata a una natura NONE la rifiuta il guard della natura. Una natura base PF (privato, ditta individuale) si rifiuta con E_SOGGETTO_CREAZIONE_NATURA_ERRATA: la porta e'' fn_crea_soggetto_pf. Il sesso non si scrive. Stato: p_stato_iso2 se detto (script.fn_stato_id_da_iso2: E_STATO_ISO2_AMBIGUO se indica piu'' stati, E_CODICE se nessuno), altrimenti lo stato proposto (script.fn_stato_proposto_id). CF e P.IVA entrano come arrivano: li normalizza trgfn_soggetti_normalize. Il doppione lo dice l''indice uq_soggetto_idstato_id_fiscale_univoco sulla coppia (stato, CF + P.IVA), tradotto in E_ADMIN_CF_DUPLICATO con campo partita_iva se passata, altrimenti codice_fiscale. NON crea indirizzi ne'' assegna ruoli.';
```

</div>

---
{% include-markdown "signature-core.md" %}
