{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_indirizzi_operatore.md" %}
# ⚙️ Funzione `fn_crea_indirizzi_operatore`

```sql
CREATE FUNCTION fn_crea_indirizzi_operatore(p_soggetto_id uuid, p_residenza jsonb, p_domicilio_fiscale jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzi_operatore(p_soggetto_id uuid, p_residenza jsonb, p_domicilio_fiscale jsonb DEFAULT NULL::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi CONSTANT text := 'anagrafiche.fn_crea_indirizzi_operatore';
    v_el  jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I due indirizzi di un operatore: la residenza e il
    --   domicilio fiscale, che se non e' dato e' la residenza.
    --
    -- Regole:
    --   - senza residenza non si scrive niente (anche se il
    --     domicilio fiscale c'e');
    --   - il tipo lo dice il parametro: un oggetto che porta
    --     tipo_indirizzo_id o tipo_indirizzo_codice_interno e'
    --     una chiamata non valida;
    --   - la forma dell'indirizzo la giudica
    --     fn_crea_indirizzo_soggetto, che scrive le righe.
    -- =========================================================
    IF p_residenza IS NULL THEN
        RETURN;
    END IF;

    FOREACH v_el IN ARRAY ARRAY[p_residenza, p_domicilio_fiscale] LOOP
        IF v_el IS NOT NULL
           AND (jsonb_typeof(v_el) <> 'object'
                OR v_el ? 'tipo_indirizzo_id'
                OR v_el ? 'tipo_indirizzo_codice_interno') THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
                jsonb_build_object('soggetto_id', p_soggetto_id),
                NULL::uuid,
                c_chi,
                'ogni indirizzo e'' un oggetto senza il tipo, che lo dice il parametro');
        END IF;
    END LOOP;

    PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id,
        p_residenza || jsonb_build_object('tipo_indirizzo_codice_interno', 'RES'));

    PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id,
        COALESCE(p_domicilio_fiscale, p_residenza)
            || jsonb_build_object('tipo_indirizzo_codice_interno', 'DOMFISC'));
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_indirizzi_operatore(p_soggetto_id uuid, p_residenza jsonb, p_domicilio_fiscale jsonb)
IS 'Scrive i due indirizzi di un operatore: la residenza (RES) e il domicilio fiscale (DOMFISC), che se non e'' dato e'' la residenza. Ogni indirizzo e'' un oggetto nella forma di anagrafiche.fn_crea_indirizzo_soggetto (libero, dettaglio gia'' risolto, via da risolvere), senza il tipo: il tipo lo dice il parametro, e un oggetto che porta tipo_indirizzo_id o tipo_indirizzo_codice_interno, o che non e'' un oggetto, e'' E_SCRIPT_CHIAMATA_NON_VALIDA. Senza residenza non scrive niente, anche se il domicilio fiscale c''e''. La chiamano anagrafiche.fn_crea_operatore_v2 e anagrafiche.fn_crea_primo_amministratore. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
