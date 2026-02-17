{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_riepiloghi_iva_lotto.md" %}
# ⚙️ Funzione `fn_ricalcola_riepiloghi_iva_lotto`

```sql
CREATE FUNCTION fn_ricalcola_riepiloghi_iva_lotto(p_lotto_id bigint, p_batch_size integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_riepiloghi_iva_lotto(p_lotto_id bigint, p_batch_size integer DEFAULT 1000)
 RETURNS TABLE(fatture_count integer, deleted_rows integer, inserted_rows integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_deleted_rows integer := 0;
  v_inserted_rows integer := 0;
  v_fatture_count integer := 0;
  v_batch_size integer := 1000;
  v_ids bigint[];
  v_slice bigint[];
  v_fattura_id vendite.fatture.id%TYPE;
  v_start integer := 1;
  v_end integer := 0;
  v_max integer := 0;
  v_tmp_deleted integer;
  v_tmp_inserted integer;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Ricalcolo riepiloghi IVA per lotto con batch.
  --   Ricalcola anche i totali testata.
  --
  -- Regole:
  --   - p_lotto_id obbligatorio
  --   - batch_size > 0
  --   - usa fn_ricalcola_riepilogo_iva_fattura
  --   - usa fn_ricalcola_totali_fattura
  -- =========================================================

  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_ricalcola_riepiloghi_iva_lotto', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail','p_lotto_id obbligatorio')
      ),
      NULL::uuid,
      'p_lotto_id obbligatorio e > 0'
    );
  END IF;

  IF p_batch_size IS NULL OR p_batch_size <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_ricalcola_riepiloghi_iva_lotto', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail','p_batch_size non valido')
      ),
      NULL::uuid,
      'p_batch_size obbligatorio e > 0'
    );
  END IF;

  v_batch_size := p_batch_size;

  SELECT array_agg(lf.fattura_id ORDER BY lf.fattura_id)
    INTO v_ids
    FROM vendite.fatturazione_lotti_fatture lf
   WHERE lf.lotto_id = p_lotto_id;

  IF v_ids IS NULL THEN
    RETURN QUERY SELECT 0, 0, 0;
    RETURN;
  END IF;

  v_fatture_count := COALESCE(array_length(v_ids, 1), 0);
  v_max := v_fatture_count;

  WHILE v_start <= v_max LOOP
    v_end := LEAST(v_start + v_batch_size - 1, v_max);
    v_slice := v_ids[v_start:v_end];

    IF v_slice IS NOT NULL AND array_length(v_slice, 1) IS NOT NULL THEN
      FOREACH v_fattura_id IN ARRAY v_slice
      LOOP
        SELECT t.deleted_rows, t.inserted_rows
          INTO v_tmp_deleted, v_tmp_inserted
          FROM vendite.fn_ricalcola_riepilogo_iva_fattura(v_fattura_id) AS t;
        v_deleted_rows := v_deleted_rows + COALESCE(v_tmp_deleted, 0);
        v_inserted_rows := v_inserted_rows + COALESCE(v_tmp_inserted, 0);

        PERFORM vendite.fn_ricalcola_totali_fattura(v_fattura_id);
      END LOOP;
    END IF;

    v_start := v_end + 1;
  END LOOP;

  RETURN QUERY
  SELECT v_fatture_count, v_deleted_rows, v_inserted_rows;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_riepiloghi_iva_lotto(p_lotto_id bigint, p_batch_size integer)
IS 'Ricalcola IVA e totali per tutte le fatture del lotto con elaborazione a batch.';
```

---
{% include-markdown "signature-core.md" %}
