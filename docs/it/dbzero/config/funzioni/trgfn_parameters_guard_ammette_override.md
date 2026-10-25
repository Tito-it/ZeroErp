{% include-markdown "it/dbzero/config/manual/trgfn_parameters_guard_ammette_override.md" %}
# ⚙️ Funzione `trgfn_parameters_guard_ammette_override`

```sql
CREATE FUNCTION trgfn_parameters_guard_ammette_override()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameters_guard_ammette_override()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: un parametro non passa a «vale per tutti»
--   (ammette_override true -> false) finche' ha override, accesi
--   o spenti: resterebbero righe che nessuno legge.
-- Brief: brief-db-parametri-senza-override §3 punto 3.
-- =========================================================
DECLARE
    -- un conteggio: niente colonna da ancorare
    v_n bigint;
BEGIN
    -- Conta solo la chiusura: false -> true, o valore uguale, passano.
    IF NOT (OLD.ammette_override AND NOT NEW.ammette_override) THEN
        RETURN NEW;
    END IF;

    SELECT count(*)
      INTO v_n
      FROM config.parameter_overrides o
     WHERE o.parameter_id = OLD.id;

    IF v_n = 0 THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'database',
        'config.trgfn_parameters_guard_ammette_override',
        'E_PARAMETER_OVERRIDE_PRESENTI',
        jsonb_build_object(
            'parameter_id', OLD.id,
            'code',         OLD.code,
            'campo',        'ammette_override',
            'n_override',   v_n),
        NEW.tx_id,
        OLD.code::text,
        v_n::text);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_parameters_guard_ammette_override()
IS 'Guard di config.parameters (a10, BEFORE UPDATE OF ammette_override): il passaggio true -> false si rifiuta con E_PARAMETER_OVERRIDE_PRESENTI finche'' il parametro ha override in config.parameter_overrides, accesi o spenti (una riga spenta si riaccende). Il verso false -> true passa sempre. Gemello inverso di config.trgfn_parameter_overrides_guard_ammette_override. Brief: brief-db-parametri-senza-override §3 (D-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
