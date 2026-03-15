{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto.md" %}
# ⚙️ Funzione `fn_crea_indirizzo_soggetto`

```sql
CREATE FUNCTION fn_crea_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_codice character varying, p_indirizzo_dettaglio_id bigint, p_indirizzo_libero text, p_stato_id integer, p_comune_id integer, p_codice_postale_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_codice character varying, p_indirizzo_dettaglio_id bigint DEFAULT NULL::bigint, p_indirizzo_libero text DEFAULT NULL::text, p_stato_id integer DEFAULT NULL::integer, p_comune_id integer DEFAULT NULL::integer, p_codice_postale_id integer DEFAULT NULL::integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_indirizzo_id  config.tipi_indirizzi.id%TYPE;
    v_indirizzo_id       anagrafiche.indirizzi_soggetti.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Building block per creazione indirizzo soggetto.
    --   Supporta due modalita':
    --     A) Normalizzata: p_indirizzo_dettaglio_id (preferita)
    --     B) Libera: p_indirizzo_libero + p_stato_id +
    --        (p_comune_id + p_codice_postale_id)
    --
    -- Parametri obbligatori:
    --   p_soggetto_id:            soggetto destinatario
    --   p_tipo_indirizzo_codice:  codice_interno del tipo
    --                             (es. 'RESID', 'DOMFISC')
    --
    -- Vincoli DB che scattano automaticamente:
    --   - XOR: chk_indirizzi_soggetti_xor_norm_libero
    --   - Free: chk_indirizzi_soggetti_free_requirements
    --   - Unicita': uq_indirizzi_soggetti_soggetto_tipo
    --   - Guard tipo: trgfn_indirizzi_soggetti_guard_tipo_indirizzo
    --   - Normalize: trgfn_indirizzi_base_normalize
    --   - Geoloc: trgfn_indirizzi_sync_geoloc
    --   - Audit: trgfn_audit_data_user_generic
    --   - TxId: trgfn_tx_id_managed
    --
    -- Restituisce:
    --   indirizzi_soggetti.id creato
    -- =========================================================

    -- =============================================================
    -- Guard: p_soggetto_id obbligatorio
    -- =============================================================
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_indirizzo_soggetto',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_soggetto_id'),
            NULL::uuid, 'p_soggetto_id obbligatorio.'
        );
    END IF;

    -- =============================================================
    -- Guard: p_tipo_indirizzo_codice obbligatorio
    -- =============================================================
    IF p_tipo_indirizzo_codice IS NULL OR BTRIM(p_tipo_indirizzo_codice) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_indirizzo_soggetto',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_tipo_indirizzo_codice'),
            NULL::uuid, 'p_tipo_indirizzo_codice obbligatorio.'
        );
    END IF;

    -- =============================================================
    -- Guard XOR: o normalizzato o libero, mai entrambi, mai nessuno
    -- (il CHECK constraint DB lo rinforza, ma guard esplicito
    --  produce messaggio piu' chiaro)
    -- =============================================================
    IF p_indirizzo_dettaglio_id IS NOT NULL AND p_indirizzo_libero IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_indirizzo_soggetto',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object(
                'p_indirizzo_dettaglio_id', p_indirizzo_dettaglio_id,
                'p_indirizzo_libero', p_indirizzo_libero
            ),
            NULL::uuid,
            'Specificare indirizzo_dettaglio_id OPPURE indirizzo_libero, non entrambi.'
        );
    END IF;

    IF p_indirizzo_dettaglio_id IS NULL AND (p_indirizzo_libero IS NULL OR BTRIM(p_indirizzo_libero) = '') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_indirizzo_soggetto',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'indirizzo'),
            NULL::uuid,
            'Specificare almeno indirizzo_dettaglio_id o indirizzo_libero.'
        );
    END IF;

    -- =============================================================
    -- Guard completezza indirizzo libero
    -- (il CHECK constraint DB lo rinforza, ma guard esplicito
    --  produce messaggio piu' chiaro)
    -- =============================================================
    IF p_indirizzo_libero IS NOT NULL THEN
        IF p_stato_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_indirizzo_soggetto',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_stato_id'),
                NULL::uuid,
                'p_stato_id obbligatorio per indirizzo libero.'
            );
        END IF;

        IF p_comune_id IS NULL OR p_codice_postale_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_indirizzo_soggetto',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object(
                    'p_comune_id', p_comune_id,
                    'p_codice_postale_id', p_codice_postale_id
                ),
                NULL::uuid,
                'p_comune_id e p_codice_postale_id obbligatori per indirizzo libero.'
            );
        END IF;
    END IF;

    -- =============================================================
    -- Lookup tipo_indirizzo_id da codice_interno
    -- =============================================================
    SELECT id INTO v_tipo_indirizzo_id
    FROM config.tipi_indirizzi
    WHERE codice_interno = UPPER(BTRIM(p_tipo_indirizzo_codice));

    IF v_tipo_indirizzo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_indirizzo_soggetto',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_tipo_indirizzo_codice', p_tipo_indirizzo_codice),
            NULL::uuid,
            'Tipo indirizzo non trovato per codice: ' || p_tipo_indirizzo_codice || '.'
        );
    END IF;

    -- =============================================================
    -- INSERT in indirizzi_soggetti
    -- I trigger si occupano di:
    --   - guard tipo (trgfn_indirizzi_soggetti_guard_tipo_indirizzo)
    --   - require parent attivo (soggetti, indirizzi_dettaglio)
    --   - normalize (trgfn_indirizzi_base_normalize)
    --   - sync geoloc (trgfn_indirizzi_sync_geoloc)
    --   - audit (trgfn_audit_data_user_generic)
    --   - tx_id (trgfn_tx_id_managed)
    -- Il vincolo uq_indirizzi_soggetti_soggetto_tipo impedisce
    -- duplicati (soggetto_id, tipo_indirizzo_id).
    -- =============================================================
    INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id,
        tipo_indirizzo_id,
        indirizzo_dettaglio_id,
        indirizzo_libero,
        stato_id,
        comune_id,
        codice_postale_id
    )
    VALUES (
        p_soggetto_id,
        v_tipo_indirizzo_id,
        p_indirizzo_dettaglio_id,
        NULLIF(BTRIM(p_indirizzo_libero), ''),
        p_stato_id,
        p_comune_id,
        p_codice_postale_id
    )
    RETURNING id INTO v_indirizzo_id;

    RETURN v_indirizzo_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_codice character varying, p_indirizzo_dettaglio_id bigint, p_indirizzo_libero text, p_stato_id integer, p_comune_id integer, p_codice_postale_id integer)
IS 'Building block creazione indirizzo soggetto. Supporta modalita'' normalizzata (indirizzo_dettaglio_id) e libera (indirizzo_libero + stato_id + comune_id + codice_postale_id). Guard XOR, lookup tipo_indirizzo da codice_interno, guard completezza libero. Trigger gestiscono: guard tipo, normalize, geoloc, audit, tx_id.';
```

---
{% include-markdown "signature-core.md" %}
