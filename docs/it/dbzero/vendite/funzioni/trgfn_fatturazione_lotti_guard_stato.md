{% include-markdown "it/dbzero/vendite/manual/trgfn_fatturazione_lotti_guard_stato.md" %}
# ⚙️ Funzione `trgfn_fatturazione_lotti_guard_stato`

```sql
CREATE FUNCTION trgfn_fatturazione_lotti_guard_stato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ok BOOLEAN;
    v_bypass TEXT;
    v_tipo_lotto TEXT;
BEGIN
    -- Bypass per reset tecnico
    v_bypass := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
    IF v_bypass IS NOT NULL AND lower(v_bypass) IN ('1', 'true', 'on', 'yes') THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE'
       AND NEW.stato_doc_fiscale_id IS NOT NULL
       AND NEW.stato_doc_fiscale_id IS DISTINCT FROM OLD.stato_doc_fiscale_id
    THEN
        IF OLD.stato_doc_fiscale_id IS NULL THEN
            -- Prima assegnazione: verifica applica_lotto
            SELECT s.applica_lotto INTO v_ok
              FROM config.stati_doc_fiscale s
             WHERE s.id = NEW.stato_doc_fiscale_id AND s.attivo;

            IF COALESCE(v_ok, FALSE) = FALSE THEN
                PERFORM script.fn_log_and_raise_error('database', 'vendite.trgfn_fatturazione_lotti_guard_stato', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'stato_doc_fiscale_id', 'atteso', 'applica_lotto=true', 'ricevuto', NEW.stato_doc_fiscale_id),
                    NULL::uuid, 'stato non applicabile a lotto', NEW.stato_doc_fiscale_id::text);
            END IF;
        ELSE
            -- Transizione: verifica ammessa e non solo_fattura
            SELECT EXISTS (
                SELECT 1 FROM config.stati_doc_fiscale_transizioni t
                 WHERE t.ammesso AND t.stato_from_id = OLD.stato_doc_fiscale_id AND t.stato_to_id = NEW.stato_doc_fiscale_id
                   AND t.solo_fattura = FALSE
                   AND ((t.meta->>'tipo_lotto') IS NULL OR (t.meta->>'tipo_lotto') = NEW.tipo_lotto)
            ) INTO v_ok;

            IF NOT v_ok THEN
                v_tipo_lotto := COALESCE(NEW.tipo_lotto, '');
                PERFORM script.fn_log_and_raise_error('database', 'vendite.trgfn_fatturazione_lotti_guard_stato', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'transizione_stato', 'atteso', concat(OLD.stato_doc_fiscale_id, '→ammessa'), 'ricevuto', NEW.stato_doc_fiscale_id, 'tipo_lotto', v_tipo_lotto),
                    NULL::uuid, concat('transizione ', OLD.stato_doc_fiscale_id, '→', NEW.stato_doc_fiscale_id), v_tipo_lotto);
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato()
IS 'Guard transizioni stato lotti via config.stati_doc_fiscale_transizioni. Bypass via GUC.';
```

</div>

---
{% include-markdown "signature-core.md" %}
