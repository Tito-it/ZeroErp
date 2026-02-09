{% include-markdown "it/dbzero/vendite/manual/fn_assign_numero_fattura.md" %}
# ⚙️ Funzione `fn_assign_numero_fattura`

```sql
CREATE FUNCTION fn_assign_numero_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_assign_numero_fattura(p_fattura_id bigint)
 RETURNS TABLE(registro_id bigint, anno smallint, mese smallint, serie character varying, numero bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_registro_id vendite.fatture.registro_id%TYPE;
  v_data vendite.fatture.data%TYPE;
  v_serie vendite.fatture.serie%TYPE;
  v_reset vendite.registri_fatturazione.reset_policy%TYPE;
  v_anno vendite.fatture.anno%TYPE;
  v_mese smallint;
  v_numero vendite.fatture.numero%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Assegnare progressivo di fattura usando il registro
  --   e aggiornare anno/serie/numero sulla testata.
  --
  -- Regole:
  --   - p_fattura_id obbligatorio (> 0)
  --   - usa fn_get_next_progressivo
  --   - mese valorizzato solo se reset_policy = MENSILE
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_assign_numero_fattura',
      'E_GENERICO',
      jsonb_build_object('detail','p_fattura_id obbligatorio', 'fattura_id', p_fattura_id),
      NULL::uuid,
      concat('p_fattura_id obbligatorio: ', COALESCE(p_fattura_id::text, 'NULL'))
    );
  END IF;

  SELECT f.registro_id,
         f.data,
         COALESCE(f.serie, r.serie_default, ''),
         r.reset_policy
    INTO v_registro_id,
         v_data,
         v_serie,
         v_reset
    FROM vendite.fatture f
    JOIN vendite.registri_fatturazione r ON r.id = f.registro_id
   WHERE f.id = p_fattura_id
   FOR UPDATE;

  IF v_registro_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_assign_numero_fattura',
      'E_GENERICO',
      jsonb_build_object('detail','fattura non trovata', 'fattura_id', p_fattura_id),
      NULL::uuid,
      concat('fattura non trovata: ', p_fattura_id)
    );
  END IF;

  v_anno := vendite.fn_get_anno_registro(v_data);
  v_numero := vendite.fn_get_next_progressivo(v_registro_id, v_data, v_serie);
  v_mese := CASE WHEN v_reset = 'MENSILE'
                   THEN EXTRACT(MONTH FROM v_data)::smallint
                   ELSE NULL
                 END;

  UPDATE vendite.fatture
     SET anno = v_anno,
         serie = NULLIF(v_serie, ''),
         numero = v_numero,
         data_update = now(),
         user_update = current_user
   WHERE id = p_fattura_id;

  RETURN QUERY SELECT v_registro_id, v_anno, v_mese, NULLIF(v_serie, '')::varchar, v_numero;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
