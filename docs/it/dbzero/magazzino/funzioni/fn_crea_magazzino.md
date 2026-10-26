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
    c_ammesse  CONSTANT text[] := ARRAY['usa_ubicazioni', 'predefinito', 'meta'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare un magazzino: codice, descrizione, indirizzo, i
    --   campi facoltativi di p_campi (le assenti e le null al
    --   DEFAULT) e l'emittente (NULL = quello della sessione,
    --   dal trigger). Ritorna l'id.
    --
    -- Regole:
    --   - una chiave fuori elenco si rifiuta: E_CAMPO_NON_AMMESSO;
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

    v_estranea := script.fn_prima_chiave_estranea(v_campi, c_ammesse);
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
IS 'BB (2026-10-18): crea un magazzino, cioe'' la riga di magazzino.magazzini, in una sola istruzione. Codice, descrizione e indirizzo di dettaglio sono argomenti (NOT NULL della tabella, obbligatori nel backend); p_campi: usa_ubicazioni, predefinito, meta (le assenti e le null al DEFAULT; chiave estranea: E_CAMPO_NON_AMMESSO). attivo non e'' un campo: un magazzino nasce attivo. p_emittente_fiscale_id NULL = quello della sessione, che mette trgfn_default_emittente_fiscale(SOLLEVA); indicato, lo controlla trgfn_guard_emittente_scope. Scope, unicita'' del codice e indirizzo attivo li dicono i guard e i vincoli della tabella. Scrive con script.fn_scrivi_riga_da_jsonb. INVOKER: dentro una SECURITY DEFINER senza operatore in sessione il guard di scope ferma una riga con un padrone. Ritorna l''id. Prende il posto di AnagraficheMagazzinoRepository.create_magazzino (2b-2), dell''INSERT di dbops.fn_pgtap_crea_magazzino e delle fixture dei pgTAP del magazzino. Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 7).';
```

</div>

---
{% include-markdown "signature-core.md" %}
