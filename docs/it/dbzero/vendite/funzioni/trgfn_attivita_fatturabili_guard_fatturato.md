{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_guard_fatturato.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_guard_fatturato`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_guard_fatturato()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Blocca UPDATE/DELETE se la riga e' gia' fatturata
  --   (fattura_riga_id valorizzato).
  -- =========================================================
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
```

---
{% include-markdown "signature-core.md" %}
