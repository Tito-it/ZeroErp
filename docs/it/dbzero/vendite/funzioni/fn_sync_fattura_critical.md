{% include-markdown "it/dbzero/vendite/manual/fn_sync_fattura_critical.md" %}
# ⚙️ Funzione `fn_sync_fattura_critical`

```sql
CREATE FUNCTION fn_sync_fattura_critical(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_fattura_critical(p_fattura_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_has_critical boolean;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Aggiorna fatture.critical in base ai log attivi.
  --
  -- Regole:
  --   - C (critical) ha priorita` su W (warning)
  --   - disabilitato = true esclude il log
  -- =========================================================

  IF p_fattura_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_fattura_critical', 'E_GENERICO',
      jsonb_build_object('detail','fattura_id obbligatorio'),
      NULL::uuid, 'fattura_id obbligatorio'
    );
  END IF;

  SELECT EXISTS (
    SELECT 1
    FROM vendite.fatture_log
    WHERE fattura_id = p_fattura_id
      AND disabilitato IS FALSE
      AND status = 'C'
  )
  INTO v_has_critical;

  UPDATE vendite.fatture
     SET critical = COALESCE(v_has_critical, false),
         data_update = now(),
         user_update = current_user
   WHERE id = p_fattura_id;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
