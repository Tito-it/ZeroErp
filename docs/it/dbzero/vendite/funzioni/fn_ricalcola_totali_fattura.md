{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_totali_fattura.md" %}
# ⚙️ Funzione `fn_ricalcola_totali_fattura`

```sql
CREATE FUNCTION fn_ricalcola_totali_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_totali_fattura(
  p_fattura_id vendite.fatture.id%TYPE
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_imponibile_tot vendite.fatture.imponibile_tot%TYPE;
  v_imposta_tot vendite.fatture.imposta_tot%TYPE;
  v_totale_doc vendite.fatture.totale_doc%TYPE;
  v_totale_fondi vendite.fatture_fondi_fattura.importo%TYPE;
  v_totale_a_pagare vendite.fatture.totale_a_pagare%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Ricalcolo totali testata a partire da riepiloghi IVA
  --   e fondi fattura (tabella dedicata).
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_ricalcola_totali_fattura', 'E_GENERICO',
      jsonb_build_object('detail','fattura_id obbligatoria'),
      NULL::uuid,
      'fattura_id non valido'
    );
  END IF;

  SELECT
    COALESCE(SUM(r.imponibile), 0),
    COALESCE(SUM(r.imposta), 0)
    INTO v_imponibile_tot, v_imposta_tot
  FROM vendite.fatture_riepiloghi_iva r
  WHERE r.fattura_id = p_fattura_id;

  SELECT
    COALESCE(SUM(ff.importo), 0)
    INTO v_totale_fondi
  FROM vendite.fatture_fondi_fattura ff
  WHERE ff.fattura_id = p_fattura_id
    AND ff.attivo IS TRUE;

  v_totale_doc := COALESCE(v_imponibile_tot, 0) + COALESCE(v_imposta_tot, 0);
  v_totale_a_pagare := v_totale_doc
    + COALESCE((SELECT f.arrotondamento_precedente FROM vendite.fatture f WHERE f.id = p_fattura_id), 0)
    + COALESCE((SELECT f.arrotondamento_attuale FROM vendite.fatture f WHERE f.id = p_fattura_id), 0)
    + COALESCE(v_totale_fondi, 0);

  UPDATE vendite.fatture f
     SET imponibile_tot = v_imponibile_tot,
         imposta_tot = v_imposta_tot,
         totale_doc = v_totale_doc,
         totale_a_pagare = v_totale_a_pagare,
         data_update = now(),
         user_update = current_user
   WHERE f.id = p_fattura_id;
END;
$$
```

---
{% include-markdown "signature-core.md" %}
