{% include-markdown "it/dbzero/vendite/manual/fn_get_next_progressivo.md" %}
# ⚙️ Funzione `fn_get_next_progressivo`

```sql
CREATE FUNCTION fn_get_next_progressivo(p_registro_id bigint, p_data date, p_serie text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_next_progressivo(p_registro_id bigint, p_data date, p_serie text DEFAULT NULL::text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_anno  SMALLINT;
    v_mese  SMALLINT := 0;
    v_serie TEXT := COALESCE(p_serie, '');
    v_last  BIGINT;
    v_next  BIGINT;
BEGIN
    IF p_registro_id IS NULL OR p_data IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_next_progressivo', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_registro_id/p_data', 'registro_id', p_registro_id, 'data', p_data),
            NULL::uuid, 'p_registro_id e p_data obbligatori'
        );
    END IF;

    v_anno := vendite.fn_get_anno_registro(p_data);

    -- Lock transazionale per evitare interleaving
    PERFORM pg_advisory_xact_lock(
        hashtext('registri_fatturazione_progressivi'),
        hashtext(p_registro_id::text || '|' || v_anno::text || '|' || v_serie)
    );

    SELECT rp.last_numero INTO v_last
      FROM vendite.registri_fatturazione_progressivi rp
     WHERE rp.registro_id = p_registro_id
       AND rp.anno = v_anno AND rp.mese = v_mese AND rp.serie = v_serie
       FOR UPDATE;

    IF v_last IS NULL THEN
        INSERT INTO vendite.registri_fatturazione_progressivi (registro_id, anno, mese, serie, last_numero, attivo)
        VALUES (p_registro_id, v_anno, v_mese, v_serie, 0, true)
        RETURNING last_numero INTO v_last;
    END IF;

    v_next := v_last + 1;

    UPDATE vendite.registri_fatturazione_progressivi
       SET last_numero = v_next
     WHERE registro_id = p_registro_id AND anno = v_anno AND mese = v_mese AND serie = v_serie;

    RETURN v_next;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_next_progressivo(p_registro_id bigint, p_data date, p_serie text)
IS 'Prossimo progressivo con lock su registri_fatturazione_progressivi.';
```

---
{% include-markdown "signature-core.md" %}
