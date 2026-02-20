{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_resellers_guard_attivo.md" %}
# ⚙️ Funzione `trgfn_resellers_guard_attivo`

```sql
CREATE FUNCTION trgfn_resellers_guard_attivo()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_resellers_guard_attivo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_has_mapping boolean;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Impedisce la disattivazione di un reseller quando esistono
  --   mapping attivi in resellers_billing_account.
  -- =========================================================
  IF TG_OP = 'UPDATE'
    AND NEW.attivo = false
    AND COALESCE(OLD.attivo, true) = true
  THEN
    SELECT EXISTS (
      SELECT 1
        FROM anagrafiche.resellers_billing_account m
       WHERE m.reseller_soggetto_ruolo_id = NEW.soggetto_ruolo_id
    )
    INTO v_has_mapping;

    IF v_has_mapping THEN
      PERFORM script.fn_log_and_raise_error(
        TG_TABLE_SCHEMA,
        TG_NAME,
        'E_GENERICO',
        jsonb_build_object(
          'detail','Disattivazione reseller non consentita: mapping billing_account presente',
          'soggetto_ruolo_id', NEW.soggetto_ruolo_id
        ),
        NULL::uuid,
        'Disattivazione reseller non consentita: mapping billing_account presente'
      );
    END IF;
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_resellers_guard_attivo()
IS 'Blocca la disattivazione se esistono mapping in resellers_billing_account.';
```

---
{% include-markdown "signature-core.md" %}
