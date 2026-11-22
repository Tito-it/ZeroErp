# ⚙️ Funzione `fn_crea_asset`

```sql
CREATE FUNCTION fn_crea_asset(p_articolo_id uuid, p_seriale character varying, p_stato_id bigint, p_ownership_id bigint, p_campi jsonb, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_crea_asset(p_articolo_id uuid, p_seriale character varying, p_stato_id bigint, p_ownership_id bigint, p_campi jsonb DEFAULT '{}'::jsonb, p_emittente_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi     jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_estranea  text;
    -- Le colonne che il BB riceve come argomenti: non stanno in p_campi.
    c_argomenti CONSTANT text[] := ARRAY['seriale', 'stato_id', 'ownership_id'];
    v_ammesse   text[];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare il seriale p_seriale dell'articolo p_articolo_id:
    --   stato, proprieta', i campi facoltativi di p_campi (le
    --   assenti e le null al DEFAULT) e l'emittente (NULL =
    --   quello della sessione, dal trigger). Ritorna l'id.
    --
    -- Regole:
    --   - le chiavi ammesse in p_campi: la lista 'crea' di
    --     magazzino.fn_assets_colonne_ammesse, tolti gli
    --     argomenti; una chiave fuori elenco: E_CAMPO_NON_AMMESSO;
    --   - perimetro, padri attivi, unicita': i guard della tabella.
    -- =========================================================
    IF jsonb_typeof(v_campi) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_crea_asset', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_campi', jsonb_typeof(v_campi)),
            NULL::uuid,
            'magazzino.fn_crea_asset',
            'i campi non sono un oggetto');
    END IF;

    v_ammesse := ARRAY(SELECT c
                         FROM unnest(magazzino.fn_assets_colonne_ammesse('crea')) AS c
                        WHERE c <> ALL (c_argomenti));

    v_estranea := script.fn_prima_chiave_estranea(v_campi, v_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_crea_asset', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'seriale', p_seriale),
            NULL::uuid,
            v_estranea);
    END IF;

    -- jsonb_strip_nulls: anche l'emittente NULL resta fuori, e lo
    -- mette il trigger dalla sessione.
    RETURN (script.fn_scrivi_riga_da_jsonb(
                'magazzino.assets'::regclass,
                jsonb_strip_nulls(
                    v_campi
                    || jsonb_build_object('articolo_id',          p_articolo_id,
                                          'seriale',              p_seriale,
                                          'stato_id',             p_stato_id,
                                          'ownership_id',         p_ownership_id,
                                          'emittente_fiscale_id', p_emittente_fiscale_id)))
            ->> 'id')::bigint;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_crea_asset(p_articolo_id uuid, p_seriale character varying, p_stato_id bigint, p_ownership_id bigint, p_campi jsonb, p_emittente_fiscale_id bigint)
IS 'BB: crea un seriale, cioe'' la riga di magazzino.assets, in una sola istruzione. Articolo, seriale, stato e proprieta'' sono argomenti (NOT NULL della tabella; l''articolo e'' l''identita'' della nascita); in p_campi le altre colonne della lista crea di magazzino.fn_assets_colonne_ammesse (le assenti e le null al DEFAULT; una chiave fuori lista: E_CAMPO_NON_AMMESSO col suo nome). attivo non e'' un campo: un seriale nasce attivo; la posizione la dice il registro. p_emittente_fiscale_id NULL = quello della sessione, che mette trgfn_default_emittente_fiscale(SOLLEVA); indicato, lo controlla trgfn_guard_emittente_scope. Perimetro, articolo, stato, proprieta'' ed emittente attivi e unicita'' del seriale li dicono i guard e i vincoli della tabella. Non controlla il permesso: lo controlla chi lo chiama (il verbo di nascita). Scrive con script.fn_scrivi_riga_da_jsonb. INVOKER. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
