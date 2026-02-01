{% include-markdown "it/dbzero/vendite/manual/fn_log_lotto_esito_fatture.md" %}
# ⚙️ Funzione `fn_log_lotto_esito_fatture`

```sql
CREATE FUNCTION fn_log_lotto_esito_fatture(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_lotto_esito_fatture(p_lotto_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_has_critical boolean;
  v_has_warning boolean;
  v_status character;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Registra un log di esito lotto dedotto dai log fatture.
  --
  -- Regole:
  --   - C ha priorita` su W
  --   - se nessun log attivo: status I
  -- =========================================================

  IF p_lotto_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_log_lotto_esito_fatture', 'E_GENERICO',
      jsonb_build_object('detail','lotto_id obbligatorio'),
      NULL::uuid, 'lotto_id obbligatorio'
    );
  END IF;

  SELECT EXISTS (
    SELECT 1
    FROM vendite.fatturazione_lotti_fatture lf
    JOIN vendite.fatture_log fl
      ON fl.fattura_id = lf.fattura_id
    WHERE lf.lotto_id = p_lotto_id
      AND fl.disabilitato IS FALSE
      AND fl.status = 'C'
  )
  INTO v_has_critical;

  SELECT EXISTS (
    SELECT 1
    FROM vendite.fatturazione_lotti_fatture lf
    JOIN vendite.fatture_log fl
      ON fl.fattura_id = lf.fattura_id
    WHERE lf.lotto_id = p_lotto_id
      AND fl.disabilitato IS FALSE
      AND fl.status = 'W'
  )
  INTO v_has_warning;

  v_status := CASE
                WHEN v_has_critical THEN 'C'
                WHEN v_has_warning THEN 'W'
                ELSE 'I'
              END;

  PERFORM vendite.fn_log_pipeline_fase(
    p_lotto_id,
    NULL,
    'Esito fatture lotto',
    v_status,
    NULL,
    jsonb_build_object('source','fatture_log')
  );
END
$function$
```

---
{% include-markdown "signature-core.md" %}
