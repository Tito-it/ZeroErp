# ⚙️ Funzione `fn_valore_parametro_non_conforme`

```sql
CREATE FUNCTION fn_valore_parametro_non_conforme(p_tipo_valore text, p_valore text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_valore_parametro_non_conforme(p_tipo_valore text, p_valore text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- =========================================================
-- Scopo: la forma del valore di un parametro. NULL = il valore
--   ha la forma di p_tipo_valore; altrimenti la forma attesa in
--   parole, per il messaggio d'errore.
-- STABLE e non IMMUTABLE: pg_input_is_valid lo e'.
-- Brief: brief-db-liste-datatable-grezze-secondo-giro §4.6.1.
-- =========================================================
DECLARE
    -- La forma attesa in parole: testo di lavoro, nessuna colonna.
    v_forma text;
BEGIN
    v_forma := CASE p_tipo_valore
        WHEN 'BOOLEANO'                      THEN 'true oppure false'
        WHEN 'INTERO_POSITIVO'               THEN 'un numero intero da 1 a 999999'
        WHEN 'INTERO_NON_NEGATIVO'           THEN 'un numero intero da 0 a 999999'
        WHEN 'DECIMALE_POSITIVO'             THEN 'un numero maggiore di zero, col punto per i decimali (al massimo 6)'
        WHEN 'DECIMALE_NON_NEGATIVO'         THEN 'un numero da zero in su, col punto per i decimali (al massimo 6)'
        WHEN 'DECIMALE_NON_NEGATIVO_O_VUOTO' THEN 'un numero da zero in su, col punto per i decimali (al massimo 6), oppure vuoto'
        WHEN 'DATA'                          THEN 'una data nella forma AAAA-MM-GG'
        WHEN 'TESTO'                         THEN 'un valore'
    END;

    IF v_forma IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_valore_parametro_non_conforme',
            'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_valore', p_tipo_valore),
            NULL::uuid,
            'script.fn_valore_parametro_non_conforme',
            format('tipo del valore sconosciuto: %s', COALESCE(p_tipo_valore, 'NULL')));
    END IF;

    -- Nessun valore: non e' conforme a nessun tipo.
    IF p_valore IS NULL THEN
        RETURN v_forma;
    END IF;

    CASE p_tipo_valore
        WHEN 'BOOLEANO' THEN
            IF p_valore IN ('true', 'false') THEN
                RETURN NULL;
            END IF;
        WHEN 'INTERO_POSITIVO' THEN
            IF p_valore ~ '^[1-9][0-9]{0,5}$' THEN
                RETURN NULL;
            END IF;
        WHEN 'INTERO_NON_NEGATIVO' THEN
            IF p_valore ~ '^(0|[1-9][0-9]{0,5})$' THEN
                RETURN NULL;
            END IF;
        WHEN 'DECIMALE_POSITIVO' THEN
            IF p_valore ~ '^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' THEN
                -- Il cast solo dopo la forma: un IF annidato.
                IF p_valore::numeric > 0 THEN
                    RETURN NULL;
                END IF;
            END IF;
        WHEN 'DECIMALE_NON_NEGATIVO' THEN
            IF p_valore ~ '^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' THEN
                RETURN NULL;
            END IF;
        WHEN 'DECIMALE_NON_NEGATIVO_O_VUOTO' THEN
            IF p_valore = '' OR p_valore ~ '^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' THEN
                RETURN NULL;
            END IF;
        WHEN 'DATA' THEN
            IF p_valore ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN
                -- La forma non basta (2026-02-30): la data deve esistere.
                IF pg_input_is_valid(p_valore, 'date') THEN
                    RETURN NULL;
                END IF;
            END IF;
        WHEN 'TESTO' THEN
            RETURN NULL;
    END CASE;

    RETURN v_forma;
END;
$function$

COMMENT ON FUNCTION script.fn_valore_parametro_non_conforme(p_tipo_valore text, p_valore text)
IS 'La forma del valore di un parametro (config.parameters.tipo_valore), in un posto solo: NULL se p_valore ha la forma di p_tipo_valore, altrimenti la forma attesa in parole, per il messaggio d''errore. Forme canoniche, niente btrim: BOOLEANO true/false minuscolo; INTERO_POSITIVO 1..999999 e INTERO_NON_NEGATIVO 0..999999, senza segno ne'' zeri iniziali; DECIMALE_POSITIVO (> 0), DECIMALE_NON_NEGATIVO (>= 0) e DECIMALE_NON_NEGATIVO_O_VUOTO (anche la stringa vuota): fino a 12 cifre intere e 6 decimali, col punto; DATA AAAA-MM-GG e data esistente; TESTO qualunque valore. NULL non e'' conforme a nessun tipo. Tipo sconosciuto: E_SCRIPT_CHIAMATA_NON_VALIDA. Il confine del dominio (un giorno del mese, una percentuale) lo controlla chi legge il parametro. Lettori: i guard a07 di config.parameters e config.parameter_overrides, script.fn_intero_positivo_da_testo. Brief: brief-db-liste-datatable-grezze-secondo-giro (D-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
