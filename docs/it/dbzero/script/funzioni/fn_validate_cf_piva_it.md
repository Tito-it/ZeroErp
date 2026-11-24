{% include-markdown "it/dbzero/script/manual/fn_validate_cf_piva_it.md" %}
# ⚙️ Funzione `fn_validate_cf_piva_it`

```sql
CREATE FUNCTION fn_validate_cf_piva_it(p_tipo_det_id bigint, p_partita_iva text, p_piva_gruppo text, p_codice_fiscale text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_validate_cf_piva_it(p_tipo_det_id bigint, p_partita_iva text, p_piva_gruppo text, p_codice_fiscale text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
    DECLARE
        l_tipo_det RECORD;
        l_error_ctx JSONB;
        l_cf_valido BOOLEAN;  -- esito di un validatore: nessuna colonna di cui sia il riflesso
    BEGIN
        -- 0) Se tipo_soggetto_dettaglio non specificato, skip
        IF p_tipo_det_id IS NULL THEN
            RETURN;
        END IF;

        -- 0b) Recupero il tipo di dettaglio del soggetto
        --     Natura inesistente: il validatore tace e parla la FK di
        --     anagrafiche.soggetti, come in fn_check_cambio_natura_soggetto
        --     (S43-3, brief-db-revisione-anagrafiche §20). Con INTO STRICT
        --     usciva un no_data_found tecnico prima della FK.
        SELECT formato_cf, formato_piva
        INTO l_tipo_det
        FROM config.tipi_soggetto_dettaglio
        WHERE id = p_tipo_det_id;

        IF NOT FOUND THEN
            RETURN;
        END IF;

        ----------------------------------------------------------------
        -- 2) Validazione Partita IVA principale (se prevista e valorizzata)
        ----------------------------------------------------------------
        IF l_tipo_det.formato_piva <> 'NON_APPLICABILE'
        AND p_partita_iva IS NOT NULL
        AND NOT script.fn_valida_partita_iva(p_partita_iva)
        THEN
            l_error_ctx := jsonb_build_object(
                'campo', 'partita_iva',
                'tipo_det', p_tipo_det_id,
                'partita_iva', p_partita_iva
            );
            PERFORM script.fn_log_and_raise_error(
                'database',
                'fn_validate_cf_piva_it',
                'E_PIVA_NON_VALIDA',
                l_error_ctx,
                NULL::uuid,
                p_partita_iva::text
            );
        END IF;

        ----------------------------------------------------------------
        -- 3) Validazione Partita IVA Gruppo Acquisto (stesse regole)
        ----------------------------------------------------------------
        IF l_tipo_det.formato_piva <> 'NON_APPLICABILE'
        AND p_piva_gruppo IS NOT NULL
        AND NOT script.fn_valida_partita_iva(p_piva_gruppo)
        THEN
            l_error_ctx := jsonb_build_object(
                'campo', 'piva_gruppo_acquisto',
                'tipo_det', p_tipo_det_id,
                'piva_gruppo_acquisto', p_piva_gruppo
            );
            PERFORM script.fn_log_and_raise_error(
                'database',
                'fn_validate_cf_piva_it',
                'E_PIVA_NON_VALIDA',
                l_error_ctx,
                NULL::uuid,
                p_piva_gruppo::text
            );
        END IF;

        ----------------------------------------------------------------
        -- 4) Validazione Codice Fiscale (se previsto e valorizzato)
        --    Dispatch in base a formato_cf:
        --    - ALFANUM_16: CF persona fisica (16 char, algoritmo tabella)
        --    - NUM_11:     CF persona giuridica (11 cifre, Luhn = P.IVA)
        ----------------------------------------------------------------
        IF l_tipo_det.formato_cf <> 'NON_APPLICABILE'
        AND p_codice_fiscale IS NOT NULL
        THEN
            -- Selezione validatore in base al formato
            IF l_tipo_det.formato_cf = 'ALFANUM_16' THEN
                l_cf_valido := script.fn_valida_codice_fiscale(p_codice_fiscale);
            ELSIF l_tipo_det.formato_cf = 'NUM_11' THEN
                l_cf_valido := script.fn_valida_partita_iva(p_codice_fiscale);
            ELSE
                -- Formato non ancora supportato per validazione check digit:
                -- accettiamo il valore (la lunghezza e' gia' verificata altrove)
                l_cf_valido := TRUE;
            END IF;

            IF NOT l_cf_valido THEN
                l_error_ctx := jsonb_build_object(
                    'campo', 'codice_fiscale',
                    'tipo_det', p_tipo_det_id,
                    'codice_fiscale', p_codice_fiscale,
                    'formato_cf', l_tipo_det.formato_cf
                );
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    'fn_validate_cf_piva_it',
                    'E_CF_NON_VALIDO',
                    l_error_ctx,
                    NULL::uuid,
                    p_codice_fiscale::text
                );
            END IF;
        END IF;

        RETURN;
    END;
    $function$

COMMENT ON FUNCTION script.fn_validate_cf_piva_it(p_tipo_det_id bigint, p_partita_iva text, p_piva_gruppo text, p_codice_fiscale text)
IS 'Valida partita IVA principale, partita IVA di gruppo e codice fiscale per i soggetti italiani, secondo la natura di dettaglio (config.tipi_soggetto_dettaglio): formato_piva NON_APPLICABILE salta la P.IVA, formato_cf NON_APPLICABILE salta il CF. Il CF si valida per formato: ALFANUM_16 con script.fn_valida_codice_fiscale (persona fisica), NUM_11 con script.fn_valida_partita_iva (persona giuridica); gli altri formati non hanno controllo del carattere di controllo. Natura NULL o inesistente: nessuna validazione (una natura inesistente la rifiuta la FK del chiamante). Un valore non valido solleva E_PIVA_NON_VALIDA o E_CF_NON_VALIDO, con il campo nel contesto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
