{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_guard_fatturato.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_guard_fatturato`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_guard_fatturato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_bypass text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Blocca UPDATE/DELETE se la riga e' gia' fatturata
  --   (fattura_riga_id valorizzato).
  --   Bypass controllato via GUC per reset tecnico.
  -- =========================================================
  v_bypass := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
  IF v_bypass IS NOT NULL AND lower(v_bypass) IN ('1','true','on','yes') THEN
    IF TG_OP = 'DELETE' THEN
      RETURN OLD;
    END IF;
    RETURN NEW;
  END IF;

  IF TG_OP = 'UPDATE' THEN
    IF OLD.fattura_riga_id IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_RIGA_GIA_FATTURATA',
        jsonb_build_object('id', OLD.id, 'fattura_riga_id', OLD.fattura_riga_id),
        NULL::uuid, OLD.id::text
      );
    END IF;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    IF OLD.fattura_riga_id IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_RIGA_GIA_FATTURATA',
        jsonb_build_object('id', OLD.id, 'fattura_riga_id', OLD.fattura_riga_id),
        NULL::uuid, OLD.id::text
      );
    END IF;
    RETURN OLD;
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()
IS 'Blocca update/delete se fattura_riga_id e'' valorizzato; bypass via GUC zeroerp.maintenance_reset_lotto_draft.';
```

</div>

---
{% include-markdown "signature-core.md" %}
