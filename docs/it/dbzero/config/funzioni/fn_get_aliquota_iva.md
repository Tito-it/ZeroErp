{% include-markdown "it/dbzero/config/manual/fn_get_aliquota_iva.md" %}
# ⚙️ Funzione `fn_get_aliquota_iva`

```sql
CREATE FUNCTION fn_get_aliquota_iva(p_iva_id integer, p_stato_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_get_aliquota_iva(p_iva_id integer, p_stato_id integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_aliquota numeric;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Recupero aliquota IVA considerando override per stato.
  --
  -- Regole:
  --   - p_iva_id obbligatorio e > 0
  --   - p_stato_id opzionale (se NULL usa config.iva)
  -- =========================================================

  IF p_iva_id IS NULL OR p_iva_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'config', 'fn_get_aliquota_iva', 'E_GENERICO',
      jsonb_build_object('detail','p_iva_id obbligatorio'),
      NULL::uuid,
      'p_iva_id obbligatorio e > 0'
    );
  END IF;

  SELECT COALESCE(s.aliquota_override, i.aliquota_iva)
    INTO v_aliquota
    FROM config.iva i
    LEFT JOIN config.iva_stati s
      ON s.iva_id = i.id
     AND s.stato_id = p_stato_id
   WHERE i.id = p_iva_id;

  IF v_aliquota IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'config', 'fn_get_aliquota_iva', 'E_GENERICO',
      jsonb_build_object('detail','iva non trovata', 'iva_id', p_iva_id),
      NULL::uuid,
      concat('IVA non trovata per id ', p_iva_id)
    );
  END IF;

  RETURN v_aliquota;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
