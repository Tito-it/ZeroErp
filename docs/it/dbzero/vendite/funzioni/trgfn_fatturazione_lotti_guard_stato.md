{% include-markdown "it/dbzero/vendite/manual/trgfn_fatturazione_lotti_guard_stato.md" %}
# ⚙️ Funzione `trgfn_fatturazione_lotti_guard_stato`

```sql
CREATE FUNCTION trgfn_fatturazione_lotti_guard_stato()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_ok boolean;
  v_bypass text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Valida le transizioni di stato dei lotti usando
  --   config.stati_doc_fiscale_transizioni.
  --
  -- Regole:
  --   - Stato applicabile a lotto (applica_lotto=true).
  --   - Transizione ammessa e non solo_fattura.
  --   - Bypass controllato via GUC per reset tecnico.
  -- =========================================================
  v_bypass := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
  IF v_bypass IS NOT NULL AND lower(v_bypass) IN ('1','true','on','yes') THEN
    RETURN NEW;
  END IF;

  IF TG_OP = 'UPDATE'
    AND NEW.stato_doc_fiscale_id IS NOT NULL
    AND NEW.stato_doc_fiscale_id IS DISTINCT FROM OLD.stato_doc_fiscale_id
  THEN
    IF OLD.stato_doc_fiscale_id IS NULL THEN
      SELECT s.applica_lotto
        INTO v_ok
        FROM config.stati_doc_fiscale s
      WHERE s.id = NEW.stato_doc_fiscale_id
        AND s.attivo;

      IF COALESCE(v_ok, false) = false THEN
        PERFORM script.fn_log_and_raise_error(
          'database', 
          'vendite.trgfn_fatturazione_lotti_guard_stato',
          'E_GENERICO',
          jsonb_build_object(
            'detail','Stato non applicabile a lotto',
            'stato_id', NEW.stato_doc_fiscale_id
          ),
          NULL::uuid,
          concat('Stato non applicabile a lotto', ' stato_id: ', NEW.stato_doc_fiscale_id::text)
        );
      END IF;
    ELSE
      SELECT EXISTS (
        SELECT 1
          FROM config.stati_doc_fiscale_transizioni t
        WHERE t.ammesso
          AND t.stato_from_id = OLD.stato_doc_fiscale_id
          AND t.stato_to_id = NEW.stato_doc_fiscale_id
          AND t.solo_fattura = false
      )
      INTO v_ok;

      IF NOT v_ok THEN
        PERFORM script.fn_log_and_raise_error(
          'database',
          'vendite.trgfn_fatturazione_lotti_guard_stato',
          'E_GENERICO',
          jsonb_build_object(
            'detail','Transizione stato lotto non ammessa',
            'from', OLD.stato_doc_fiscale_id,
            'to', NEW.stato_doc_fiscale_id
          ),
          NULL::uuid,
          concat('Transizione stato lotto non ammessa', 
                  ' from: ', OLD.stato_doc_fiscale_id::text, 
                  ' to: ', NEW.stato_doc_fiscale_id::text)
        );
      END IF;
    END IF;
  END IF;

  RETURN NEW;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
