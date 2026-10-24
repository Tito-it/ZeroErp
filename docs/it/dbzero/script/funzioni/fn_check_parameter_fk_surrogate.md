{% include-markdown "it/dbzero/script/manual/fn_check_parameter_fk_surrogate.md" %}
# ⚙️ Funzione `fn_check_parameter_fk_surrogate`

```sql
CREATE FUNCTION fn_check_parameter_fk_surrogate(p_code text, p_value text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_parameter_fk_surrogate(p_code text, p_value text)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: check FK-surrogata generico per parametri.
-- Cerca un pattern abilitato in config.parameter_fk_surrogate
-- che matchi p_code (EXACT prioritario su LIKE), poi verifica
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

    SELECT pfs.target_schema, pfs.target_table, pfs.target_column
      INTO v_target_schema, v_target_table, v_target_column
      FROM config.parameter_fk_surrogate pfs
     WHERE pfs.enabled
       AND (
              (pfs.match_mode = 'EXACT' AND pfs.code_pattern = p_code)
           OR (pfs.match_mode = 'LIKE'  AND p_code LIKE pfs.code_pattern)
       )
     ORDER BY (pfs.match_mode = 'EXACT') DESC, length(pfs.code_pattern) DESC
     LIMIT 1;

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
IS 'Check FK-surrogata generico per parametri. Lookup registry config.parameter_fk_surrogate (EXACT > LIKE), poi lookup dinamico sul target. Ritorna boolean. Usata dai dispatcher config.trgfn_parameters_fk_surrogate_dispatch e config.trgfn_parameter_overrides_fk_surrogate_dispatch. ⭐ rev 2026-08-31: «valore assente» comprende la STRINGA VUOTA e non solo il NULL. L''argomento sta sul modello e non sulla comodita'': config.parameters.default_value e config.parameter_overrides.overridden_value sono ENTRAMBE NOT NULL, quindi il ramo NULL era codice irraggiungibile da tutti e due i chiamanti e la regola che dichiarava — «assenza di valore, nessun controllo» — non si applicava mai; su un parametro il vuoto e'' l''unica forma che «nessun valore» puo'' assumere. ⛔ Senza questa rev, db/changelog/migrations_v2/80_data/sql/config/parameters.csv e'' un file INTOCCABILE: la riga DEFAULT_UTILITY ha default_value vuoto e una riga di registry attiva, il suo mirror e'' runOnChange, e qualunque modifica al CSV lo sveglia e fa morire il migrate su quella riga (successo il 2026-08-25). ⚠️ Solo la stringa vuota, NON il bianco: un valore fatto di spazi resta rifiutato, perche'' un codice_interno non e'' mai bianco e questa check e'' l''unica cosa che intercetta quel refuso. brief-db-default-iva-chiave-naturale §2-bis (decisione A, Tid 2026-08-31).';
```

</div>

---
{% include-markdown "signature-core.md" %}
