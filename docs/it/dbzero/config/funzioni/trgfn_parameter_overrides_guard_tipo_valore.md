# ⚙️ Funzione `trgfn_parameter_overrides_guard_tipo_valore`

```sql
CREATE FUNCTION trgfn_parameter_overrides_guard_tipo_valore()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameter_overrides_guard_tipo_valore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: il valore di un override ha la forma del tipo del suo
--   parametro (script.fn_valore_parametro_non_conforme).
-- Parametro assente: lo giudica la FK fk_overrides_parameter.
-- Brief: brief-db-liste-datatable-grezze-secondo-giro §4.6.1.
-- Rev 2026-11-01 (§7.7.1): il campo va sotto 'campo', l'unica chiave
--   che fn_log_and_raise_error porta sul canale COLUMN.
-- =========================================================
DECLARE
    v_code  config.parameters.code%TYPE;
    v_tipo  config.parameters.tipo_valore%TYPE;
    -- La forma attesa in parole (NULL = conforme): nessuna colonna.
    v_forma text;
BEGIN
    -- UPDATE OF scatta anche a valore uguale: conta il cambio.
    IF TG_OP = 'UPDATE'
       AND NEW.parameter_id     IS NOT DISTINCT FROM OLD.parameter_id
       AND NEW.overridden_value IS NOT DISTINCT FROM OLD.overridden_value THEN
        RETURN NEW;
    END IF;

    SELECT p.code, p.tipo_valore
      INTO v_code, v_tipo
      FROM config.parameters p
     WHERE p.id = NEW.parameter_id;

    -- Zero righe: passa, e decide la FK.
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    v_forma := script.fn_valore_parametro_non_conforme(v_tipo, NEW.overridden_value);
    IF v_forma IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'config.trgfn_parameter_overrides_guard_tipo_valore',
            'E_PARAMETER_VALORE_NON_CONFORME',
            jsonb_build_object(
                'campo',        'value',
                'override_id',  NEW.id,
                'parameter_id', NEW.parameter_id,
                'code',         v_code,
                'tipo_valore',  v_tipo,
                'valore',       NEW.overridden_value),
            NEW.tx_id,
            NEW.overridden_value::text, v_code::text, v_forma);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_parameter_overrides_guard_tipo_valore()
IS 'Guard di config.parameter_overrides (a07, BEFORE INSERT OR UPDATE OF parameter_id, overridden_value): overridden_value deve avere la forma di config.parameters.tipo_valore del parametro padre (script.fn_valore_parametro_non_conforme), altrimenti E_PARAMETER_VALORE_NON_CONFORME, sul campo value (canale COLUMN, chiave ''campo'' del contesto; fino al 2026-11-01 stava sotto ''field'' e non arrivava). Prima veniva accettato, e l''errore arrivava in lettura (E_CONFIG_MANCANTE) su ogni lettore del parametro. Dopo a05 (ammette_override), prima di a10 (FK-surrogata). Parametro assente: lo giudica la FK. Gemello: config.trgfn_parameters_guard_tipo_valore (default e cambio di tipo). Brief: brief-db-liste-datatable-grezze-secondo-giro (D-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
