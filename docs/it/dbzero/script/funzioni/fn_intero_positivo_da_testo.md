# ⚙️ Funzione `fn_intero_positivo_da_testo`

```sql
CREATE FUNCTION fn_intero_positivo_da_testo(p_valore text, p_parametro character varying, p_chi text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_intero_positivo_da_testo(p_valore text, p_parametro character varying, p_chi text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il valore di un parametro che deve essere un intero
    --   positivo: dal testo all'intero, oppure E_CONFIG_MANCANTE.
    --
    -- Regole:
    --   - ammesso: la forma INTERO_POSITIVO di
    --     script.fn_valore_parametro_non_conforme (da 1 a 999999,
    --     senza zeri iniziali, segno, decimali o spazi), la
    --     stessa che i guard applicano in scrittura;
    --   - NULL o vuoto: il parametro manca, E_CONFIG_MANCANTE;
    --   - niente valore di ripiego, niente btrim.
    -- =========================================================

    -- Guard di chiamata: senza il nome del parametro l'errore non
    -- direbbe all'amministratore che cosa correggere.
    IF NULLIF(btrim(p_parametro), '') IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', COALESCE(p_chi, 'script.fn_intero_positivo_da_testo'),
            'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'p_parametro obbligatorio'),
            NULL::uuid,
            'script.fn_intero_positivo_da_testo',
            'il codice del parametro da validare e'' obbligatorio');
    END IF;

    -- La regola dal BB delle forme (NULL non e' conforme).
    IF script.fn_valore_parametro_non_conforme('INTERO_POSITIVO', p_valore) IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', COALESCE(p_chi, 'script.fn_intero_positivo_da_testo'),
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config',    'config.parameters',
                               'parametro', p_parametro,
                               'valore',    p_valore),
            NULL::uuid,
            VARIADIC ARRAY[format('parametro %s (intero positivo)', p_parametro)]);
    END IF;

    RETURN p_valore::integer;
END;
$function$

COMMENT ON FUNCTION script.fn_intero_positivo_da_testo(p_valore text, p_parametro character varying, p_chi text)
IS 'La regola «intero positivo» del valore di un parametro di sistema, letta: restituisce l''intero (da 1 a 999999, senza zeri iniziali, segno, decimali o spazi), oppure solleva E_CONFIG_MANCANTE col nome del parametro (assente, vuoto o forma non ammessa). La forma la dice script.fn_valore_parametro_non_conforme (tipo INTERO_POSITIVO, rev 2026-10-31), la stessa che i guard applicano in scrittura. Fail-loud, niente ripiego, niente btrim. Non legge tabelle: il valore lo passa il chiamante, che lo legge dove sta. p_chi: chi la chiama, per il log. Consumatori: dbops.fn_idempotency_soglia_secondi, script.fn_login_parametri, vendite.fn_listini_in_scadenza_senza_successore. Brief: brief-be-verifica-documentazione-api §I.11.0, brief-db-liste-datatable-grezze-secondo-giro (D-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
