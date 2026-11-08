{% include-markdown "it/dbzero/script/manual/fn_check_parameter_fk_surrogate.md" %}
# ⚙️ Funzione `fn_check_parameter_fk_surrogate`

```sql
CREATE FUNCTION fn_check_parameter_fk_surrogate(p_code text, p_value text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_parameter_fk_surrogate(p_code text, p_value text)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: check FK-surrogata generico per parametri.
-- Chiede a script.fn_parameter_fk_surrogate_regola la regola
-- che governa p_code (EXACT prioritario su LIKE), poi verifica
-- che p_value esista in <target_schema>.<target_table>.
-- <target_column> via SQL dinamico.
-- Ritorna true (passa) se: p_value assente, o nessun pattern
-- matcha, o lookup trova il valore. Ritorna false solo se
-- pattern matcha E valore non esiste.
DECLARE
    v_target_schema text;
    v_target_table  text;
    v_target_column text;
    v_lookup_sql    text;
    v_found         boolean;
BEGIN
    -- ⭐ rev 2026-08-31: «assente» comprende la STRINGA VUOTA.
    --    default_value (config.parameters) e overridden_value
    --    (config.parameter_overrides) sono ENTRAMBE NOT NULL,
    --    quindi il solo ramo NULL era irraggiungibile da tutti e
    --    due i chiamanti: su un parametro il vuoto E' l'unica
    --    forma che «nessun valore» puo' assumere.
    -- ⚠️ Solo `= ''`, non btrim(): un valore fatto di spazi resta
    --    rifiutato. Un codice_interno non e' mai bianco, quindi
    --    ' ' e' un refuso, e questa check e' l'unica cosa che lo
    --    intercetta — allargare a btrim spegnerebbe quel presidio
    --    in cambio di niente.
    IF p_value IS NULL OR p_value = '' THEN
        RETURN true;
    END IF;

    -- La regola la sceglie il risolutore, la stessa che legge il presidio
    -- dbops.vw_parameter_fk_surrogate_dangling.
    SELECT pfs.target_schema, pfs.target_table, pfs.target_column
      INTO v_target_schema, v_target_table, v_target_column
      FROM config.parameter_fk_surrogate pfs
     WHERE pfs.id = script.fn_parameter_fk_surrogate_regola(p_code);

    IF v_target_schema IS NULL THEN
        -- Nessuna regola: code non soggetto a guard.
        RETURN true;
    END IF;

    v_lookup_sql := format(
        'SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I = $1)',
        v_target_schema, v_target_table, v_target_column
    );
    EXECUTE v_lookup_sql INTO v_found USING p_value;
    RETURN v_found;
END;
$function$

COMMENT ON FUNCTION script.fn_check_parameter_fk_surrogate(p_code text, p_value text)
IS 'Check FK-surrogata generica per i parametri: la regola che governa p_code la sceglie script.fn_parameter_fk_surrogate_regola, poi un lookup dinamico verifica che p_value esista in <target_schema>.<target_table>.<target_column>. Ritorna true se il valore e'' assente, se nessuna regola governa il codice o se il lookup lo trova; false solo se una regola lo governa e il valore non esiste. «Valore assente» comprende la stringa vuota: config.parameters.default_value e config.parameter_overrides.overridden_value sono NOT NULL, e su un parametro il vuoto e'' l''unica forma che «nessun valore» puo'' assumere. Solo la stringa vuota, non il bianco: un valore fatto di spazi resta rifiutato, perche'' un codice_interno non e'' mai bianco. La usano i dispatcher config.trgfn_parameters_fk_surrogate_dispatch e config.trgfn_parameter_overrides_fk_surrogate_dispatch, e il presidio dbops.vw_parameter_fk_surrogate_dangling.';
```

</div>

---
{% include-markdown "signature-core.md" %}
