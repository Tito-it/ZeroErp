{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_riepiloghi_iva_lotto.md" %}
# ⚙️ Funzione `fn_ricalcola_riepiloghi_iva_lotto`

```sql
CREATE FUNCTION fn_ricalcola_riepiloghi_iva_lotto(p_lotto_id bigint, p_batch_size integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_riepiloghi_iva_lotto(p_lotto_id bigint, p_batch_size integer DEFAULT 1000)
 RETURNS TABLE(fatture_count integer, deleted_rows integer, inserted_rows integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_deleted_rows  INTEGER := 0;
    v_inserted_rows INTEGER := 0;
    v_fatture_count INTEGER := 0;
    v_batch_size    INTEGER := 1000;
    v_ids           BIGINT[];
    v_slice         BIGINT[];
    v_fattura_id    vendite.fatture.id%TYPE;
    v_start         INTEGER := 1;
    v_end           INTEGER := 0;
    v_max           INTEGER := 0;
    v_tmp_deleted   INTEGER;
    v_tmp_inserted  INTEGER;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepiloghi_iva_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_batch_size IS NULL OR p_batch_size <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepiloghi_iva_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_batch_size', 'valore', p_batch_size), NULL::uuid, 'p_batch_size obbligatorio e > 0');
    END IF;

    v_batch_size := p_batch_size;

    SELECT array_agg(lf.fattura_id ORDER BY lf.fattura_id) INTO v_ids
      FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = p_lotto_id;

    IF v_ids IS NULL THEN
        RETURN QUERY SELECT 0, 0, 0;
        RETURN;
    END IF;

    v_max := array_length(v_ids, 1);

    WHILE v_start <= v_max LOOP
        v_end := LEAST(v_start + v_batch_size - 1, v_max);
        v_slice := v_ids[v_start:v_end];

        FOR i IN 1..array_length(v_slice, 1) LOOP
            v_fattura_id := v_slice[i];
            v_fatture_count := v_fatture_count + 1;

            SELECT r.deleted_rows, r.inserted_rows INTO v_tmp_deleted, v_tmp_inserted
              FROM vendite.fn_ricalcola_riepilogo_iva_fattura(v_fattura_id) r;

            v_deleted_rows := v_deleted_rows + COALESCE(v_tmp_deleted, 0);
            v_inserted_rows := v_inserted_rows + COALESCE(v_tmp_inserted, 0);

            PERFORM vendite.fn_ricalcola_totali_fattura(v_fattura_id);
        END LOOP;

        v_start := v_end + 1;
    END LOOP;

    RETURN QUERY SELECT v_fatture_count, v_deleted_rows, v_inserted_rows;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_riepiloghi_iva_lotto(p_lotto_id bigint, p_batch_size integer)
IS 'Ricalcolo riepiloghi IVA + totali per lotto con batch.';
```

</div>

---
{% include-markdown "signature-core.md" %}
