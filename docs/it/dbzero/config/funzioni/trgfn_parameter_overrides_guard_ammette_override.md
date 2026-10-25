{% include-markdown "it/dbzero/config/manual/trgfn_parameter_overrides_guard_ammette_override.md" %}
# ⚙️ Funzione `trgfn_parameter_overrides_guard_ammette_override`

```sql
CREATE FUNCTION trgfn_parameter_overrides_guard_ammette_override()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameter_overrides_guard_ammette_override()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: rifiuta un override su un parametro che vale per tutti
--   (config.parameters.ammette_override = false). Qualunque riga,
--   anche spenta: una riga spenta si riaccende senza passare di qui.
-- Parametro assente: lo giudica la FK fk_overrides_parameter.
-- Brief: brief-db-parametri-senza-override §3 punto 2.
-- =========================================================
DECLARE
    v_code     config.parameters.code%TYPE;
    v_ammette  config.parameters.ammette_override%TYPE;
BEGIN
    -- UPDATE OF scatta anche a valore uguale: conta il cambio.
    IF TG_OP = 'UPDATE' AND NEW.parameter_id IS NOT DISTINCT FROM OLD.parameter_id THEN
        RETURN NEW;
    END IF;

    SELECT p.code, p.ammette_override
      INTO v_code, v_ammette
      FROM config.parameters p
     WHERE p.id = NEW.parameter_id;

    -- Zero righe lascia NULL: passa, e decide la FK.
    IF v_ammette IS DISTINCT FROM false THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'database',
        'config.trgfn_parameter_overrides_guard_ammette_override',
        'E_PARAMETER_OVERRIDE_NON_AMMESSO',
        jsonb_build_object(
            'override_id',  NEW.id,
            'parameter_id', NEW.parameter_id,
            'code',         v_code),
        NEW.tx_id,
        v_code::text);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_parameter_overrides_guard_ammette_override()
IS 'Guard di config.parameter_overrides (a05, BEFORE INSERT OR UPDATE OF parameter_id): un override su un parametro con config.parameters.ammette_override = false si rifiuta con E_PARAMETER_OVERRIDE_NON_AMMESSO. Vale per qualunque riga, anche spenta: una riga spenta si riaccende con un UPDATE di attivo, che il guard non vede. Parla prima del dispatcher FK-surrogata (a10): se il parametro non si personalizza, la frase giusta e'' questa e non «valore assente dal catalogo». Parametro assente: lo giudica la FK. Gemello inverso: config.trgfn_parameters_guard_ammette_override. Brief: brief-db-parametri-senza-override §3 (D-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
