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
    --   - ammesso: da 1 a 999999, senza zeri iniziali, segno,
    --     decimali o spazi ('^[1-9][0-9]{0,5}$');
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

    IF COALESCE(p_valore, '') !~ '^[1-9][0-9]{0,5}$' THEN
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
IS 'La regola «intero positivo» del valore di un parametro di sistema, in una sede: restituisce l''intero (da 1 a 999999, senza zeri iniziali, segno, decimali o spazi), oppure solleva E_CONFIG_MANCANTE col nome del parametro (assente, vuoto o forma non ammessa). Fail-loud, niente ripiego, niente btrim. Non legge tabelle: il valore lo passa il chiamante, che lo legge dove sta (di solito il default nudo di config.parameters, per un parametro senza override). p_chi: chi la chiama, per il log. Consumatori: dbops.fn_idempotency_soglia_secondi, script.fn_login_parametri. Brief: brief-be-verifica-documentazione-api §I.11.0.';
```

</div>

---
{% include-markdown "signature-core.md" %}
