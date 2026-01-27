{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_guard_stato.md" %}
# ⚙️ Funzione `trgfn_fatture_guard_stato`

```sql
CREATE FUNCTION trgfn_fatture_guard_stato()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_ok boolean;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Valida le transizioni di stato delle fatture usando
  --   config.stati_doc_fiscale_transizioni.
  --
  -- Regole:
  --   - Stato applicabile a fattura (applica_fattura=true).
  --   - Transizione ammessa e non solo_lotto.
  -- =========================================================
  IF TG_OP = 'UPDATE'
    AND NEW.stato_doc_fiscale_id IS NOT NULL
    AND NEW.stato_doc_fiscale_id IS DISTINCT FROM OLD.stato_doc_fiscale_id
  THEN
    IF OLD.stato_doc_fiscale_id IS NULL THEN
      SELECT s.applica_fattura
        INTO v_ok
        FROM config.stati_doc_fiscale s
       WHERE s.id = NEW.stato_doc_fiscale_id
         AND s.attivo;

      IF COALESCE(v_ok, false) = false THEN
        PERFORM script.fn_log_and_raise_error(
          TG_TABLE_SCHEMA,
          TG_NAME,
          'E_GENERICO',
          jsonb_build_object(
            'detail','Stato non applicabile a fattura',
            'stato_id', NEW.stato_doc_fiscale_id
          ),
          NULL::uuid,
          'Stato non applicabile a fattura'
        );
      END IF;
    ELSE
      SELECT EXISTS (
        SELECT 1
          FROM config.stati_doc_fiscale_transizioni t
         WHERE t.ammesso
           AND t.stato_from_id = OLD.stato_doc_fiscale_id
           AND t.stato_to_id = NEW.stato_doc_fiscale_id
           AND t.solo_lotto = false
      )
      INTO v_ok;

      IF NOT v_ok THEN
        PERFORM script.fn_log_and_raise_error(
          TG_TABLE_SCHEMA,
          TG_NAME,
          'E_GENERICO',
          jsonb_build_object(
            'detail','Transizione stato fattura non ammessa',
            'from', OLD.stato_doc_fiscale_id,
            'to', NEW.stato_doc_fiscale_id
          ),
          NULL::uuid,
          'Transizione stato fattura non ammessa'
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
