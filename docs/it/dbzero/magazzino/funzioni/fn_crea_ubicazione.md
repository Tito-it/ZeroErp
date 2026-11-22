# ⚙️ Funzione `fn_crea_ubicazione`

```sql
CREATE FUNCTION fn_crea_ubicazione(p_magazzino_id bigint, p_codice character varying, p_tipo_id bigint, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_crea_ubicazione(p_magazzino_id bigint, p_codice character varying, p_tipo_id bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi     jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_estranea  text;
    -- Le colonne che il BB riceve come argomenti: non stanno in p_campi.
    c_argomenti CONSTANT text[] := ARRAY['codice', 'tipo_id'];
    v_ammesse   text[];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare un'ubicazione del magazzino p_magazzino_id: codice,
    --   tipo e i campi facoltativi di p_campi (le assenti e le
    --   null al DEFAULT). Ritorna l'id.
    --
    -- Regole:
    --   - le chiavi ammesse in p_campi: la lista 'crea' di
    --     magazzino.fn_ubicazioni_colonne_ammesse, tolti gli
    --     argomenti; una chiave fuori elenco: E_CAMPO_NON_AMMESSO;
    --   - perimetro, padre, tipo, unicita': i guard della tabella.
    -- =========================================================
    IF jsonb_typeof(v_campi) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_crea_ubicazione', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_campi', jsonb_typeof(v_campi)),
            NULL::uuid,
            'magazzino.fn_crea_ubicazione',
            'i campi non sono un oggetto');
    END IF;

    v_ammesse := ARRAY(SELECT c
                         FROM unnest(magazzino.fn_ubicazioni_colonne_ammesse('crea')) AS c
                        WHERE c <> ALL (c_argomenti));

    v_estranea := script.fn_prima_chiave_estranea(v_campi, v_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_crea_ubicazione', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'codice', p_codice),
            NULL::uuid,
            v_estranea);
    END IF;

    RETURN (script.fn_scrivi_riga_da_jsonb(
                'magazzino.ubicazioni'::regclass,
                jsonb_strip_nulls(
                    v_campi
                    || jsonb_build_object('magazzino_id', p_magazzino_id,
                                          'codice',       p_codice,
                                          'tipo_id',      p_tipo_id)))
            ->> 'id')::bigint;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_crea_ubicazione(p_magazzino_id bigint, p_codice character varying, p_tipo_id bigint, p_campi jsonb)
IS 'BB: crea un''ubicazione, cioe'' la riga di magazzino.ubicazioni, in una sola istruzione. Magazzino, codice e tipo sono argomenti (NOT NULL della tabella; il magazzino e'' l''identita'' della nascita e poi non cambia); in p_campi le altre colonne della lista crea di magazzino.fn_ubicazioni_colonne_ammesse (le assenti e le null al DEFAULT; una chiave fuori lista: E_CAMPO_NON_AMMESSO col suo nome). attivo non e'' un campo: un''ubicazione nasce attiva. Perimetro, padre dello stesso magazzino, padre e tipo attivi, unicita'' del codice nel magazzino li dicono i guard e i vincoli della tabella. Non controlla il permesso: lo controlla chi lo chiama (il verbo di nascita). Scrive con script.fn_scrivi_riga_da_jsonb. INVOKER. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
