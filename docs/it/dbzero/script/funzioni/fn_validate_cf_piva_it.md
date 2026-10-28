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
        l_cf_valido BOOLEAN;
    BEGIN
        -- 0) Se tipo_soggetto_dettaglio non specificato, skip
        IF p_tipo_det_id IS NULL THEN
            RETURN;
        END IF;

        -- 0b) Recupero il tipo di dettaglio del soggetto
        SELECT formato_cf, formato_piva
        INTO STRICT l_tipo_det
        FROM config.tipi_soggetto_dettaglio
        WHERE id = p_tipo_det_id;

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
IS 'Valida Partita IVA principale, Partita IVA di gruppo e Codice Fiscale per soggetti italiani.

La logica utilizza la configurazione del tipo soggetto di dettaglio (config.tipi_soggetto_dettaglio):
- se formato_piva = NON_APPLICABILE non viene eseguita alcuna validazione sulla P.IVA;
- se formato_cf  = NON_APPLICABILE non viene eseguita alcuna validazione sul Codice Fiscale.

Dispatch validazione CF in base a formato_cf:
- ALFANUM_16: fn_valida_codice_fiscale (algoritmo CF persona fisica, 16 char)
- NUM_11: fn_valida_partita_iva (algoritmo Luhn, CF persona giuridica = P.IVA)
- altri formati: nessuna validazione check digit (solo lunghezza)

In caso di valore non valido richiama script.fn_log_and_raise_error con i codici:
- PIVA_NON_VALIDA per P.IVA principale o di gruppo non valida,
- CF_NON_VALIDO per Codice Fiscale non valido.';
```

</div>

---
{% include-markdown "signature-core.md" %}
