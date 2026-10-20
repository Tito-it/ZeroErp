{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_guard_stato.md" %}
# ⚙️ Funzione `trgfn_fatture_guard_stato`

```sql
CREATE FUNCTION trgfn_fatture_guard_stato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ok BOOLEAN;
    v_tipo_lotto vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_old_ordine config.stati_doc_fiscale.ordine%TYPE;
    v_new_ordine config.stati_doc_fiscale.ordine%TYPE;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.stato_doc_fiscale_id IS NOT NULL
       AND NEW.stato_doc_fiscale_id IS DISTINCT FROM OLD.stato_doc_fiscale_id
    THEN
        -- Blocco retrocessione per lotti giornalieri
        SELECT l.tipo_lotto, s_old.ordine, s_new.ordine
          INTO v_tipo_lotto, v_old_ordine, v_new_ordine
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatturazione_lotti l ON l.id = lf.lotto_id
          LEFT JOIN config.stati_doc_fiscale s_old ON s_old.id = OLD.stato_doc_fiscale_id
          LEFT JOIN config.stati_doc_fiscale s_new ON s_new.id = NEW.stato_doc_fiscale_id
         WHERE lf.fattura_id = NEW.id ORDER BY l.id LIMIT 1;

        IF v_tipo_lotto = 'GIORNALIERO' AND v_old_ordine IS NOT NULL AND v_new_ordine IS NOT NULL AND v_new_ordine < v_old_ordine THEN
            PERFORM script.fn_log_and_raise_error(TG_TABLE_SCHEMA, TG_NAME, 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'retrocessione_giornaliero', 'atteso', concat('ordine>=', v_old_ordine), 'ricevuto', v_new_ordine),
                NULL::uuid, concat('retrocessione ', OLD.stato_doc_fiscale_id, '→', NEW.stato_doc_fiscale_id), 'GIORNALIERO');
        END IF;

        IF OLD.stato_doc_fiscale_id IS NULL THEN
            -- Prima assegnazione
            SELECT s.applica_fattura INTO v_ok FROM config.stati_doc_fiscale s WHERE s.id = NEW.stato_doc_fiscale_id AND s.attivo;
            IF COALESCE(v_ok, FALSE) = FALSE THEN
                PERFORM script.fn_log_and_raise_error(TG_TABLE_SCHEMA, TG_NAME, 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'stato_doc_fiscale_id', 'atteso', 'applica_fattura=true', 'ricevuto', NEW.stato_doc_fiscale_id),
                    NULL::uuid, 'stato non applicabile a fattura', NEW.stato_doc_fiscale_id::text);
            END IF;
        ELSE
            -- Transizione ammessa
            SELECT EXISTS (
                SELECT 1 FROM config.stati_doc_fiscale_transizioni t
                 WHERE t.ammesso AND t.stato_from_id = OLD.stato_doc_fiscale_id AND t.stato_to_id = NEW.stato_doc_fiscale_id AND t.solo_lotto = FALSE
            ) INTO v_ok;
            IF NOT v_ok THEN
                PERFORM script.fn_log_and_raise_error(TG_TABLE_SCHEMA, TG_NAME, 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'transizione_stato', 'atteso', concat(OLD.stato_doc_fiscale_id, '→ammessa'), 'ricevuto', NEW.stato_doc_fiscale_id),
                    NULL::uuid, concat('transizione ', OLD.stato_doc_fiscale_id, '→', NEW.stato_doc_fiscale_id), 'fattura');
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_guard_stato()
IS 'Guard transizioni stato fatture via config.stati_doc_fiscale_transizioni. Blocco retrocessione GIORNALIERO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
