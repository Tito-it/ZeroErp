{% include-markdown "it/dbzero/magazzino/manual/fn_crea_magazzino.md" %}
# ⚙️ Funzione `fn_crea_magazzino`

```sql
CREATE FUNCTION fn_crea_magazzino(p_codice character varying, p_descrizione character varying, p_indirizzo_dettaglio_id bigint, p_campi jsonb, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_crea_magazzino(p_codice character varying, p_descrizione character varying, p_indirizzo_dettaglio_id bigint, p_campi jsonb DEFAULT '{}'::jsonb, p_emittente_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi    jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_estranea text;
    -- Le colonne che il BB riceve come argomenti: non stanno in p_campi.
    c_argomenti CONSTANT text[] := ARRAY['codice', 'descrizione', 'indirizzo_dettaglio_id'];
    v_ammesse  text[];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare un magazzino: codice, descrizione, indirizzo, i
    --   campi facoltativi di p_campi (le assenti e le null al
    --   DEFAULT) e l'emittente (NULL = quello della sessione,
    --   dal trigger). Ritorna l'id.
    --
    -- Regole:
    --   - le chiavi ammesse in p_campi: la lista 'crea' di
    --     magazzino.fn_magazzini_colonne_ammesse, tolti gli
    --     argomenti; una chiave fuori elenco: E_CAMPO_NON_AMMESSO;
    --   - scope, unicita', indirizzo attivo: i guard della tabella.
    -- =========================================================
    IF jsonb_typeof(v_campi) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_crea_magazzino', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_campi', jsonb_typeof(v_campi)),
            NULL::uuid,
            'magazzino.fn_crea_magazzino',
            'i campi non sono un oggetto');
    END IF;

    v_ammesse := ARRAY(SELECT c
                         FROM unnest(magazzino.fn_magazzini_colonne_ammesse('crea')) AS c
                        WHERE c <> ALL (c_argomenti));

    v_estranea := script.fn_prima_chiave_estranea(v_campi, v_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_crea_magazzino', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'codice', p_codice),
            NULL::uuid,
            v_estranea);
    END IF;

    -- jsonb_strip_nulls: anche l'emittente NULL resta fuori, e lo
    -- mette il trigger dalla sessione.
    RETURN (script.fn_scrivi_riga_da_jsonb(
                'magazzino.magazzini'::regclass,
                jsonb_strip_nulls(
                    v_campi
                    || jsonb_build_object('codice',                 p_codice,
                                          'descrizione',            p_descrizione,
                                          'indirizzo_dettaglio_id', p_indirizzo_dettaglio_id,
                                          'emittente_fiscale_id',   p_emittente_fiscale_id)))
            ->> 'id')::bigint;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_crea_magazzino(p_codice character varying, p_descrizione character varying, p_indirizzo_dettaglio_id bigint, p_campi jsonb, p_emittente_fiscale_id bigint)
IS 'BB: crea un magazzino, cioe'' la riga di magazzino.magazzini, in una sola istruzione. Codice, descrizione e indirizzo di dettaglio sono argomenti (NOT NULL della tabella); in p_campi le altre colonne della lista crea di magazzino.fn_magazzini_colonne_ammesse (le assenti e le null al DEFAULT; una chiave fuori lista: E_CAMPO_NON_AMMESSO col suo nome). attivo non e'' un campo: un magazzino nasce attivo. p_emittente_fiscale_id NULL = quello della sessione, che mette trgfn_default_emittente_fiscale(SOLLEVA); indicato, lo controlla trgfn_guard_emittente_scope. Scope, unicita'' del codice e indirizzo attivo li dicono i guard e i vincoli della tabella. Non controlla il permesso: lo controlla chi lo chiama (il verbo di nascita). Scrive con script.fn_scrivi_riga_da_jsonb. INVOKER: dentro una SECURITY DEFINER senza operatore in sessione il guard di scope ferma una riga con un padrone. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
