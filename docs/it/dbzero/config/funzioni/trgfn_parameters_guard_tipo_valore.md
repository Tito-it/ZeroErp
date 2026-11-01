# ⚙️ Funzione `trgfn_parameters_guard_tipo_valore`

```sql
CREATE FUNCTION trgfn_parameters_guard_tipo_valore()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameters_guard_tipo_valore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: il default di un parametro ha la forma del suo tipo;
--   cambiando il tipo, anche ogni override esistente (anche spento).
-- La forma la dice script.fn_valore_parametro_non_conforme.
-- Brief: brief-db-liste-datatable-grezze-secondo-giro §4.6.1.
-- Rev 2026-11-01 (§7.7.1): il campo va sotto 'campo', l'unica chiave
--   che fn_log_and_raise_error porta sul canale COLUMN.
-- =========================================================
DECLARE
    -- La forma attesa in parole (NULL = conforme): nessuna colonna.
    v_forma        text;
    v_override_id  config.parameter_overrides.id%TYPE;
    v_override_val config.parameter_overrides.overridden_value%TYPE;
BEGIN
    -- UPDATE OF scatta anche a valore uguale: conta il cambio.
    IF TG_OP = 'UPDATE'
       AND NEW.default_value IS NOT DISTINCT FROM OLD.default_value
       AND NEW.tipo_valore   IS NOT DISTINCT FROM OLD.tipo_valore THEN
        RETURN NEW;
    END IF;

    -- 1. Il default.
    v_forma := script.fn_valore_parametro_non_conforme(NEW.tipo_valore, NEW.default_value);
    IF v_forma IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'config.trgfn_parameters_guard_tipo_valore',
            'E_PARAMETER_VALORE_NON_CONFORME',
            jsonb_build_object(
                'campo',        'default_value',
                'parameter_id', NEW.id,
                'code',         NEW.code,
                'tipo_valore',  NEW.tipo_valore,
                'valore',       NEW.default_value),
            NEW.tx_id,
            NEW.default_value::text, NEW.code::text, v_forma);
    END IF;

    -- 2. Gli override, solo se il tipo cambia (all'INSERT non ce ne sono).
    IF TG_OP = 'UPDATE' AND NEW.tipo_valore IS DISTINCT FROM OLD.tipo_valore THEN
        SELECT o.id, o.overridden_value
          INTO v_override_id, v_override_val
          FROM config.parameter_overrides o
         WHERE o.parameter_id = NEW.id
           AND script.fn_valore_parametro_non_conforme(NEW.tipo_valore, o.overridden_value) IS NOT NULL
         ORDER BY o.id
         LIMIT 1;

        IF FOUND THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'config.trgfn_parameters_guard_tipo_valore',
                'E_PARAMETER_OVERRIDE_NON_CONFORME_AL_TIPO',
                jsonb_build_object(
                    'campo',        'tipo_valore',
                    'parameter_id', NEW.id,
                    'code',         NEW.code,
                    'tipo_valore',  NEW.tipo_valore,
                    'override_id',  v_override_id,
                    'valore',       v_override_val),
                NEW.tx_id,
                NEW.code::text, v_override_val::text,
                script.fn_valore_parametro_non_conforme(NEW.tipo_valore, v_override_val));
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_parameters_guard_tipo_valore()
IS 'Guard di config.parameters (a07, BEFORE INSERT OR UPDATE OF default_value, tipo_valore): default_value deve avere la forma di tipo_valore (script.fn_valore_parametro_non_conforme), altrimenti E_PARAMETER_VALORE_NON_CONFORME. Quando cambia il tipo, anche ogni override esistente del parametro, acceso o spento, deve averne la forma, altrimenti E_PARAMETER_OVERRIDE_NON_CONFORME_AL_TIPO (CONFLITTO_STATO). Parla prima del dispatcher FK-surrogata (a10): prima la forma, poi l''esistenza nel catalogo. Il campo da correggere esce sul canale COLUMN (chiave ''campo'' del contesto: default_value, o tipo_valore sul cambio di tipo; fino al 2026-11-01 stava sotto ''field'' e non arrivava). Gemello: config.trgfn_parameter_overrides_guard_tipo_valore. Brief: brief-db-liste-datatable-grezze-secondo-giro (D-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
