{% include-markdown "it/dbzero/script/manual/fn_guard_campi_ammessi.md" %}
# ⚙️ Funzione `fn_guard_campi_ammessi`

```sql
CREATE FUNCTION fn_guard_campi_ammessi(p_campi jsonb, p_ammesse text[], p_dominio text, p_porta text, p_contesto jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_campi_ammessi(p_campi jsonb, p_ammesse text[], p_dominio text, p_porta text, p_contesto jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_estranea text;        -- un nome di chiave jsonb, non una colonna
BEGIN
    -- Scopo: la regola delle porte che ricevono i campi in jsonb.
    --   1. i campi sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA
    --      (NULL compreso: chi non ha campi passa '{}');
    --   2. la prima chiave fuori da p_ammesse (in ordine
    --      alfabetico, da script.fn_prima_chiave_estranea):
    --      E_CAMPO_NON_AMMESSO, col nome nella frase e in
    --      context.campo. Il log e' della porta (p_dominio,
    --      p_porta), il contesto e' il suo piu' la chiave.
    IF jsonb_typeof(p_campi) IS DISTINCT FROM 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            p_dominio, p_porta, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            COALESCE(p_contesto, '{}'::jsonb)
                || jsonb_build_object('tipo_campi', jsonb_typeof(p_campi)),
            NULL::uuid,
            p_porta,
            'i campi non sono un oggetto');
    END IF;

    v_estranea := script.fn_prima_chiave_estranea(p_campi, p_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            p_dominio, p_porta, 'E_CAMPO_NON_AMMESSO',
            COALESCE(p_contesto, '{}'::jsonb)
                || jsonb_build_object('campo', v_estranea),
            NULL::uuid,
            v_estranea);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_campi_ammessi(p_campi jsonb, p_ammesse text[], p_dominio text, p_porta text, p_contesto jsonb)
IS 'BB, guard: la regola delle porte di scrittura che ricevono i campi in jsonb. p_campi deve essere un oggetto (NULL compreso: chi non ha campi passa ''{}''), altrimenti E_SCRIPT_CHIAMATA_NON_VALIDA con context.tipo_campi; nessuna chiave fuori da p_ammesse, altrimenti E_CAMPO_NON_AMMESSO con il nome della prima chiave estranea (in ordine alfabetico, da script.fn_prima_chiave_estranea) nella frase e in context.campo, che il backend legge per accendere il campo. p_ammesse NULL non ammette niente. p_dominio e p_porta sono i primi due argomenti di script.fn_log_and_raise_error: il log resta della funzione che rifiuta. p_contesto e'' il contesto della porta (id, codice, soggetto), a cui il guard aggiunge la sua chiave. La usano i BB di nascita fn_crea_* (magazzino, anagrafiche), i verbi di modifica di magazzino, config.fn_scrivi_profilo_accesso, config.fn_imposta_override_oggetti, anagrafiche.fn_indirizzo_elemento. Non la usa config.fn_pannello_scrivi, che rifiuta con il codice suo E_PANNELLO_CAMPO_NON_AMMESSO. INVOKER, non legge tabelle.';
```

</div>

---
{% include-markdown "signature-core.md" %}
