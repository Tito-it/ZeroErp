{% include-markdown "it/dbzero/config/manual/trgfn_parameters_fk_surrogate_dispatch.md" %}
# ⚙️ Funzione `trgfn_parameters_fk_surrogate_dispatch`

```sql
CREATE FUNCTION trgfn_parameters_fk_surrogate_dispatch()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameters_fk_surrogate_dispatch()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: dispatcher generico per il framework FK-surrogata su
-- config.parameters. Per ogni INSERT/UPDATE OF code, default_value
-- delega a script.fn_check_parameter_fk_surrogate (lookup
-- registry config.parameter_fk_surrogate). Se il check fallisce,
-- raise E_PARAMETER_DEFAULT_VALUE_INVALID.
-- Per code non presenti nel registry, il check ritorna true e
-- il trigger e' di fatto no-op.
DECLARE
    v_target_schema text;
    v_target_table  text;
    v_target_column text;
    v_target_label  text;
BEGIN
    IF NEW.default_value IS NULL THEN
        RETURN NEW;
    END IF;

    IF script.fn_check_parameter_fk_surrogate(NEW.code, NEW.default_value) THEN
        RETURN NEW;
    END IF;

    -- Lookup target per messaggio errore (info diagnostica).
    SELECT pfs.target_schema, pfs.target_table, pfs.target_column
      INTO v_target_schema, v_target_table, v_target_column
      FROM config.parameter_fk_surrogate pfs
     WHERE pfs.enabled
       AND (
              (pfs.match_mode = 'EXACT' AND pfs.code_pattern = NEW.code)
           OR (pfs.match_mode = 'LIKE'  AND NEW.code LIKE pfs.code_pattern)
       )
     ORDER BY (pfs.match_mode = 'EXACT') DESC, length(pfs.code_pattern) DESC
     LIMIT 1;

    v_target_label := format('%I.%I.%I',
        v_target_schema, v_target_table, v_target_column);

    PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME::text,
        'E_PARAMETER_DEFAULT_VALUE_INVALID',
        jsonb_build_object(
            'parameter_id',  NEW.id,
            'code',          NEW.code,
            'default_value', NEW.default_value,
            'target',        v_target_label
        ),
        NEW.tx_id,
        NEW.code,
        NEW.default_value,
        v_target_label
    );
    -- Unreachable: fn_log_and_raise_error solleva.
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_parameters_fk_surrogate_dispatch()
IS 'Dispatcher framework FK-surrogata su config.parameters. Legge regole da config.parameter_fk_surrogate via script.fn_check_parameter_fk_surrogate. Raise E_PARAMETER_DEFAULT_VALUE_INVALID. Sostituisce trgfn_parameters_guard_default_tipo_soggetto_dettaglio (droppato 20260502-07).';
```

</div>

---
{% include-markdown "signature-core.md" %}
