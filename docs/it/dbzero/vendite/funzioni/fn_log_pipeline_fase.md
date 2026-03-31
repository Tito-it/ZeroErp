{% include-markdown "it/dbzero/vendite/manual/fn_log_pipeline_fase.md" %}
# ⚙️ Funzione `fn_log_pipeline_fase`

```sql
CREATE FUNCTION fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character, p_messaggio text, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character DEFAULT 'I'::bpchar, p_messaggio text DEFAULT NULL::text, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_lotto      vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_stato_operativo vendite.fatturazione_lotti.stato_operativo%TYPE;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_pipeline_fase', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_status IS NULL OR p_status NOT IN ('I', 'W', 'C') THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_pipeline_fase', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_status', 'valore', p_status), NULL::uuid, concat('p_status=', coalesce(p_status::text, 'NULL'), ' (ammessi: I, W, C)'));
    END IF;

    SELECT l.tipo_lotto, l.stato_operativo INTO v_tipo_lotto, v_stato_operativo
      FROM vendite.fatturazione_lotti l WHERE l.id = p_lotto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_pipeline_fase', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_id', p_lotto_id), NULL::uuid, concat('lotto_id ', p_lotto_id));
    END IF;

    INSERT INTO vendite.fatturazione_lotti_log (
        lotto_id, data_ora, messaggio, status, disabilitato, fase,
        stato_doc_fiscale_id, tipo_lotto, stato_operativo, meta,
        data_insert, user_insert, data_update, user_update
    )
    VALUES (
        p_lotto_id, now(), COALESCE(p_messaggio, p_fase, 'pipeline'), p_status,
        FALSE, p_fase, p_stato_doc_fiscale_id, v_tipo_lotto, v_stato_operativo,
        COALESCE(p_meta, '{}'::jsonb), now(), current_user, now(), current_user
    );
END;
$function$

COMMENT ON FUNCTION vendite.fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character, p_messaggio text, p_meta jsonb)
IS 'Registra fase pipeline nel log lotto con metadati stato operativo.';
```

---
{% include-markdown "signature-core.md" %}
