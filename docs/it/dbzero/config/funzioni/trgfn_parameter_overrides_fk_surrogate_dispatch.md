{% include-markdown "it/dbzero/config/manual/trgfn_parameter_overrides_fk_surrogate_dispatch.md" %}
# ⚙️ Funzione `trgfn_parameter_overrides_fk_surrogate_dispatch`

```sql
CREATE FUNCTION trgfn_parameter_overrides_fk_surrogate_dispatch()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameter_overrides_fk_surrogate_dispatch()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: dispatcher framework FK-surrogata su
-- config.parameter_overrides. Per ogni INSERT/UPDATE OF
-- parameter_id, overridden_value, lookup il code padre dal
-- parametro e delega a script.fn_check_parameter_fk_surrogate.
-- Stessa logica del dispatcher su parameters: code non in
-- registry passa, valore NULL passa. Raise solo se pattern
-- matcha E valore non esiste in target.
DECLARE
    v_code           text;
    v_target_schema  text;
    v_target_table   text;
    v_target_column  text;
    v_target_label   text;
BEGIN
    IF NEW.overridden_value IS NULL THEN
        RETURN NEW;
    END IF;

    -- Lookup code dal parametro padre. La FK
    -- fk_overrides_parameter garantisce parameter_id
    -- esistente; in transazione il SELECT vede gia' il
    -- record padre.
    SELECT p.code INTO v_code
      FROM config.parameters p
     WHERE p.id = NEW.parameter_id;

    IF v_code IS NULL THEN
        -- Caso difensivo: parameter_id non risolve. La FK
        -- gestira' l'errore strutturale; qui passiamo.
        RETURN NEW;
    END IF;

    IF script.fn_check_parameter_fk_surrogate(v_code, NEW.overridden_value) THEN
        RETURN NEW;
    END IF;

    SELECT pfs.target_schema, pfs.target_table, pfs.target_column
      INTO v_target_schema, v_target_table, v_target_column
      FROM config.parameter_fk_surrogate pfs
     WHERE pfs.enabled
       AND (
              (pfs.match_mode = 'EXACT' AND pfs.code_pattern = v_code)
           OR (pfs.match_mode = 'LIKE'  AND v_code LIKE pfs.code_pattern)
       )
     ORDER BY (pfs.match_mode = 'EXACT') DESC, length(pfs.code_pattern) DESC
     LIMIT 1;

    v_target_label := format('%I.%I.%I',
        v_target_schema, v_target_table, v_target_column);

    PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME::text,
        'E_PARAMETER_OVERRIDE_VALUE_INVALID',
        jsonb_build_object(
            'override_id',      NEW.id,
            'parameter_id',     NEW.parameter_id,
            'code',             v_code,
            'overridden_value', NEW.overridden_value,
            'target',           v_target_label
        ),
        NEW.tx_id,
        v_code,
        NEW.overridden_value,
        v_target_label
    );
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_parameter_overrides_fk_surrogate_dispatch()
IS 'Dispatcher framework FK-surrogata su config.parameter_overrides. Lookup code via parameter_id e delega a script.fn_check_parameter_fk_surrogate. Raise E_PARAMETER_OVERRIDE_VALUE_INVALID. Chiude la lacuna del guard ad-hoc precedente che non scattava sugli override.';
```

</div>

---
{% include-markdown "signature-core.md" %}
