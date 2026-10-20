{% include-markdown "it/dbzero/vendite/manual/fn_get_anno_registro.md" %}
# ⚙️ Funzione `fn_get_anno_registro`

```sql
CREATE FUNCTION fn_get_anno_registro(p_data date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_anno_registro(p_data date)
 RETURNS smallint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_anno smallint;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce l'anno di registro per reset ANNUALE.
  --
  -- Regola:
  --   - usa l'anno solare della data documento.
  -- =========================================================

  IF p_data IS NULL THEN
    RETURN NULL;
  END IF;

  v_anno := EXTRACT(YEAR FROM p_data)::smallint;
  RETURN v_anno;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_anno_registro(p_data date)
IS 'Calcola anno di registro per reset ANNUALE (anno solare).';
```

</div>

---
{% include-markdown "signature-core.md" %}
